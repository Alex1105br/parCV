import re
import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from flask_mail import Message

from src.models.db import db
from src.models.user import User

bp = Blueprint("auth", __name__)

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str) -> bool:
    """Validação simples de formato (regex usuario@dominio.tld) — não checa
    existência real do domínio/caixa postal, só formato sintático."""
    return bool(email and EMAIL_REGEX.match(email))


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Tela e processamento de login. GET renderiza o formulário; POST
    valida email/senha contra o hash salvo e, se válido, inicia a sessão
    (session["user_id"], session["user_name"]) e redireciona para home.
    Já logado, redireciona direto para home sem mostrar o formulário."""
    if "user_id" in session:
        return redirect(url_for("home.index"))

    error = None
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")   # sem .strip() — preserva senha exata

        if not email or not password:
            error = "Por favor, preencha todos os campos."
        elif not is_valid_email(email):
            error = "Digite um email válido."
        else:
            user = User.query.filter_by(email=email).first()
            if not user or not check_password_hash(user.password, password):
                error = "Email ou senha incorretos."
            else:
                session.clear()
                session["user_id"]   = user.id
                session["user_name"] = user.name
                return redirect(url_for("home.index"))

    return render_template("login.html", error=error)


@bp.route("/register", methods=["GET", "POST"])
def register():
    """Tela e processamento de cadastro. Valida campos obrigatórios, formato
    de email, tamanho mínimo de senha (8), confirmação de senha e
    unicidade do email. Em sucesso, cria o User (senha já com hash),
    inicia a sessão e redireciona para home — mesmo comportamento pós-login
    do endpoint /login."""
    if "user_id" in session:
        return redirect(url_for("home.index"))

    error = None
    if request.method == "POST":
        name             = request.form.get("name", "").strip()
        email            = request.form.get("email", "").strip()
        password         = request.form.get("password", "")          # sem .strip()
        confirm_password = request.form.get("confirm_password", "")  # sem .strip()

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
    """Encerra a sessão atual (session.clear()) e volta para /login."""
    session.clear()
    return redirect(url_for("auth.login"))


# ---------------------------------------------------------------------------
# Recuperação de senha
# ---------------------------------------------------------------------------

@bp.route("/esqueci-senha", methods=["GET", "POST"])
def forgot_password():
    """Solicitação de redefinição de senha. Sempre devolve a mesma mensagem
    genérica, exista ou não o email — evita enumeração de usuários. Se o
    email existir, gera (ou reaproveita, caso ainda recente) um token
    válido por 1h e dispara o e-mail de redefinição via SMTP."""
    if "user_id" in session:
        return redirect(url_for("home.index"))

    message = None
    error   = None

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not email or not is_valid_email(email):
            error = "Digite um email válido."
        else:
            user = User.query.filter_by(email=email).first()
            # Resposta genérica — não revela se o e-mail existe
            if user:
                now = datetime.now(timezone.utc)

                # Se o token atual ainda tem mais de 59 minutos de validade
                # restante, significa que foi gerado há menos de 1 minuto —
                # reutiliza o mesmo em vez de gerar outro e reenviar e-mail.
                # Isso evita que cliques duplicados/refresh do navegador
                # invalidem o link que o usuário já recebeu.
                token_recente = (
                    user.reset_token
                    and user.reset_token_expires_at
                    and (user.reset_token_expires_at - now) > timedelta(minutes=59)
                )

                if not token_recente:
                    token = secrets.token_urlsafe(32)
                    user.reset_token            = token
                    user.reset_token_expires_at = now + timedelta(hours=1)
                    db.session.commit()
                    reset_url = url_for("auth.reset_password", token=token, _external=True)
                    _send_reset_email(user.email, user.name, reset_url)

            message = (
                "Se esse email estiver cadastrado, você receberá as instruções em breve. "
                "Verifique também a caixa de spam."
            )

    return render_template("forgot_password.html", message=message, error=error)


@bp.route("/redefinir-senha/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Tela e processamento de redefinição de senha a partir do link
    recebido por e-mail. Se o token não existir ou estiver expirado,
    renderiza a página em modo "expirado" (sem formulário). Em sucesso,
    atualiza a senha (hash) e invalida o token (uso único)."""
    if "user_id" in session:
        return redirect(url_for("home.index"))

    user = User.query.filter_by(reset_token=token).first()
    now  = datetime.now(timezone.utc)

    if not user or user.reset_token_expires_at is None or user.reset_token_expires_at < now:
        return render_template(
            "reset_password.html",
            token=token,
            expired=True,
            error=None,
        )

    error = None
    if request.method == "POST":
        password         = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not password or not confirm_password:
            error = "Preencha os dois campos."
        elif len(password) < 8:
            error = "A senha deve ter pelo menos 8 caracteres."
        elif password != confirm_password:
            error = "As senhas não coincidem."
        else:
            user.password               = generate_password_hash(password)
            user.reset_token            = None
            user.reset_token_expires_at = None
            db.session.commit()
            return redirect(url_for("auth.login") + "?reset=ok")

    return render_template("reset_password.html", token=token, expired=False, error=error)


def _send_reset_email(to_email: str, name: str, reset_url: str):
    """Envia e-mail de redefinição via SMTP tradicional (Flask-Mail / Gmail)."""
    text_body = (
        f"Olá, {name}!\n\n"
        f"Recebemos um pedido de redefinição de senha para a sua conta parCV.\n\n"
        f"Clique no link abaixo (válido por 1 hora):\n{reset_url}\n\n"
        f"Se você não solicitou isso, ignore este e-mail — sua senha permanece a mesma.\n\n"
        f"Equipe parCV"
    )
    html_body = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px;
                border:1px solid #e0e0e0;border-radius:12px;">
      <h2 style="color:#1a1a2e;margin-bottom:8px;">Redefinição de senha</h2>
      <p>Olá, <strong>{name}</strong>!</p>
      <p>Recebemos um pedido de redefinição de senha para a sua conta <strong>parCV</strong>.</p>
      <p style="margin:24px 0;">
        <a href="{reset_url}"
           style="background:#6c63ff;color:#fff;padding:12px 24px;border-radius:8px;
                  text-decoration:none;font-weight:600;display:inline-block;">
          Redefinir minha senha
        </a>
      </p>
      <p style="font-size:13px;color:#666;">
        Este link expira em <strong>1 hora</strong>.<br>
        Se você não solicitou isso, ignore este e-mail.
      </p>
    </div>
    """

    _send_via_smtp(to_email, html_body, text_body)


def _send_via_smtp(to_email: str, html_body: str, text_body: str) -> bool:
    """Envia via Flask-Mail (SMTP). Retorna True em caso de sucesso."""
    from src.logging_config import logger
    try:
        from src.app import mail
        msg = Message(
            subject="Redefinição de senha — parCV",
            recipients=[to_email],
        )
        msg.body = text_body
        msg.html = html_body
        mail.send(msg)
        return True
    except Exception as e:
        logger.error("mail_send_error", extra={"provedor": "smtp", "erro": str(e)})
        return False