"""add users table and user_id foreign keys

Revision ID: a1b2c3d4e5f6
Revises: 8ed8058846bf
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '8ed8058846bf'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Tabela de usuários
    op.create_table(
        'users',
        sa.Column('id',        sa.String(36),  primary_key=True),
        sa.Column('name',      sa.String(100), nullable=False),
        sa.Column('email',     sa.String(255), nullable=False),
        sa.Column('password',  sa.String(255), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint('uq_users_email', 'users', ['email'])

    # 2. Adiciona user_id nas tabelas existentes (nullable para não quebrar dados antigos)
    op.add_column('analise',      sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True))
    op.add_column('otimizacao',   sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True))
    op.add_column('chat_session', sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True))


def downgrade():
    op.drop_column('chat_session', 'user_id')
    op.drop_column('otimizacao',   'user_id')
    op.drop_column('analise',      'user_id')
    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.drop_table('users')
