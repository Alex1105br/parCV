import os

from flask import Blueprint, render_template, request, session, jsonify, send_file
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

from src.app import limiter
from src.config import UPLOAD_FOLDER, MAX_UPLOAD_BYTES
from src.logging_config import logger
from src.models.analise import Analise
from src.models.curriculo import Curriculo
from src.models.db import db
from src.models.otimizacao import Otimizacao
from src.services.curriculo import obter_ou_criar_curriculo
from src.services.model import call_model, gerar_titulo_analise
from src.services.parser import extrair_json, extrair_texto_curriculo
from src.services.prompts import build_prompt_ats, build_prompt_otimizar
from src.services.pdf import gerar_pdf_curriculo
from src.utils import allowed_file, carregar_arquivo, get_file_size, sanitize_text, has_prompt_injection, login_required

bp = Blueprint("analisar", __name__)


@bp.route("/analisar", methods=["GET", "POST"])
@login_required
@limiter.limit("5 per minute; 30 per hour", methods=["POST"])
def analisar():
    """Análise ATS do currículo. GET renderiza a tela; POST recebe arquivo
    (+ vaga opcional), extrai o texto, valida prompt injection, chama a
    LLM (build_prompt_ats) e persiste o resultado em Analise. Mesmo se a
    persistência falhar, o resultado da análise é devolvido ao usuário —
    o erro de banco só é logado, não impede a resposta."""
    if request.method == "GET":
        return render_template("analisar.html")

    vaga = sanitize_text(request.form.get("vaga", ""))
    curriculo_id = (request.form.get("curriculo_id") or "").strip()

    curriculo_existente = None
    if curriculo_id:
        curriculo_existente = db.session.get(Curriculo, curriculo_id)
        if not curriculo_existente or curriculo_existente.user_id != session["user_id"]:
            return jsonify({"error": "Currículo não encontrado"}), 404

    if curriculo_existente:
        # Reaproveita um currículo já salvo em /curriculos — sem reler
        # arquivo nem reextrair texto, usa os dados já persistidos.
        filename = curriculo_existente.arquivo_nome or f"{curriculo_existente.label}.pdf"
        arquivo_pdf_bytes = curriculo_existente.arquivo_pdf
        texto = curriculo_existente.texto
    else:
        if "arquivo" not in request.files:
            return jsonify({"error": "Nenhum arquivo enviado"}), 400

        arquivo = request.files["arquivo"]

        if arquivo.filename == "" or not allowed_file(arquivo.filename):
            return jsonify({"error": "Arquivo inválido"}), 400

        if get_file_size(arquivo) > MAX_UPLOAD_BYTES:
            return jsonify({"error": "Arquivo muito grande. Limite: 5 MB"}), 413

        filename = secure_filename(arquivo.filename)
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        # Preserva o binário exato enviado quando já é PDF (Task 1) — sem
        # conversão/reprocessamento. Lido antes de salvar/extrair texto para
        # garantir que é exatamente o que o usuário enviou.
        arquivo_pdf_bytes = arquivo.read() if ext == "pdf" else None
        arquivo.seek(0)

        caminho = os.path.join(UPLOAD_FOLDER, filename)
        arquivo.save(caminho)
        texto, erro = carregar_arquivo(caminho)
        os.remove(caminho)

        if erro:
            return jsonify({"error": erro}), 400

        texto = sanitize_text(texto, max_length=20000)

    if has_prompt_injection(vaga) or has_prompt_injection(texto):
        return jsonify({"error": "Conteúdo inválido detectado"}), 422

    resposta, erro = call_model(build_prompt_ats(texto, vaga), num_predict=2200)
    if erro:
        return jsonify({"error": erro}), 500

    result = extrair_json(resposta)
    result["texto_original"] = texto

    titulo = gerar_titulo_analise(texto, vaga)
    result["titulo"] = titulo

    try:
        # Salva/reutiliza currículo centralizado (dedup por hash de conteúdo)
        curriculo = obter_ou_criar_curriculo(
            user_id=session["user_id"],
            texto=texto,
            finalidade=vaga or None,
            arquivo_pdf=arquivo_pdf_bytes,
            arquivo_nome=filename if arquivo_pdf_bytes else None,
            arquivo_mimetype="application/pdf" if arquivo_pdf_bytes else None,
        )

        analise = Analise(
            titulo=titulo,
            score_total=result.get("score_total", 0),
            criterios=result.get("criterios", {}),
            pontos_fortes=result.get("pontos_fortes", []),
            pontos_fracos=result.get("pontos_fracos", []),
            sugestoes=result.get("sugestoes", []),
            veredito=result.get("veredito"),
            palavras_chave_faltando=result.get("palavras_chave_faltando", []),
            certificados_sugeridos=result.get("certificados_sugeridos", []),
            texto_original=texto,
            vaga=vaga or None,
            user_id=session["user_id"],
            curriculo_id=curriculo.id if curriculo else None,
        )
        db.session.add(analise)
        db.session.commit()
        result["id"] = analise.id
    except Exception as e:
        db.session.rollback()
        logger.error("db_error", extra={"op": "salvar_analise", "erro": str(e)})

    return jsonify(result)


@bp.route("/analises", methods=["GET"])
@login_required
def list_analises():
    """Lista paginada (page/per_page, máx 50 por página) das análises do
    usuário logado, ordenadas da mais recente para a mais antiga. Devolve
    apenas um resumo de cada análise (sem os campos pesados como
    pontos_fortes/fracos) — para o detalhe completo, ver get_analise()."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 50)
    pagination = (
        Analise.query
        # joinedload traz o Curriculo relacionado já no JOIN da mesma
        # query (LEFT JOIN), em vez de 1 query extra por linha ao acessar
        # a.curriculo no loop abaixo (era um N+1: para per_page=20, isso
        # significava 1 + 20 = 21 idas ao banco; agora é 1 só).
        .options(joinedload(Analise.curriculo))
        .filter_by(user_id=session["user_id"])
        .order_by(Analise.criado_em.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return jsonify({
        "analises": [
            {
                "id": a.id,
                "titulo": a.titulo,
                "score_total": a.score_total,
                "criado_em": a.criado_em.isoformat(),
                "vaga": a.vaga,
                "curriculo_label": a.curriculo.label if a.curriculo else None,
                "curriculo_cor":   a.curriculo.cor if a.curriculo else None,
                "curriculo_id":    a.curriculo_id,
            }
            for a in pagination.items
        ],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
    })


@bp.route("/historico")
@login_required
def historico():
    """Página HTML de histórico de análises do usuário (dados carregados
    via JS, chamando GET /analises)."""
    return render_template("historico.html")


@bp.route("/historico/<string:analise_id>")
@login_required
def historico_detalhe(analise_id):
    """Página HTML de detalhe de uma análise específica (dados carregados
    via JS, chamando GET /analises/<analise_id>)."""
    return render_template("historico_detalhe.html", analise_id=analise_id)


@bp.route("/analises/<string:analise_id>", methods=["GET"])
@login_required
def get_analise(analise_id):
    """Dados completos de uma análise (todos os campos). 404 se não
    existir ou pertencer a outro usuário — checagem de posse feita aqui,
    não delegada ao banco (não há filtro user_id na query do get)."""
    analise = db.session.get(Analise, analise_id)
    if analise is None or analise.user_id != session["user_id"]:
        return jsonify({"error": "Análise não encontrada"}), 404
    
    # Preparar dados do currículo vinculado, se existir
    curriculo_data = None
    if analise.curriculo_id and analise.curriculo:
        curriculo_data = {
            "id": analise.curriculo.id,
            "label": analise.curriculo.label,
            "cor": analise.curriculo.cor,
            "tem_arquivo_pdf": analise.curriculo.arquivo_pdf is not None,
        }
    
    return jsonify({
        "id": analise.id,
        "titulo": analise.titulo,
        "criado_em": analise.criado_em.isoformat(),
        "score_total": analise.score_total,
        "criterios": analise.criterios,
        "pontos_fortes": analise.pontos_fortes,
        "pontos_fracos": analise.pontos_fracos,
        "sugestoes": analise.sugestoes,
        "veredito": analise.veredito,
        "palavras_chave_faltando": analise.palavras_chave_faltando,
        "certificados_sugeridos": analise.certificados_sugeridos,
        "vaga": analise.vaga,
        "curriculo": curriculo_data,
    })


@bp.route("/analises/<string:analise_id>/titulo", methods=["PATCH"])
@login_required
def renomear_analise(analise_id):
    """Renomeia manualmente o título de uma análise (gerado automaticamente
    na criação — ver gerar_titulo_analise). Mesmo padrão da rota análoga em
    /chat/sessao/<sid>/titulo."""
    analise = db.session.get(Analise, analise_id)
    if analise is None or analise.user_id != session["user_id"]:
        return jsonify({"error": "Análise não encontrada"}), 404
    data = request.get_json(silent=True) or {}
    titulo = sanitize_text(data.get("titulo", ""))[:100].strip()
    if not titulo:
        return jsonify({"error": "Título vazio"}), 400
    analise.titulo = titulo
    db.session.commit()
    return jsonify({"id": analise.id, "titulo": analise.titulo})


@bp.route("/analises/<string:analise_id>", methods=["DELETE"])
@login_required
def deletar_analise(analise_id):
    """Apaga definitivamente uma análise do histórico. 404 se não existir
    ou pertencer a outro usuário (mesma checagem de posse usada em
    get_analise/renomear_analise)."""
    analise = db.session.get(Analise, analise_id)
    if analise is None or analise.user_id != session["user_id"]:
        return jsonify({"error": "Análise não encontrada"}), 404
    try:
        db.session.delete(analise)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error("db_error", extra={"op": "deletar_analise", "erro": str(e)})
        return jsonify({"error": "Erro ao apagar análise"}), 500
    return jsonify({"ok": True})


@bp.route("/otimizar", methods=["POST"])
@login_required
@limiter.limit("5 per minute; 30 per hour")
def otimizar():
    """Reescreve o currículo otimizado para a vaga informada. Mesmo fluxo
    de validação/extração de /analisar (incluindo reaproveitamento de
    currículo salvo via curriculo_id, sem reler arquivo nem reextrair
    texto), mas usa build_prompt_otimizar e extrai o texto reescrito (com
    marcadores ---SECAO:--- etc., consumidos depois por services/pdf.py).
    O texto otimizado fica salvo em session["curriculo_otimizado"] para
    uso posterior por /otimizar/pdf sem precisar reenviar o texto inteiro."""
    vaga = sanitize_text(request.form.get("vaga", ""))
    curriculo_id = (request.form.get("curriculo_id") or "").strip()

    curriculo_existente = None
    if curriculo_id:
        curriculo_existente = db.session.get(Curriculo, curriculo_id)
        if not curriculo_existente or curriculo_existente.user_id != session["user_id"]:
            return jsonify({"error": "Currículo não encontrado"}), 404

    if curriculo_existente:
        # Reaproveita um currículo já salvo em /curriculos — sem reler
        # arquivo nem reextrair texto, usa os dados já persistidos.
        texto = curriculo_existente.texto
    else:
        if "arquivo" not in request.files:
            return jsonify({"error": "Nenhum arquivo enviado"}), 400

        arquivo = request.files["arquivo"]

        if arquivo.filename == "" or not allowed_file(arquivo.filename):
            return jsonify({"error": "Arquivo inválido"}), 400

        if get_file_size(arquivo) > MAX_UPLOAD_BYTES:
            return jsonify({"error": "Arquivo muito grande. Limite: 5 MB"}), 413

        filename = secure_filename(arquivo.filename)
        caminho = os.path.join(UPLOAD_FOLDER, filename)
        arquivo.save(caminho)

        texto, erro = carregar_arquivo(caminho)
        os.remove(caminho)

        if erro:
            return jsonify({"error": erro}), 400

        texto = sanitize_text(texto, max_length=20000)

    if has_prompt_injection(vaga) or has_prompt_injection(texto):
        return jsonify({"error": "Conteúdo inválido detectado"}), 422

    resposta, erro = call_model(
        build_prompt_otimizar(texto, vaga),
        num_predict=2000
    )

    if erro:
        return jsonify({"error": f"Erro ao conectar ao modelo: {erro}"}), 500

    curriculo_texto, melhorias = extrair_texto_curriculo(resposta)

    session["curriculo_otimizado"] = curriculo_texto

    response_data = {
        "curriculo_original": texto,
        "curriculo_otimizado": curriculo_texto,
        "melhorias": melhorias,
    }

    try:
        otimizacao = Otimizacao(
            curriculo_original=texto,
            curriculo_otimizado=curriculo_texto,
            melhorias=melhorias,
            vaga=vaga or None,
            user_id=session["user_id"],
        )
        db.session.add(otimizacao)
        db.session.commit()
        response_data["id"] = otimizacao.id
    except Exception as e:
        db.session.rollback()
        logger.error("db_error", extra={"op": "salvar_otimizacao", "erro": str(e)})

    return jsonify(response_data)


@bp.route("/otimizar/pdf", methods=["GET", "POST"])
@login_required
@limiter.limit("10 per minute", methods=["POST"])
def otimizar_pdf():
    """Gera o PDF do currículo otimizado. GET usa o texto já salvo em
    session["curriculo_otimizado"] (fluxo padrão pós-/otimizar); POST
    aceita texto explícito no body — usado quando o usuário editou o
    texto antes de exportar. Aceita foto opcional (jpg/png, ≤2MB) para o
    cabeçalho e template (classico/moderno/executivo, default classico —
    qualquer valor inválido cai silenciosamente para classico)."""
    if request.method == "POST":
        curriculo_texto = sanitize_text(request.form.get("texto", ""), max_length=20000)
        if not curriculo_texto:
            return jsonify({"error": "Nenhum texto enviado."}), 400
        if has_prompt_injection(curriculo_texto):
            return jsonify({"error": "Conteúdo inválido detectado"}), 422
        template = request.form.get("template", "classico")
    else:
        curriculo_texto = session.get("curriculo_otimizado")
        if not curriculo_texto:
            return jsonify({"error": "Nenhum currículo otimizado disponível."}), 400
        template = request.args.get("template", "classico")

    if template not in ("classico", "moderno", "executivo"):
        template = "classico"

    foto_bytes = None
    foto_file = request.files.get("foto")
    if foto_file and foto_file.filename:
        ext = foto_file.filename.rsplit(".", 1)[-1].lower() if "." in foto_file.filename else ""
        if ext in ("jpg", "jpeg", "png") and get_file_size(foto_file) <= 2 * 1024 * 1024:
            foto_bytes = foto_file.read()

    try:
        pdf_buffer = gerar_pdf_curriculo(curriculo_texto, template=template, foto_bytes=foto_bytes)
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"curriculo_{template}.pdf",
        )
    except Exception as e:
        return jsonify({"error": f"Erro ao gerar PDF: {str(e)}"}), 500