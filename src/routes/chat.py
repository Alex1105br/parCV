import os

from flask import Blueprint, request, Response, session, jsonify
from werkzeug.utils import secure_filename

from src.config import UPLOAD_FOLDER
from src.services.ollama import stream_resposta
from src.utils import allowed_file, carregar_arquivo

bp = Blueprint("chat", __name__)


@bp.route("/chat")
def chat_page():
    if "historico" not in session:
        session["historico"] = []
    from flask import render_template
    return render_template("chat.html")


@bp.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    mensagem = data.get("mensagem", "").strip()
    if not mensagem:
        return jsonify({"error": "Mensagem vazia"}), 400

    historico = session.get("historico", [])

    def generate():
        yield from stream_resposta(historico, mensagem)
        session["historico"] = historico

    return Response(generate(), mimetype="text/event-stream")


@bp.route("/upload", methods=["POST"])
def upload():
    if "arquivo" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    arquivo = request.files["arquivo"]
    if arquivo.filename == "" or not allowed_file(arquivo.filename):
        return jsonify({"error": "Arquivo inválido"}), 400

    filename = secure_filename(arquivo.filename)
    caminho = os.path.join(UPLOAD_FOLDER, filename)
    arquivo.save(caminho)
    texto, erro = carregar_arquivo(caminho)
    os.remove(caminho)

    if erro:
        return jsonify({"error": erro}), 400

    historico = session.get("historico", [])
    historico.append({"role": "user", "content": f"Documento:\n\n{texto}\n\nUse para responder."})
    historico.append({"role": "assistant", "content": "Documento recebido."})
    session["historico"] = historico

    return jsonify({"success": True, "filename": filename, "chars": len(texto)})


@bp.route("/limpar", methods=["POST"])
def limpar():
    session["historico"] = []
    return jsonify({"success": True})

