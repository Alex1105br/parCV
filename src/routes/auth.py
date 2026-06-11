import re

from flask import Blueprint, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from src.models.db import db
from src.models.user import User

bp = Blueprint("auth", __name__)

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str) -> bool:
    return bool(email and EMAIL_REGEX.match(email))


@bp.route("/login", methods=["GET", "POST"])
def login():
    # Já logado → vai para home
    if "user_id" in session:
        return redirect(url_for("home.index"))

    error = None
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            error = "Por favor, preencha todos os campos."
        elif not is_valid_email(email):
            error = "Digite um email válido."
        else:
            user = User.query.filter_by(email=email).first()
            if not user or not check_password_hash(user.password, password):
                # Mensagem genérica: não revela se o e-mail existe ou não
                error = "Email ou senha incorretos."
            else:
                session.clear()
                session["user_id"]   = user.id
                session["user_name"] = user.name
                return redirect(url_for("home.index"))

    return render_template("login.html", error=error)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("home.index"))

    error = None
    if request.method == "POST":
        name             = request.form.get("name", "").strip()
        email            = request.form.get("email", "").strip()
        password         = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not all([name, email, password, confirm_password]):
            error = "Por favor, preencha todos os campos."
        elif not is_valid_email(email):
            error = "Digite um email válido."
        elif len(password) < 8:
            error = "A senha deve ter pelo menos 8 caracteres."
        elif password != confirm_password:
            error = "As senhas não coincidem."
        elif User.query.filter_by(email=email).first():
            error = "Este email já está cadastrado."
        else:
            user = User(
                name=name,
                email=email,
                password=generate_password_hash(password),
            )
            db.session.add(user)
            db.session.commit()
            session.clear()
            session["user_id"]   = user.id
            session["user_name"] = user.name
            return redirect(url_for("home.index"))

    return render_template("register.html", error=error)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
