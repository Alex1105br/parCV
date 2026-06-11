def init_db(app):
    from src.models.db import db
    import src.models.user         # noqa
    import src.models.analise      # noqa
    import src.models.otimizacao   # noqa
    import src.models.chat_session # noqa

    with app.app_context():
        db.create_all()
        print("[db] Tabelas criadas com sucesso.")