"""initial schema — versão final do MVP, schema único consolidado

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 1. users — base de autenticação, todas as outras tabelas referenciam esta
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password', sa.String(255), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reset_token', sa.String(100), nullable=True),
        sa.Column('reset_token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('email', name='uq_users_email'),
    )

    # 2. analise — análises ATS de currículo
    op.create_table(
        'analise',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('score_total', sa.Integer(), nullable=False),
        sa.Column('criterios', sa.JSON(), nullable=False),
        sa.Column('pontos_fortes', sa.JSON(), nullable=False),
        sa.Column('pontos_fracos', sa.JSON(), nullable=False),
        sa.Column('sugestoes', sa.JSON(), nullable=False),
        sa.Column('palavras_chave_faltando', sa.JSON(), nullable=False),
        sa.Column('certificados_sugeridos', sa.JSON(), nullable=False),
        sa.Column('texto_original', sa.Text(), nullable=False),
        sa.Column('vaga', sa.Text(), nullable=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
    )

    # 3. chat_session — histórico de conversas do chat de carreira
    op.create_table(
        'chat_session',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('titulo', sa.String(100), nullable=False),
        sa.Column('titulo_gerado', sa.Boolean(), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('mensagens', sa.JSON(), nullable=False),
        sa.Column('fixado', sa.Boolean(), nullable=False),
        sa.Column('fixado_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
    )

    # 4. entrevista — simulações de entrevista (plano + execução)
    op.create_table(
        'entrevista',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('curriculo_arquivo', sa.String(255), nullable=False),
        sa.Column('vaga_descricao', sa.Text(), nullable=False),
        sa.Column('numero_perguntas', sa.Integer(), nullable=False),
        sa.Column('plano_entrevista', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finalizado_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('relatorio_final', sa.JSON(), nullable=True),
    )

    # 5. otimizacao — currículos otimizados (depende de analise e users)
    op.create_table(
        'otimizacao',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('analise_id', sa.String(36), sa.ForeignKey('analise.id'), nullable=True),
        sa.Column('curriculo_original', sa.Text(), nullable=False),
        sa.Column('curriculo_otimizado', sa.Text(), nullable=False),
        sa.Column('melhorias', sa.JSON(), nullable=False),
        sa.Column('vaga', sa.Text(), nullable=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
    )

    # 6. pergunta_entrevista — perguntas e respostas de cada entrevista (depende de entrevista)
    op.create_table(
        'pergunta_entrevista',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('entrevista_id', sa.String(36), sa.ForeignKey('entrevista.id'), nullable=False),
        sa.Column('numero_sequencial', sa.Integer(), nullable=False),
        sa.Column('pergunta_principal', sa.Text(), nullable=False),
        sa.Column('resposta_usuario', sa.Text(), nullable=True),
        sa.Column('avaliacao_resposta', sa.JSON(), nullable=True),
        sa.Column('perguntas_aprofundamento', sa.JSON(), nullable=True),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('respondido_em', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    # Ordem inversa, respeitando as foreign keys
    op.drop_table('pergunta_entrevista')
    op.drop_table('otimizacao')
    op.drop_table('entrevista')
    op.drop_table('chat_session')
    op.drop_table('analise')
    op.drop_table('users')