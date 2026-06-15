import os
import json
from datetime import datetime, timezone
from io import BytesIO

from flask import Blueprint, request, jsonify, render_template, session, send_file
from werkzeug.utils import secure_filename

from src.app import limiter
from src.config import UPLOAD_FOLDER, MAX_UPLOAD_BYTES
from src.logging_config import logger
from src.models.db import db
from src.models.entrevista import Entrevista, PerguntaEntrevista
from src.services.model import (
    gerar_plano_entrevista,
    avaliar_resposta,
    gerar_relatorio_final
)
from src.services.parser import extrair_texto_curriculo
from src.services.pdf import gerar_pdf_relatorio_entrevista
from src.utils import (
    login_required, allowed_file, carregar_arquivo, 
    sanitize_text, has_prompt_injection, get_file_size
)

bp = Blueprint("entrevista", __name__, url_prefix="/entrevista")


def _get_entrevista_or_404(entrevista_id: str):
    """Helper: pega entrevista ou 404"""
    entrevista = Entrevista.query.get(entrevista_id)
    if not entrevista or entrevista.user_id != session.get("user_id"):
        return None
    return entrevista


@bp.route("/", methods=["GET"])
@login_required
def entrevista_page():
    """Página inicial de planejamento"""
    return render_template("entrevista_planejamento.html")


@bp.route("/gerar-plano", methods=["POST"])
@login_required
@limiter.limit("5 per minute")
def gerar_plano():
    """Gera plano de entrevista a partir de currículo + vaga"""
    
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
        caminho = os.path.join(UPLOAD_FOLDER, filename)
        arquivo.save(caminho)
        
        # Extrair texto
        curriculo_text = extrair_texto_curriculo(caminho)
        os.remove(caminho)
        if not curriculo_text:
            return jsonify({"error": "Não foi possível extrair texto do currículo"}), 400
        
        # Chamar IA para gerar plano
        logger.info("Gerando plano de entrevista com IA")
        plano = gerar_plano_entrevista(curriculo_text, vaga_descricao)
        
        # Criar registro Entrevista
        entrevista = Entrevista(
            user_id=session["user_id"],
            curriculo_arquivo=filename,
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
            "numero_perguntas": plano["numero_perguntas"],
            "plano": {
                "topicos": plano["topicos_principais"],
                "estrategia": plano["estrategia_entrevista"],
                "questoes": plano["questoes_principais"]
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao gerar plano: {str(e)}")
        return jsonify({"error": "Erro ao gerar plano"}), 500



@bp.route("/<entrevista_id>/executar", methods=["GET"])
@login_required
def executar_entrevista(entrevista_id):
    """Serve a página de execução da entrevista"""
    entrevista = _get_entrevista_or_404(entrevista_id)
    if not entrevista:
        return "Entrevista não encontrada", 404
    return render_template("entrevista_execucao.html", entrevista_id=entrevista_id)






@bp.route("/<entrevista_id>", methods=["GET"])
@login_required
def get_entrevista(entrevista_id):
    """Retorna dados da entrevista"""
    entrevista = _get_entrevista_or_404(entrevista_id)
    if not entrevista:
        return jsonify({"error": "Entrevista não encontrada"}), 404
    
    return jsonify({
        "id": entrevista.id,
        "status": entrevista.status,
        "numero_perguntas": entrevista.numero_perguntas,
        "plano_entrevista": entrevista.plano_entrevista,
        "criado_em": entrevista.criado_em.isoformat(),
        "relatorio_final": entrevista.relatorio_final,
        "perguntas": [
            {
                "numero_sequencial": p.numero_sequencial,
                "pergunta_principal": p.pergunta_principal,
                "resposta_usuario": p.resposta_usuario,
                "respondido": p.resposta_usuario is not None,
                "avaliacao_resposta": p.avaliacao_resposta,
                "score": p.avaliacao_resposta.get("score") if p.avaliacao_resposta else None
            }
            for p in entrevista.perguntas
        ]
    }), 200


@bp.route("/<entrevista_id>/pergunta/<int:numero>", methods=["GET"])
@login_required
def get_pergunta(entrevista_id, numero):
    """Retorna pergunta específica"""
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
        "pergunta_principal": pergunta.pergunta_principal,
        "resposta_anterior": pergunta.resposta_usuario,
        "aprofundamentos_pendentes": len(pergunta.perguntas_aprofundamento or []) if pergunta.perguntas_aprofundamento else 0,
        "total_perguntas": entrevista.numero_perguntas
    }), 200


@bp.route("/<entrevista_id>/responder", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def responder_pergunta(entrevista_id):
    """Salva resposta e gera aprofundamentos se necessário"""
    entrevista = _get_entrevista_or_404(entrevista_id)
    if not entrevista:
        return jsonify({"error": "Entrevista não encontrada"}), 404
    
    data = request.get_json()
    numero_seq = data.get("numero_sequencial")
    resposta = sanitize_text(data.get("resposta", ""))
    tipo_resposta = data.get("tipo", "principal")
    
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
        
        # Aprofundamentos removidos — entrevista direta com 5 perguntas
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
    """Marca entrevista como concluída e gera relatório final"""
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
    """Exibe página do relatório"""
    entrevista = _get_entrevista_or_404(entrevista_id)
    if not entrevista:
        return jsonify({"error": "Entrevista não encontrada"}), 404
    
    return render_template("entrevista_relatorio.html", entrevista_id=entrevista_id)


@bp.route("/<entrevista_id>/exportar-pdf", methods=["GET"])
@login_required
def exportar_pdf(entrevista_id):
    """Exporta relatório em PDF"""
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
