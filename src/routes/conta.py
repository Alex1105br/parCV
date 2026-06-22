"""Blueprint de configurações de conta do usuário.

Rotas:
    GET  /conta            → página HTML de configurações
    POST /conta/dados      → atualizar nome e informações de perfil
    POST /conta/senha      → alterar senha
    POST /conta/excluir    → excluir conta permanentemente
"""
from flask import Blueprint, jsonify, render_template, request, session, redirect, url_for

from src.app import limiter
from src.models.db import db
from src.models.user import User
from src.services import conta_service
from src.utils import login_required

bp = Blueprint("conta", __name__)


def _usuario_atual() -> User | None:
    """Retorna o User da sessão ou None."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


# ── Página principal ───────────────────────────────────────────────────────────

@bp.route("/conta")
@login_required
def conta():
    """Renderiza a página de configurações da conta."""
    user = _usuario_atual()
    return render_template(
        "conta.html",
        user=user,
        user_name=session.get("user_name", ""),
    )


# ── Atualizar dados cadastrais ─────────────────────────────────────────────────

@bp.route("/conta/dados", methods=["POST"])
@login_required
@limiter.limit("10/minute")
def atualizar_dados():
    """Atualiza nome e informações extras de perfil (exceto e-mail).

    Body (JSON):
        nome        (str, obrigatório)
        telefone    (str, opcional)
        profissao   (str, opcional)

    Respostas:
        200  { ok: true, name: "..." }
        400  { error: "mensagem de validação" }
    """
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    telefone = (data.get("telefone") or "").strip()
    profissao = (data.get("profissao") or "").strip()

    resultado = conta_service.atualizar_dados(
        user_id=session["user_id"],
        nome=nome,
        telefone=telefone,
        profissao=profissao,
    )

    if not resultado["ok"]:
        return jsonify({"error": resultado["error"]}), 400

    # Atualiza o nome na sessão para refletir na navbar imediatamente
    session["user_name"] = resultado["name"]
    return jsonify({"ok": True, "name": resultado["name"]}), 200


# ── Alterar senha ──────────────────────────────────────────────────────────────

@bp.route("/conta/senha", methods=["POST"])
@login_required
@limiter.limit("5/minute")
def alterar_senha():
    """Altera a senha após verificar a senha atual.

    Body (JSON):
        senha_atual       (str)
        nova_senha        (str)
        confirmar_senha   (str)

    Respostas:
        200  { ok: true }
        400  { error: "mensagem de validação" }
    """
    data = request.get_json(silent=True) or {}
    senha_atual = data.get("senha_atual", "")
    nova_senha = data.get("nova_senha", "")
    confirmar_senha = data.get("confirmar_senha", "")

    resultado = conta_service.alterar_senha(
        user_id=session["user_id"],
        senha_atual=senha_atual,
        nova_senha=nova_senha,
        confirmar_senha=confirmar_senha,
    )

    if not resultado["ok"]:
        return jsonify({"error": resultado["error"]}), 400

    return jsonify({"ok": True}), 200


# ── Excluir conta ──────────────────────────────────────────────────────────────

@bp.route("/conta/excluir", methods=["POST"])
@login_required
@limiter.limit("3/minute")
def excluir_conta():
    """Remove permanentemente o usuário e todos os seus dados.

    Body (JSON):
        senha  (str) — confirmação de identidade

    Respostas:
        200  { ok: true }          → frontend redireciona para /login
        400  { error: "..." }
    """
    data = request.get_json(silent=True) or {}
    senha = data.get("senha", "")

    resultado = conta_service.excluir_conta(
        user_id=session["user_id"],
        senha_confirmacao=senha,
    )

    if not resultado["ok"]:
        return jsonify({"error": resultado["error"]}), 400

    # Encerra a sessão antes de retornar
    session.clear()
    return jsonify({"ok": True}), 200
