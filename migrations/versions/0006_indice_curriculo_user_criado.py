"""Índice composto (user_id, criado_em) em curriculo — resolve sequential
scan em GET /curriculos/ e GET /curriculos/lista, que filtram por user_id
e ordenam por criado_em desc. Mesma justificativa de
0005_indices_user_criado.py (analise/entrevista), agora para a tabela
curriculo.

Revision ID: 0006_indice_curriculo_user_criado
Revises: 0005_indices_user_criado
Create Date: 2026-06-22

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '0006_indice_curriculo_user_criado'
down_revision = '0005_indices_user_criado'
branch_labels = None
depends_on = None


def upgrade():
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_curriculo_user_criado",
            "curriculo",
            ["user_id", "criado_em"],
            postgresql_concurrently=True,
        )


def downgrade():
    with op.get_context().autocommit_block():
        op.drop_index("ix_curriculo_user_criado", table_name="curriculo", postgresql_concurrently=True)
