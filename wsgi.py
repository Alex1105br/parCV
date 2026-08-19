"""Entrypoint para produção (Gunicorn/Render).

Diferente do run.py (desenvolvimento local), aqui não abrimos o browser
nem rodamos o servidor de desenvolvimento do Flask. O Gunicorn importa
este módulo, chama create_app() e serve a aplicação diretamente.

O init_db roda uma vez no boot do worker principal para garantir que
todas as tabelas e migrações de coluna estejam aplicadas antes de
qualquer requisição ser servida.
"""
from src.app import create_app
from src.db_init import init_db

app = create_app()

# Roda as migrações no boot — idempotente, seguro rodar a cada deploy.
# Em produção não há reloader do Werkzeug, então init_db roda exatamente
# uma vez por processo worker.
with app.app_context():
    init_db(app)
