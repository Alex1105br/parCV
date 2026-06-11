"""Entrypoint for the application."""
from src.app import create_app
from src.db_init import init_db
import webbrowser
import os

app = create_app()

if __name__ == "__main__":
    init_db(app)
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        webbrowser.open("http://localhost:5000")
    app.run(host="::", port=5000, debug=True)