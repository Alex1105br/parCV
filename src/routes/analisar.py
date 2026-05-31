import os

from flask import Blueprint, render_template, request, session, jsonify, send_file
from werkzeug.utils import secure_filename

from src.config import UPLOAD_FOLDER, MAX_UPLOAD_BYTES
from src.services.model import call_model
from src.services.parser import extrair_json, extrair_texto_curriculo
from src.services.prompts import build_prompt_ats, build_prompt_otimizar
from src.services.pdf import gerar_pdf_curriculo
from src.utils import allowed_file, carregar_arquivo, get_file_size, sanitize_text, has_prompt_injection

bp = Blueprint("analisar", __name__)


@bp.route("/analisar", methods=["GET", "POST"])
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
    return jsonify(result)


@bp.route("/otimizar", methods=["POST"])
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

    return jsonify({
        "curriculo_original": texto,
        "curriculo_otimizado": curriculo_texto,
        "melhorias": melhorias
    })


@bp.route("/otimizar/pdf", methods=["GET", "POST"])
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

    try:
        pdf_buffer = gerar_pdf_curriculo(curriculo_texto, template=template)
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"curriculo_{template}.pdf",
        )
    except Exception as e:
        return jsonify({"error": f"Erro ao gerar PDF: {str(e)}"}), 500
