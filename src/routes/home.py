from flask import Blueprint, render_template, session

from src.utils import login_required

bp = Blueprint("home", __name__)


@bp.route("/")
@login_required
def index():
    return render_template("home.html", user_name=session.get("user_name", ""))
