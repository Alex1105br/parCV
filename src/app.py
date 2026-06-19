import os
import time
import uuid

from flask import Flask, jsonify, g, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from flask_migrate import Migrate

from src.config import UPLOAD_FOLDER, SECRET_KEY, DATABASE_URL, MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USE_SSL, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER, RESEND_API_KEY
from src.logging_config import setup_logging, logger, request_id_var
from src.models.db import db

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://",
)

# Instância global de Mail — inicializada dentro de create_app
mail = Mail()


def create_app():
    setup_logging()

    app = Flask(__name__)
    app.secret_key = SECRET_KEY or os.urandom(24)
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # ── Flask-Mail (SMTP) ──────────────────────────────────────────────────
    # Configure as variáveis abaixo no seu .env.
    # Exemplo para Gmail: MAIL_SERVER=smtp.gmail.com, MAIL_PORT=587,
    # MAIL_USE_TLS=True, MAIL_USERNAME=seu@gmail.com, MAIL_PASSWORD=app_password
    # Valores carregados via config.py (environs) — garante leitura correta do .env
    app.config["MAIL_SERVER"]   = MAIL_SERVER
    app.config["MAIL_PORT"]     = MAIL_PORT
    app.config["MAIL_USE_TLS"]  = MAIL_USE_TLS
    app.config["MAIL_USE_SSL"]  = MAIL_USE_SSL
    app.config["MAIL_USERNAME"] = MAIL_USERNAME
    app.config["MAIL_PASSWORD"] = MAIL_PASSWORD
    app.config["MAIL_DEFAULT_SENDER"] = MAIL_DEFAULT_SENDER

    logger.info(
        "mail_config_loaded",
        extra={
            "mail_server": app.config["MAIL_SERVER"],
            "mail_port": app.config["MAIL_PORT"],
            "mail_use_tls": app.config["MAIL_USE_TLS"],
            "mail_username_set": bool(app.config["MAIL_USERNAME"]),
            "mail_password_set": bool(app.config["MAIL_PASSWORD"]),
            "resend_api_key_set": bool(RESEND_API_KEY),
        },
    )
    # ─────────────────────────────────────────────────────────────────────

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    db.init_app(app)
    mail.init_app(app)
    Migrate(app, db)

    # Registra todos os models com o Alembic
    import src.models.user          # noqa: F401
    import src.models.analise       # noqa: F401
    import src.models.otimizacao    # noqa: F401
    import src.models.chat_session  # noqa: F401
    import src.models.entrevista    # noqa: F401

    limiter.init_app(app)

    @app.before_request
    def _before():
        rid = str(uuid.uuid4())[:8]
        request_id_var.set(rid)
        g.request_id = rid
        g.start_time = time.time()

    @app.after_request
    def _after(response):
        duration_ms = int((time.time() - g.start_time) * 1000)
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        response.headers["X-Request-Id"] = g.request_id
        return response

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({"error": "Muitas requisições. Aguarde antes de tentar novamente."}), 429

    from src.routes.auth import bp as auth_bp
    from src.routes.home import bp as home_bp
    from src.routes.chat import bp as chat_bp
    from src.routes.analisar import bp as analisar_bp
    from src.routes.entrevista import bp as entrevista_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(analisar_bp)
    app.register_blueprint(entrevista_bp)

    return app