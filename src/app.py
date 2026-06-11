import os
import time
import uuid

from flask import Flask, jsonify, g, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate

from src.config import UPLOAD_FOLDER, SECRET_KEY, DATABASE_URL
from src.logging_config import setup_logging, logger, request_id_var
from src.models.db import db

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://",
)


def create_app():
    setup_logging()

    app = Flask(__name__)
    app.secret_key = SECRET_KEY or os.urandom(24)
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    db.init_app(app)
    Migrate(app, db)

    # Registra todos os models com o Alembic
    import src.models.user          # noqa: F401
    import src.models.analise       # noqa: F401
    import src.models.otimizacao    # noqa: F401
    import src.models.chat_session  # noqa: F401

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

    app.register_blueprint(auth_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(analisar_bp)

    return app
