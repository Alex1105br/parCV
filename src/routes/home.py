from flask import Blueprint, render_template, session

from src.utils import login_required

bp = Blueprint("home", __name__)


@bp.route("/")
@login_required
def index():
    """Página inicial pós-login. Não lista dados — apenas renderiza
    home.html com o nome do usuário da sessão (usado no cabeçalho)."""
    return render_template("home.html", user_name=session.get("user_name", ""))