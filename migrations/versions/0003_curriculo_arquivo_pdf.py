"""arquivo_pdf em curriculo — preserva o binário original do PDF enviado
pelo usuário (sem conversão/reprocessamento), permitindo visualização e
download fiéis ao arquivo enviado na tela /curriculos.

Revision ID: 0003_curriculo_arquivo_pdf
Revises: 0002_entrevista_titulo
Create Date: 2026-06-22

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003_curriculo_arquivo_pdf'
down_revision = '0002_entrevista_titulo'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'curriculo',
        sa.Column('arquivo_pdf', sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        'curriculo',
        sa.Column('arquivo_nome', sa.String(255), nullable=True),
    )
    op.add_column(
        'curriculo',
        sa.Column('arquivo_mimetype', sa.String(100), nullable=True,
                  server_default='application/pdf'),
    )


def downgrade():
    op.drop_column('curriculo', 'arquivo_mimetype')
    op.drop_column('curriculo', 'arquivo_nome')
    op.drop_column('curriculo', 'arquivo_pdf')
