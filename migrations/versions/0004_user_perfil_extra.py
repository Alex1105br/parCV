"""perfil extra em users — telefone e profissao, exibidos e editáveis na
tela /conta (ver src/services/conta_service.atualizar_dados).

Revision ID: 0004_user_perfil_extra
Revises: 0003_curriculo_arquivo_pdf
Create Date: 2026-06-22

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0004_user_perfil_extra'
down_revision = '0003_curriculo_arquivo_pdf'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'users',
        sa.Column('telefone', sa.String(20), nullable=True),
    )
    op.add_column(
        'users',
        sa.Column('profissao', sa.String(100), nullable=True),
    )


def downgrade():
    op.drop_column('users', 'profissao')
    op.drop_column('users', 'telefone')
