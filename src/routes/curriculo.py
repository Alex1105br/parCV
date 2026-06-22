from flask import Blueprint, jsonify, render_template, request, session, send_file
import io

from src.logging_config import logger
from src.models.curriculo import Curriculo
from src.models.db import db
from src.services.curriculo_service import renomear_label
from src.utils import login_required, sanitize_text

bp = Blueprint("curriculo", __name__, url_prefix="/curriculos")


@bp.route("/", methods=["GET"])
@login_required
def curriculos_page():
    """Página HTML de gestão de currículos (dados carregados via JS)."""
    return render_template("curriculos.html")


@bp.route("/", methods=["GET"])
@login_required
def listar():
    """Lista todos os currículos do usuário logado, do mais recente ao mais antigo."""
    curriculos = (
        Curriculo.query
        .filter_by(user_id=session["user_id"])
        .order_by(Curriculo.criado_em.desc())
        .all()
    )
    return jsonify({
        "curriculos": [
            {
                "id":        c.id,
                "label":     c.label,
                "criado_em": c.criado_em.isoformat(),
                "preview":   c.texto[:200].replace("\n", " "),
            }
            for c in curriculos
        ]
    })


@bp.route("/lista", methods=["GET"])
@login_required
def listar_api():
    """API JSON: lista todos os currículos do usuário logado.

    A listagem trabalha exclusivamente com a versão PDF de cada currículo
    (original ou convertida nas Tasks 1/2) — não retorna mais o texto extraído.
    """
    curriculos = (
        Curriculo.query
        .filter_by(user_id=session["user_id"])
        .order_by(Curriculo.criado_em.desc())
        .all()
    )
    return jsonify({
        "curriculos": [
            {
                "id":              c.id,
                "label":           c.label,
                "criado_em":       c.criado_em.isoformat(),
                "arquivo_nome":    c.arquivo_nome,
                "tem_arquivo_pdf": c.arquivo_pdf is not None,
            }
            for c in curriculos
        ]
    })


@bp.route("/<string:curriculo_id>", methods=["GET"])
@login_required
def get_curriculo(curriculo_id):
    """Retorna texto completo de um currículo."""
    c = db.session.get(Curriculo, curriculo_id)
    if not c or c.user_id != session["user_id"]:
        return jsonify({"error": "Currículo não encontrado"}), 404
    return jsonify({
        "id":        c.id,
        "label":     c.label,
        "texto":     c.texto,
        "criado_em": c.criado_em.isoformat(),
    })


@bp.route("/<string:curriculo_id>/label", methods=["PATCH"])
@login_required
def editar_label(curriculo_id):
    """Edita a label de um currículo garantindo unicidade."""
    c = db.session.get(Curriculo, curriculo_id)
    if not c or c.user_id != session["user_id"]:
        return jsonify({"error": "Currículo não encontrado"}), 404

    data = request.get_json(silent=True) or {}
    nova_label = sanitize_text(data.get("label", "")).strip()
    if not nova_label:
        return jsonify({"error": "Label vazia"}), 400

    ok, erro = renomear_label(c, nova_label, session["user_id"])
    if not ok:
        return jsonify({"error": erro}), 400

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error("db_error", extra={"op": "editar_label_curriculo", "erro": str(e)})
        return jsonify({"error": "Erro ao salvar"}), 500

    return jsonify({"id": c.id, "label": c.label})


@bp.route("/<string:curriculo_id>", methods=["DELETE"])
@login_required
def deletar_curriculo(curriculo_id):
    """Apaga um currículo permanentemente."""
    c = db.session.get(Curriculo, curriculo_id)
    if not c or c.user_id != session["user_id"]:
        return jsonify({"error": "Currículo não encontrado"}), 404
    try:
        db.session.delete(c)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error("db_error", extra={"op": "deletar_curriculo", "erro": str(e)})
        return jsonify({"error": "Erro ao apagar"}), 500
    return jsonify({"ok": True})


@bp.route("/pdf/<string:curriculo_id>", methods=["GET"])
@login_required
def visualizar_pdf(curriculo_id):
    """Retorna o binário do PDF para visualização no iframe."""
    c = db.session.get(Curriculo, curriculo_id)
    if not c or c.user_id != session["user_id"]:
        return "Currículo não encontrado", 404

    if not c.arquivo_pdf:
        return "Arquivo PDF não disponível", 404

    return send_file(
        io.BytesIO(c.arquivo_pdf),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=c.arquivo_nome or f"{c.label}.pdf"
    )


@bp.route("/download/<string:curriculo_id>", methods=["GET"])
@login_required
def baixar_pdf(curriculo_id):
    """Força o download do arquivo PDF."""
    c = db.session.get(Curriculo, curriculo_id)
    if not c or c.user_id != session["user_id"]:
        return "Currículo não encontrado", 404

    if not c.arquivo_pdf:
        return "Arquivo PDF não disponível", 404

    return send_file(
        io.BytesIO(c.arquivo_pdf),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=c.arquivo_nome or f"{c.label}.pdf"
    )