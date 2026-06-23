"""Entrypoint for the application."""
from src.app import create_app
from src.db_init import init_db
import webbrowser
import os

app = create_app()

# Com debug=True, o Werkzeug sobe 2 processos: um "vigia" (reloader) e um
# filho que de fato serve as requisições. Os dois processos executam este
# módulo do início ao fim — o reloader funciona reimportando o script, não
# pulando o bloco __main__. A variável WERKZEUG_RUN_MAIN só vem definida
# como "true" no processo filho, então é ela (e não __name__) que diferencia
# "sou o processo que vai realmente atender requisições" de "sou só o
# vigia que vai reiniciar o filho quando um arquivo mudar". Por isso
# init_db roda só quando NÃO somos o processo vigia (ou seja: sem debug
# reloader, ou já dentro do processo filho).
is_watcher_process = __name__ == "__main__" and not os.environ.get("WERKZEUG_RUN_MAIN")

if not is_watcher_process:
    init_db(app)

if __name__ == "__main__":
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        webbrowser.open("http://localhost:5000")
    app.run(host="::", port=5000, debug=True)