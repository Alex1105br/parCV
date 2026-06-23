"""Índices compostos (user_id, criado_em) em analise e entrevista —
resolve sequential scan nas listagens paginadas /analises e
/entrevista/lista (GET), que filtram por user_id e ordenam por
criado_em desc. Usa CONCURRENTLY para não bloquear leituras/escritas
na tabela durante a criação do índice em produção (necessário rodar
fora de uma transação implícita — ver Connection autocommit abaixo).

Revision ID: 0005_indices_user_criado
Revises: 0004_user_perfil_extra
Create Date: 2026-06-22

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '0005_indices_user_criado'
down_revision = '0004_user_perfil_extra'
branch_labels = None
depends_on = None


def upgrade():
    # CREATE INDEX CONCURRENTLY não pode rodar dentro de uma transação.
    # op.get_context().autocommit_block() sai do BEGIN que o Alembic abre
    # por padrão, só para os comandos dentro do bloco.
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_analise_user_criado",
            "analise",
            ["user_id", "criado_em"],
            postgresql_concurrently=True,
        )
        op.create_index(
            "ix_entrevista_user_criado",
            "entrevista",
            ["user_id", "criado_em"],
            postgresql_concurrently=True,
        )


def downgrade():
    with op.get_context().autocommit_block():
        op.drop_index("ix_entrevista_user_criado", table_name="entrevista", postgresql_concurrently=True)
        op.drop_index("ix_analise_user_criado", table_name="analise", postgresql_concurrently=True)
