import os

from flask import Blueprint, render_template, request, session, jsonify, send_file
from werkzeug.utils import secure_filename

from src.app import limiter
from src.config import UPLOAD_FOLDER, MAX_UPLOAD_BYTES
from src.logging_config import logger
from src.models.analise import Analise
from src.models.db import db
from src.models.otimizacao import Otimizacao
from src.services.model import call_model
from src.services.parser import extrair_json, extrair_texto_curriculo
from src.services.prompts import build_prompt_ats, build_prompt_otimizar
from src.services.pdf import gerar_pdf_curriculo
from src.utils import allowed_file, carregar_arquivo, get_file_size, sanitize_text, has_prompt_injection, login_required

bp = Blueprint("analisar", __name__)


@bp.route("/analisar", methods=["GET", "POST"])
@login_required
@limiter.limit("5 per minute; 30 per hour", methods=["POST"])
def analisar():
    if request.method == "GET":
        return render_template("analisar.html")

    if "arquivo" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    arquivo = request.files["arquivo"]
    vaga = sanitize_text(request.form.get("vaga", ""))

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

    resposta, erro = call_model(build_prompt_ats(texto, vaga))
    if erro:
        return jsonify({"error": erro}), 500

    result = extrair_json(resposta)
    result["texto_original"] = texto

    try:
        analise = Analise(
            score_total=result.get("score_total", 0),
            criterios=result.get("criterios", {}),
            pontos_fortes=result.get("pontos_fortes", []),
            pontos_fracos=result.get("pontos_fracos", []),
            sugestoes=result.get("sugestoes", []),
            palavras_chave_faltando=result.get("palavras_chave_faltando", []),
            certificados_sugeridos=result.get("certificados_sugeridos", []),
            texto_original=texto,
            vaga=vaga or None,
            user_id=session["user_id"],
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
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 50)
    pagination = (
        Analise.query
        .filter_by(user_id=session["user_id"])
        .order_by(Analise.criado_em.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return jsonify({
        "analises": [
            {
                "id": a.id,
                "score_total": a.score_total,
                "criado_em": a.criado_em.isoformat(),
                "vaga": a.vaga,
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
    return render_template("historico.html")


@bp.route("/historico/<string:analise_id>")
@login_required
def historico_detalhe(analise_id):
    return render_template("historico_detalhe.html", analise_id=analise_id)


@bp.route("/analises/<string:analise_id>", methods=["GET"])
@login_required
def get_analise(analise_id):
    analise = db.session.get(Analise, analise_id)
    if analise is None or analise.user_id != session["user_id"]:
        return jsonify({"error": "Análise não encontrada"}), 404
    return jsonify({
        "id": analise.id,
        "criado_em": analise.criado_em.isoformat(),
        "score_total": analise.score_total,
        "criterios": analise.criterios,
        "pontos_fortes": analise.pontos_fortes,
        "pontos_fracos": analise.pontos_fracos,
        "sugestoes": analise.sugestoes,
        "palavras_chave_faltando": analise.palavras_chave_faltando,
        "certificados_sugeridos": analise.certificados_sugeridos,
        "vaga": analise.vaga,
    })


@bp.route("/otimizar", methods=["POST"])
@login_required
@limiter.limit("5 per minute; 30 per hour")
def otimizar():
    if "arquivo" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    arquivo = request.files["arquivo"]
    vaga = sanitize_text(request.form.get("vaga", ""))

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
