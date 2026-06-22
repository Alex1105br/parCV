import os
from datetime import datetime, timezone
from io import BytesIO

from flask import Blueprint, request, jsonify, render_template, session, send_file
from werkzeug.utils import secure_filename

from src.app import limiter
from src.config import UPLOAD_FOLDER, MAX_UPLOAD_BYTES
from src.logging_config import logger
from src.models.db import db
from src.models.entrevista import Entrevista, PerguntaEntrevista
from src.services.curriculo_service import obter_ou_criar_curriculo
from src.services.model import (
    gerar_plano_entrevista,
    avaliar_resposta,
    gerar_relatorio_final,
    gerar_titulo_entrevista
)
from src.services.pdf import gerar_pdf_relatorio_entrevista
from src.utils import (
    login_required, allowed_file, carregar_arquivo, 
    sanitize_text, has_prompt_injection, get_file_size
)

bp = Blueprint("entrevista", __name__, url_prefix="/entrevista")


def _get_entrevista_or_404(entrevista_id: str):
    """Busca uma Entrevista pelo id e confere se pertence ao usuário logado.
    Devolve None tanto se o id não existir quanto se pertencer a outro
    usuário — as duas situações são tratadas pelo chamador como 404, sem
    distinguir "não existe" de "não é seu" (evita confirmar a um usuário
    que um id de entrevista de outra pessoa é válido)."""
    entrevista = Entrevista.query.get(entrevista_id)
    if not entrevista or entrevista.user_id != session.get("user_id"):
        return None
    return entrevista


@bp.route("/", methods=["GET"])
@login_required
def entrevista_page():
    """Página inicial do simulador de entrevista (entrevista_planejamento.html),
    onde o usuário envia o currículo e a descrição da vaga para iniciar o
    fluxo. O envio em si é feito via JS, chamando POST /entrevista/gerar-plano."""
    return render_template("entrevista_planejamento.html")


@bp.route("/gerar-plano", methods=["POST"])
@login_required
@limiter.limit("5 per minute")
def gerar_plano():
    """Inicia uma simulação de entrevista a partir de currículo + vaga.

    Valida arquivo e descrição da vaga, extrai o texto do currículo,
    checa prompt injection em ambos os campos e chama a IA
    (gerar_plano_entrevista) para montar o plano: 10 perguntas fixas
    (1-6 hard skills, 7-10 soft skills — convenção fixada no código, não
    numa coluna própria do schema). Cria o registro Entrevista e, a
    partir de plano["questoes_principais"], um PerguntaEntrevista por
    pergunta (cascade delete: apagar a Entrevista apaga as perguntas).

    Usa db.session.flush() antes do commit para ter o id da Entrevista
    disponível e poder referenciá-lo como entrevista_id nas perguntas
    filhas, sem precisar de dois commits separados."""

    # Validar multipart
    if "curriculo" not in request.files:
        return jsonify({"error": "Currículo não fornecido"}), 400
    
    vaga_descricao = request.form.get("vaga_descricao", "").strip()
    if not vaga_descricao:
        return jsonify({"error": "Descrição da vaga não fornecida"}), 400
    
    if has_prompt_injection(vaga_descricao):
        return jsonify({"error": "Conteúdo inválido detectado"}), 422
    
    arquivo = request.files["curriculo"]
    if arquivo.filename == "":
        return jsonify({"error": "Arquivo vazio"}), 400
    
    # Validar arquivo
    if not allowed_file(arquivo.filename):
        return jsonify({"error": "Tipo de arquivo não permitido"}), 400
    
    # Validar tamanho
    file_size = get_file_size(arquivo)
    if file_size > MAX_UPLOAD_BYTES:
        return jsonify({"error": "Arquivo muito grande"}), 413
    
    try:
        # Salvar arquivo
        filename = secure_filename(arquivo.filename)
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        # Preserva o binário exato enviado quando já é PDF (Task 1) — sem
        # conversão/reprocessamento.
        arquivo_pdf_bytes = arquivo.read() if ext == "pdf" else None
        arquivo.seek(0)

        caminho = os.path.join(UPLOAD_FOLDER, filename)
        arquivo.save(caminho)
        
        # Extrair texto do currículo (PDF/DOCX/TXT)
        curriculo_text, erro = carregar_arquivo(caminho)
        os.remove(caminho)
        if erro:
            return jsonify({"error": erro}), 400
        if not curriculo_text:
            return jsonify({"error": "Não foi possível extrair texto do currículo"}), 400

        curriculo_text = sanitize_text(curriculo_text, max_length=20000)

        if has_prompt_injection(curriculo_text):
            return jsonify({"error": "Conteúdo inválido detectado"}), 422
        
        # Chamar IA para gerar plano
        logger.info("Gerando plano de entrevista com IA")
        plano = gerar_plano_entrevista(curriculo_text, vaga_descricao)

        # Título automático (mesmo padrão de gerar_titulo_analise, usado em
        # /analisar) — pode ser renomeado depois via PATCH /entrevista/<id>/titulo
        titulo = gerar_titulo_entrevista(vaga_descricao, curriculo_text)

        # Salva/reutiliza currículo centralizado (dedup por hash de conteúdo)
        curriculo = obter_ou_criar_curriculo(
            user_id=session["user_id"],
            texto=curriculo_text,
            finalidade=vaga_descricao or None,
            arquivo_pdf=arquivo_pdf_bytes,
            arquivo_nome=filename if arquivo_pdf_bytes else None,
            arquivo_mimetype="application/pdf" if arquivo_pdf_bytes else None,
        )

        # Criar registro Entrevista
        entrevista = Entrevista(
            user_id=session["user_id"],
            titulo=titulo,
            curriculo_arquivo=filename,
            curriculo_id=curriculo.id if curriculo else None,
            vaga_descricao=vaga_descricao,
            numero_perguntas=plano["numero_perguntas"],
            plano_entrevista=plano,
            status="em_planejamento"
        )
        db.session.add(entrevista)
        db.session.flush()  # Get ID antes de commit
        
        # Criar PerguntaEntrevista para cada pergunta
        for i, pergunta_text in enumerate(plano["questoes_principais"], 1):
            pergunta = PerguntaEntrevista(
                entrevista_id=entrevista.id,
                numero_sequencial=i,
                pergunta_principal=pergunta_text
            )
            db.session.add(pergunta)
        
        db.session.commit()
        
        logger.info(f"Plano gerado para entrevista {entrevista.id}")
        
        return jsonify({
            "entrevista_id": entrevista.id,
            "titulo": entrevista.titulo,
            "numero_perguntas": plano["numero_perguntas"],  # 10 (6 hard skills + 4 soft skills)
            "plano": {
                "topicos": plano["topicos_principais"],
                "estrategia": plano["estrategia_entrevista"],
                "questoes": plano["questoes_principais"]
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao gerar plano: {str(e)}")
        return jsonify({"error": "Erro ao gerar plano"}), 500


@bp.route("/lista", methods=["GET"])
@login_required
def list_entrevistas():
    """Lista paginada (page/per_page, máx 50 por página) das entrevistas do
    usuário logado, ordenadas da mais recente para a mais antiga. Mesmo
    padrão de list_analises (routes/analisar.py) — devolve um resumo de
    cada entrevista (sem o plano completo nem as perguntas). Inclui
    score_geral (extraído de relatorio_final, quando a entrevista já
    estiver concluída) para exibir um indicador de desempenho na lista,
    análogo ao score_total das análises."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 50)
    pagination = (
        Entrevista.query
        .filter_by(user_id=session["user_id"])
        .order_by(Entrevista.criado_em.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return jsonify({
        "entrevistas": [
            {
                "id": e.id,
                "titulo": e.titulo,
                "status": e.status,
                "vaga_descricao": e.vaga_descricao,
                "criado_em": e.criado_em.isoformat(),
                "score_geral": (e.relatorio_final or {}).get("score_geral"),
                "curriculo_label": e.curriculo.label if e.curriculo else None,
                "curriculo_id":    e.curriculo_id,
            }
            for e in pagination.items
        ],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
    })


@bp.route("/<entrevista_id>/executar", methods=["GET"])
@login_required
def executar_entrevista(entrevista_id):
    """Página de execução da entrevista (entrevista_execucao.html), onde o
    usuário responde pergunta a pergunta. Apenas serve o HTML — o
    carregamento de cada pergunta e o envio de respostas é feito via JS,
    chamando GET /entrevista/<id>/pergunta/<numero> e
    POST /entrevista/<id>/responder. 404 (texto simples, não JSON) se a
    entrevista não existir ou não pertencer ao usuário logado."""
    entrevista = _get_entrevista_or_404(entrevista_id)
    if not entrevista:
        return "Entrevista não encontrada", 404
    return render_template("entrevista_execucao.html", entrevista_id=entrevista_id)


@bp.route("/<entrevista_id>", methods=["GET"])
@login_required
def get_entrevista(entrevista_id):
    """Dados completos de uma entrevista: status, plano gerado pela IA,
    relatório final (se já concluída) e a lista de todas as perguntas
    com a respectiva resposta do usuário e avaliação da IA, quando
    existirem. Usado para repopular a tela de execução/relatório após
    um reload, sem precisar buscar pergunta por pergunta."""
    entrevista = _get_entrevista_or_404(entrevista_id)
    if not entrevista:
        return jsonify({"error": "Entrevista não encontrada"}), 404
    
    # Preparar dados do currículo vinculado, se existir
    curriculo_data = None
    if entrevista.curriculo_id and entrevista.curriculo:
        curriculo_data = {
            "id": entrevista.curriculo.id,
            "label": entrevista.curriculo.label,
            "tem_arquivo_pdf": entrevista.curriculo.arquivo_pdf is not None,
        }
    
    return jsonify({
        "id": entrevista.id,
        "titulo": entrevista.titulo,
        "status": entrevista.status,
        "vaga_descricao": entrevista.vaga_descricao,
        "numero_perguntas": entrevista.numero_perguntas,
        "plano_entrevista": entrevista.plano_entrevista,
        "criado_em": entrevista.criado_em.isoformat(),
        "relatorio_final": entrevista.relatorio_final,
        "curriculo": curriculo_data,
        "perguntas": [
            {
                "numero_sequencial": p.numero_sequencial,
                "tema": p.tema,
                "pergunta_principal": p.pergunta_principal,
                "resposta_usuario": p.resposta_usuario,
                "respondido": p.resposta_usuario is not None,
                "avaliacao_resposta": p.avaliacao_resposta,
                "score": p.avaliacao_resposta.get("score") if p.avaliacao_resposta else None
            }
            for p in entrevista.perguntas
        ]
    }), 200


@bp.route("/<entrevista_id>/titulo", methods=["PATCH"])
@login_required
def renomear_entrevista(entrevista_id):
    """Renomeia manualmente o título de uma entrevista (gerado automaticamente
    na criação — ver gerar_titulo_entrevista). Mesmo padrão da rota análoga
    em /analises/<id>/titulo (routes/analisar.py)."""
    entrevista = _get_entrevista_or_404(entrevista_id)
    if not entrevista:
        return jsonify({"error": "Entrevista não encontrada"}), 404
    data = request.get_json(silent=True) or {}
    titulo = sanitize_text(data.get("titulo", ""))[:100].strip()
    if not titulo:
        return jsonify({"error": "Título vazio"}), 400
    entrevista.titulo = titulo
    db.session.commit()
    return jsonify({"id": entrevista.id, "titulo": entrevista.titulo})


@bp.route("/<entrevista_id>", methods=["DELETE"])
@login_required
def deletar_entrevista(entrevista_id):
    """Apaga definitivamente uma entrevista do histórico — cascade delete
    remove também as PerguntaEntrevista filhas (ver relationship em
    models/entrevista.py). Mesmo padrão de deletar_analise
    (routes/analisar.py)."""
    entrevista = _get_entrevista_or_404(entrevista_id)
    if not entrevista:
        return jsonify({"error": "Entrevista não encontrada"}), 404
    try:
        db.session.delete(entrevista)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error("db_error", extra={"op": "deletar_entrevista", "erro": str(e)})
        return jsonify({"error": "Erro ao apagar entrevista"}), 500
    return jsonify({"ok": True})


@bp.route("/<entrevista_id>/pergunta/<int:numero>", methods=["GET"])
@login_required
def get_pergunta(entrevista_id, numero):
    """Dados de uma pergunta específica da entrevista, pelo número
    sequencial (1-10). Usado pela tela de execução para carregar cada
    pergunta sob demanda, conforme o usuário avança. O campo
    aprofundamentos_pendentes existe no contrato de resposta por
    compatibilidade com o frontend, mas a funcionalidade de perguntas de
    aprofundamento foi removida — perguntas_aprofundamento nunca é mais
    populada, então este campo sempre será 0."""
    entrevista = _get_entrevista_or_404(entrevista_id)
    if not entrevista:
        return jsonify({"error": "Entrevista não encontrada"}), 404
    
    pergunta = PerguntaEntrevista.query.filter_by(
        entrevista_id=entrevista_id,
        numero_sequencial=numero
    ).first()
    
    if not pergunta:
        return jsonify({"error": "Pergunta não encontrada"}), 404
    
    return jsonify({
        "pergunta_id": pergunta.id,
        "numero_sequencial": pergunta.numero_sequencial,
        "tema": pergunta.tema,
        "pergunta_principal": pergunta.pergunta_principal,
        "resposta_anterior": pergunta.resposta_usuario,
        "aprofundamentos_pendentes": len(pergunta.perguntas_aprofundamento or []) if pergunta.perguntas_aprofundamento else 0,
        "total_perguntas": entrevista.numero_perguntas
    }), 200


@bp.route("/<entrevista_id>/responder", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def responder_pergunta(entrevista_id):
    """Salva a resposta do usuário a uma pergunta e dispara a avaliação
    por IA (avaliar_resposta). Na primeira resposta de uma entrevista,
    move o status de em_planejamento para em_andamento.

    O campo "aprofundamentos" da resposta é sempre uma lista vazia: a
    funcionalidade de perguntas de aprofundamento (avaliacao.deve_aprofundar
    -> novas perguntas extras sobre a mesma resposta) foi removida do
    fluxo — a entrevista é direta, com as 10 perguntas fixas definidas
    no plano e nenhuma pergunta adicional gerada dinamicamente. O campo
    é mantido no contrato de resposta por compatibilidade com o
    frontend existente."""
    entrevista = _get_entrevista_or_404(entrevista_id)
    if not entrevista:
        return jsonify({"error": "Entrevista não encontrada"}), 404
    
    data = request.get_json()
    numero_seq = data.get("numero_sequencial")
    resposta = sanitize_text(data.get("resposta", ""))
    
    if not resposta or len(resposta) > 2000:
        return jsonify({"error": "Resposta inválida"}), 400
    
    if has_prompt_injection(resposta):
        return jsonify({"error": "Conteúdo inválido"}), 422
    
    try:
        # Encontrar pergunta
        pergunta = PerguntaEntrevista.query.filter_by(
            entrevista_id=entrevista_id,
            numero_sequencial=numero_seq
        ).first()
        
        if not pergunta:
            return jsonify({"error": "Pergunta não encontrada"}), 404
        
        # Atualizar status
        if entrevista.status == "em_planejamento":
            entrevista.status = "em_andamento"
        
        # Salvar resposta
        pergunta.resposta_usuario = resposta
        pergunta.respondido_em = datetime.now(timezone.utc)
        db.session.add(pergunta)
        db.session.commit()
        
        # Chamar IA para avaliar
        logger.info(f"Avaliando pergunta {numero_seq} da entrevista {entrevista_id}")
        
        contexto = {
            "curriculo_resumo": entrevista.plano_entrevista.get("estrategia_entrevista", "")[:500],
            "vaga_resumida": entrevista.vaga_descricao[:500],
            "pergunta_numero": numero_seq
        }
        
        avaliacao = avaliar_resposta(
            pergunta.pergunta_principal,
            resposta,
            contexto
        )
        
        # Salvar avaliação
        pergunta.avaliacao_resposta = {
            "feedback": avaliacao.get("feedback", ""),
            "score": avaliacao.get("score", 5),
            "aprofundar": avaliacao.get("deve_aprofundar", False)
        }
        
        # Aprofundamentos removidos da funcionalidade — entrevista é direta,
        # com as 10 perguntas fixas do plano (ver docstring da rota acima)
        aprofundamentos_resposta = []
        
        db.session.commit()
        
        return jsonify({
            "salvo": True,
            "feedback_ia": avaliacao.get("feedback", ""),
            "score": avaliacao.get("score", 5),
            "aprofundamentos": aprofundamentos_resposta
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao responder pergunta: {str(e)}")
        return jsonify({"error": "Erro ao processar resposta"}), 500


@bp.route("/<entrevista_id>/finalizar", methods=["POST"])
@login_required
def finalizar_entrevista(entrevista_id):
    """Encerra a entrevista e gera o relatório executivo final.

    Exige que todas as 10 perguntas já tenham resposta_usuario preenchida
    (400 caso contrário). Em sucesso, chama gerar_relatorio_final — que
    compila as avaliações de hard e soft skills em um parecer único — e
    grava o resultado em Entrevista.relatorio_final, junto com o status
    "concluida" e o timestamp finalizado_em."""
    entrevista = _get_entrevista_or_404(entrevista_id)
    if not entrevista:
        return jsonify({"error": "Entrevista não encontrada"}), 404
    
    # Verificar se todas perguntas foram respondidas
    nao_respondidas = PerguntaEntrevista.query.filter_by(
        entrevista_id=entrevista_id
    ).filter(PerguntaEntrevista.resposta_usuario == None).count()
    
    if nao_respondidas > 0:
        return jsonify({"error": "Ainda há perguntas não respondidas"}), 400
    
    try:
        # Gerar relatório
        logger.info(f"Gerando relatório final para entrevista {entrevista_id}")
        relatorio = gerar_relatorio_final(entrevista_id)
        
        # Atualizar entrevista
        entrevista.status = "concluida"
        entrevista.relatorio_final = relatorio
        entrevista.finalizado_em = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            "finalizado": True,
            "relatorio": relatorio
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao finalizar entrevista: {str(e)}")
        return jsonify({"error": "Erro ao gerar relatório"}), 500


@bp.route("/<entrevista_id>/relatorio", methods=["GET"])
@login_required
def relatorio(entrevista_id):
    """Página HTML do relatório final (entrevista_relatorio.html). Os
    dados do relatório em si são carregados via JS, chamando
    GET /entrevista/<id> e lendo o campo relatorio_final."""
    entrevista = _get_entrevista_or_404(entrevista_id)
    if not entrevista:
        return jsonify({"error": "Entrevista não encontrada"}), 404
    
    return render_template("entrevista_relatorio.html", entrevista_id=entrevista_id)


@bp.route("/<entrevista_id>/exportar-pdf", methods=["GET"])
@login_required
def exportar_pdf(entrevista_id):
    """Gera e devolve o relatório final da entrevista como PDF para
    download (gerar_pdf_relatorio_entrevista). Não exige que a entrevista
    esteja com status "concluida" no código desta rota — se chamada antes
    de /finalizar, gerar_pdf_relatorio_entrevista é quem decide como
    tratar um relatorio_final ainda vazio."""
    entrevista = _get_entrevista_or_404(entrevista_id)
    if not entrevista:
        return jsonify({"error": "Entrevista não encontrada"}), 404
    
    try:
        pdf_bytes = gerar_pdf_relatorio_entrevista(entrevista)
        
        return send_file(
            BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"relatorio_entrevista_{entrevista.id}.pdf"
        )
    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {str(e)}")
        return jsonify({"error": "Erro ao gerar PDF"}), 500
    
#comentario