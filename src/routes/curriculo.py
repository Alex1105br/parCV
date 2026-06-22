from flask import Blueprint, jsonify, render_template, request, session, send_file
import io

from src.logging_config import logger
from src.models.curriculo import Curriculo
from src.models.db import db
from src.services.curriculo import renomear_label, alterar_cor
from src.utils import login_required, sanitize_text

bp = Blueprint("curriculo", __name__, url_prefix="/curriculos")


@bp.route("/", methods=["GET"])
@login_required
def curriculos_page():
    """Página HTML de gestão de currículos (dados carregados via JS)."""
    return render_template("curriculos.html", user_name=session.get("user_name", ""))


@bp.route("/cores", methods=["GET"])
@login_required
def listar_cores():
    """Devolve a paleta fixa de cores disponíveis para a label, e qual
    delas é o padrão (usado em todo novo currículo)."""
    return jsonify({
        "cores": Curriculo.CORES_PERMITIDAS,
        "cor_padrao": Curriculo.COR_PADRAO,
    })


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
                "cor":       c.cor,
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
                "cor":             c.cor,
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
        "cor":       c.cor,
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


@bp.route("/<string:curriculo_id>/cor", methods=["PATCH"])
@login_required
def editar_cor(curriculo_id):
    """Altera a cor da label de um currículo.

    A cor deve ser exatamente uma das opções da paleta fixa devolvida por
    GET /curriculos/cores — qualquer outro valor é rejeitado.
    """
    c = db.session.get(Curriculo, curriculo_id)
    if not c or c.user_id != session["user_id"]:
        return jsonify({"error": "Currículo não encontrado"}), 404

    data = request.get_json(silent=True) or {}
    nova_cor = (data.get("cor") or "").strip()
    if not nova_cor:
        return jsonify({"error": "Cor não informada"}), 400

    ok, erro = alterar_cor(c, nova_cor)
    if not ok:
        return jsonify({"error": erro}), 400

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error("db_error", extra={"op": "editar_cor_curriculo", "erro": str(e)})
        return jsonify({"error": "Erro ao salvar"}), 500

    return jsonify({"id": c.id, "cor": c.cor})


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