import os

from flask import Blueprint, render_template, request, session, jsonify, send_file
from werkzeug.utils import secure_filename

from src.config import UPLOAD_FOLDER
from src.services.model import call_model
from src.services.parser import extrair_json, extrair_texto_curriculo
from src.services.prompts import build_prompt_ats, build_prompt_otimizar
from src.services.pdf import gerar_pdf_curriculo
from src.utils import allowed_file, carregar_arquivo

bp = Blueprint("analisar", __name__)


@bp.route("/analisar", methods=["GET", "POST"])
def analisar():
    if request.method == "GET":
        return render_template("analisar.html")

    if "arquivo" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    arquivo = request.files["arquivo"]
    vaga = request.form.get("vaga", "").strip()

    if arquivo.filename == "" or not allowed_file(arquivo.filename):
        return jsonify({"error": "Arquivo inválido"}), 400

    filename = secure_filename(arquivo.filename)
    caminho = os.path.join(UPLOAD_FOLDER, filename)
    arquivo.save(caminho)
    texto, erro = carregar_arquivo(caminho)
    os.remove(caminho)

    if erro:
        return jsonify({"error": erro}), 400

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
    vaga = request.form.get("vaga", "").strip()

    if arquivo.filename == "" or not allowed_file(arquivo.filename):
        return jsonify({"error": "Arquivo inválido"}), 400

    filename = secure_filename(arquivo.filename)
    caminho = os.path.join(UPLOAD_FOLDER, filename)
    arquivo.save(caminho)

    texto, erro = carregar_arquivo(caminho)
    os.remove(caminho)

    if erro:
        return jsonify({"error": erro}), 400

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


@bp.route("/otimizar/pdf")
def otimizar_pdf():
    curriculo_texto = session.get("curriculo_otimizado")
    if not curriculo_texto:
        return jsonify({"error": "Nenhum currículo otimizado disponível."}), 400

    try:
        pdf_buffer = gerar_pdf_curriculo(curriculo_texto)
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="curriculo_otimizado.pdf",
        )
    except Exception as e:
        return jsonify({"error": f"Erro ao gerar PDF: {str(e)}"}), 500
