"""Entrypoint for the application."""
from src.app import create_app
from src.db_init import init_db
import webbrowser
import os

app = create_app()

# Roda init_db sempre — inclusive no processo filho do reloader do Flask
# debug=True sobe dois processos; o filho não passa pelo bloco __main__,
# por isso init_db precisa ficar fora do if __name__.
init_db(app)

if __name__ == "__main__":
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        webbrowser.open("http://localhost:5000")
    app.run(host="::", port=5000, debug=True)