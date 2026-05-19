import os

from flask import Flask

from src.config import UPLOAD_FOLDER, SECRET_KEY


def create_app():
    """Application factory — creates and configures the Flask app."""
    app = Flask(__name__)
    app.secret_key = SECRET_KEY or os.urandom(24)
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Register blueprints
    from src.routes.home import bp as home_bp
    from src.routes.chat import bp as chat_bp
    from src.routes.analisar import bp as analisar_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(analisar_bp)

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5005, debug=True)
