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


def _colunas_existentes(conn, db, tabela, colunas):
    """Retorna o subconjunto de `colunas` que já existe na tabela `tabela`,
    consultando information_schema (leitura de metadado, não pega lock na
    tabela). Em caso de qualquer erro na consulta, retorna None — sinal para
    o chamador ignorar a checagem e seguir com o ALTER TABLE como antes
    (comportamento idêntico ao anterior, nunca pior)."""
    try:
        resultado = conn.execute(
            db.text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = :tabela
                  AND column_name = ANY(:colunas)
                """
            ),
            {"tabela": tabela.lower(), "colunas": [c.lower() for c in colunas]},
        )
        return {row[0] for row in resultado}
    except Exception:
        return None


def _apply_column_migrations(db):
    """
    Aplica ALTER TABLE para colunas adicionadas após a criação inicial
    do banco (necessário em ambientes como Supabase onde db.create_all
    ignora tabelas já existentes).

    Cada entry é uma tupla (descricao, sql, checagem), onde `checagem` é
    opcional: (tabela, [colunas]) que, se já existirem todas, faz a
    migração ser pulada sem nem tentar o ALTER TABLE — evita pegar lock
    na tabela à toa em todo restart do app quando a migração já foi
    aplicada anteriormente (isso era a causa de timeouts tipo
    "QueryCanceled: canceling statement due to statement timeout" em
    bancos remotos/lentos). Migrações sem checagem (CREATE TABLE/INDEX,
    constraints via DO block, UPDATE de backfill) continuam exatamente
    como antes — elas já são idempotentes por conta própria.
    """
    migrations = [
        (
            "reset_token em users",
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS reset_token VARCHAR(100),
            ADD COLUMN IF NOT EXISTS reset_token_expires_at TIMESTAMPTZ
            """,
            ("users", ["reset_token", "reset_token_expires_at"]),
        ),
        (
            "fixado_em em chat_session",
            """
            ALTER TABLE chat_session
            ADD COLUMN IF NOT EXISTS fixado_em TIMESTAMPTZ
            """,
            ("chat_session", ["fixado_em"]),
        ),
        (
            "backfill fixado_em para fixadas legadas (sem fixado_em)",
            """
            UPDATE chat_session
            SET fixado_em = criado_em
            WHERE fixado = true AND fixado_em IS NULL
            """,
            None,
        ),
        (
            "veredito em analise",
            """
            ALTER TABLE analise
            ADD COLUMN IF NOT EXISTS veredito JSON
            """,
            ("analise", ["veredito"]),
        ),
        (
            "titulo em analise",
            """
            ALTER TABLE analise
            ADD COLUMN IF NOT EXISTS titulo VARCHAR(100) NOT NULL DEFAULT ''
            """,
            ("analise", ["titulo"]),
        ),
        (
            "titulo em entrevista",
            """
            ALTER TABLE entrevista
            ADD COLUMN IF NOT EXISTS titulo VARCHAR(100) NOT NULL DEFAULT ''
            """,
            ("entrevista", ["titulo"]),
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
            None,
        ),
        (
            "indice curriculo user_hash",
            """
            CREATE INDEX IF NOT EXISTS ix_curriculo_user_hash
            ON curriculo (user_id, hash_conteudo)
            """,
            None,
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
            None,
        ),
        (
            "curriculo_id em analise",
            """
            ALTER TABLE analise
            ADD COLUMN IF NOT EXISTS curriculo_id VARCHAR(36)
            REFERENCES curriculo(id) ON DELETE SET NULL
            """,
            ("analise", ["curriculo_id"]),
        ),
        (
            "curriculo_id em entrevista",
            """
            ALTER TABLE entrevista
            ADD COLUMN IF NOT EXISTS curriculo_id VARCHAR(36)
            REFERENCES curriculo(id) ON DELETE SET NULL
            """,
            ("entrevista", ["curriculo_id"]),
        ),
        (
            "cor em curriculo",
            """
            ALTER TABLE curriculo
            ADD COLUMN IF NOT EXISTS cor VARCHAR(7) NOT NULL DEFAULT '#6366f1'
            """,
            ("curriculo", ["cor"]),
        ),
        (
            "proximo_indice_cor em users",
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS proximo_indice_cor INTEGER NOT NULL DEFAULT 0
            """,
            ("users", ["proximo_indice_cor"]),
        ),
        (
            "telefone e profissao em users",
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS telefone VARCHAR(20),
            ADD COLUMN IF NOT EXISTS profissao VARCHAR(100)
            """,
            ("users", ["telefone", "profissao"]),
        ),
    ]

    with db.engine.connect() as conn:
        for descricao, sql, checagem in migrations:
            if checagem:
                tabela, colunas = checagem
                existentes = _colunas_existentes(conn, db, tabela, colunas)
                if existentes is not None and set(c.lower() for c in colunas) <= existentes:
                    print(f"[db] OK (já existia, pulado): {descricao}")
                    continue
            try:
                conn.execute(db.text(sql.strip()))
                conn.commit()
                print(f"[db] OK: {descricao}")
            except Exception as e:
                conn.rollback()
                print(f"[db] ERRO em '{descricao}': {e}")

    print("[db] Migrações de coluna concluídas.")