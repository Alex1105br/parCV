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
    import src.models.curriculo    # noqa

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
        (
            "veredito em analise",
            """
            ALTER TABLE analise
            ADD COLUMN IF NOT EXISTS veredito JSON
            """,
        ),
        (
            "titulo em analise",
            """
            ALTER TABLE analise
            ADD COLUMN IF NOT EXISTS titulo VARCHAR(100) NOT NULL DEFAULT ''
            """,
        ),
        (
            "titulo em entrevista",
            """
            ALTER TABLE entrevista
            ADD COLUMN IF NOT EXISTS titulo VARCHAR(100) NOT NULL DEFAULT ''
            """,
        ),
        (
            "tabela curriculo",
            """
            CREATE TABLE IF NOT EXISTS curriculo (
                id            VARCHAR(36)  PRIMARY KEY,
                user_id       VARCHAR(36)  NOT NULL REFERENCES users(id),
                label         VARCHAR(80)  NOT NULL,
                hash_conteudo VARCHAR(64)  NOT NULL,
                texto         TEXT         NOT NULL,
                criado_em     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            )
            """,
        ),
        (
            "indice curriculo user_hash",
            """
            CREATE INDEX IF NOT EXISTS ix_curriculo_user_hash
            ON curriculo (user_id, hash_conteudo)
            """,
        ),
        (
            "unique curriculo user_label",
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'uq_curriculo_user_label'
                ) THEN
                    ALTER TABLE curriculo
                    ADD CONSTRAINT uq_curriculo_user_label UNIQUE (user_id, label);
                END IF;
            END $$
            """,
        ),
        (
            "curriculo_id em analise",
            """
            ALTER TABLE analise
            ADD COLUMN IF NOT EXISTS curriculo_id VARCHAR(36)
            REFERENCES curriculo(id) ON DELETE SET NULL
            """,
        ),
        (
            "curriculo_id em entrevista",
            """
            ALTER TABLE entrevista
            ADD COLUMN IF NOT EXISTS curriculo_id VARCHAR(36)
            REFERENCES curriculo(id) ON DELETE SET NULL
            """,
        ),
        (
            "cor em curriculo",
            """
            ALTER TABLE curriculo
            ADD COLUMN IF NOT EXISTS cor VARCHAR(7) NOT NULL DEFAULT '#6366f1'
            """,
        ),
        (
            "proximo_indice_cor em users",
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS proximo_indice_cor INTEGER NOT NULL DEFAULT 0
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