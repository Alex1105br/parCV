def init_db(app):
    """
    Cria tabelas inexistentes e aplica colunas novas via ALTER TABLE.
    Usa IF NOT EXISTS — idempotente, seguro rodar múltiplas vezes.
    """
    from src.models.db import db
    import src.models.user         # noqa
    import src.models.analise      # noqa
    import src.models.otimizacao   # noqa
    import src.models.chat_session # noqa
    import src.models.entrevista   # noqa

    with app.app_context():
        db.create_all()
        print("[db] Tabelas criadas/verificadas.")
        _apply_column_migrations(db)


def _apply_column_migrations(db):
    """
    Aplica ALTER TABLE para colunas adicionadas após a criação inicial
    do banco (necessário em ambientes como Supabase onde db.create_all
    ignora tabelas já existentes).
    Cada entry é uma tupla (descricao, sql).
    """
    migrations = [
        (
            "reset_token em users",
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS reset_token VARCHAR(100),
            ADD COLUMN IF NOT EXISTS reset_token_expires_at TIMESTAMPTZ
            """,
        ),
        (
            "fixado_em em chat_session",
            """
            ALTER TABLE chat_session
            ADD COLUMN IF NOT EXISTS fixado_em TIMESTAMPTZ
            """,
        ),
        (
            "backfill fixado_em para fixadas legadas (sem fixado_em)",
            """
            UPDATE chat_session
            SET fixado_em = criado_em
            WHERE fixado = true AND fixado_em IS NULL
            """,
        ),
    ]

    with db.engine.connect() as conn:
        for descricao, sql in migrations:
            try:
                conn.execute(db.text(sql.strip()))
                conn.commit()
                print(f"[db] OK: {descricao}")
            except Exception as e:
                conn.rollback()
                print(f"[db] ERRO em '{descricao}': {e}")

    print("[db] Migrações de coluna concluídas.")