"""titulo em entrevista — título gerado automaticamente para simulações de
entrevista (mesmo padrão de Analise.titulo), exibido e editável na aba
"Entrevistas" do Histórico.

Revision ID: 0002_entrevista_titulo
Revises: 0001_initial
Create Date: 2026-06-21

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_entrevista_titulo'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'entrevista',
        sa.Column('titulo', sa.String(100), nullable=False, server_default=''),
    )


def downgrade():
    op.drop_column('entrevista', 'titulo')
