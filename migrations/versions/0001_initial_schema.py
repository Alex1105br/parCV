"""initial schema — cria todas as tabelas do zero

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-06-11
"""
from alembic import op
import sqlalchemy as sa

revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 1. users
    op.create_table(
        'users',
        sa.Column('id',        sa.String(36),              primary_key=True),
        sa.Column('name',      sa.String(100),             nullable=False),
        sa.Column('email',     sa.String(255),             nullable=False),
        sa.Column('password',  sa.String(255),             nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint('uq_users_email', 'users', ['email'])

    # 2. analise
    op.create_table(
        'analise',
        sa.Column('id',                      sa.String(36),              primary_key=True),
        sa.Column('user_id',                 sa.String(36),              sa.ForeignKey('users.id'), nullable=True),
        sa.Column('criado_em',               sa.DateTime(timezone=True), nullable=False),
        sa.Column('score_total',             sa.Integer(),               nullable=False),
        sa.Column('criterios',               sa.JSON(),                  nullable=False),
        sa.Column('pontos_fortes',           sa.JSON(),                  nullable=False),
        sa.Column('pontos_fracos',           sa.JSON(),                  nullable=False),
        sa.Column('sugestoes',               sa.JSON(),                  nullable=False),
        sa.Column('palavras_chave_faltando', sa.JSON(),                  nullable=False),
        sa.Column('certificados_sugeridos',  sa.JSON(),                  nullable=False),
        sa.Column('texto_original',          sa.Text(),                  nullable=False),
        sa.Column('vaga',                    sa.Text(),                  nullable=True),
    )

    # 3. otimizacao
    op.create_table(
        'otimizacao',
        sa.Column('id',                  sa.String(36),              primary_key=True),
        sa.Column('user_id',             sa.String(36),              sa.ForeignKey('users.id'),    nullable=True),
        sa.Column('analise_id',          sa.String(36),              sa.ForeignKey('analise.id'),  nullable=True),
        sa.Column('criado_em',           sa.DateTime(timezone=True), nullable=False),
        sa.Column('curriculo_original',  sa.Text(),                  nullable=False),
        sa.Column('curriculo_otimizado', sa.Text(),                  nullable=False),
        sa.Column('melhorias',           sa.JSON(),                  nullable=False),
        sa.Column('vaga',                sa.Text(),                  nullable=True),
    )

    # 4. chat_session
    op.create_table(
        'chat_session',
        sa.Column('id',            sa.String(36),              primary_key=True),
        sa.Column('user_id',       sa.String(36),              sa.ForeignKey('users.id'), nullable=True),
        sa.Column('titulo',        sa.String(100),             nullable=False, server_default=''),
        sa.Column('criado_em',     sa.DateTime(timezone=True), nullable=False),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('mensagens',     sa.JSON(),                  nullable=False),
        sa.Column('fixado',        sa.Boolean(),               nullable=False, server_default='false'),
    )


def downgrade():
    op.drop_table('chat_session')
    op.drop_table('otimizacao')
    op.drop_table('analise')
    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.drop_table('users')