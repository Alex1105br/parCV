import uuid
from datetime import datetime, timezone

from src.models.db import db


class User(db.Model):
    """Usuário cadastrado no sistema. Senha armazenada como hash
    (werkzeug.security). Os campos reset_token/reset_token_expires_at
    suportam o fluxo de "esqueci minha senha" (token de uso único,
    válido por 1h). Ponto central do schema: toda análise, otimização,
    sessão de chat e entrevista pertence a um User."""
    __tablename__ = "users"

    id        = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name      = db.Column(db.String(100), nullable=False)
    email     = db.Column(db.String(255), unique=True, nullable=False)
    password  = db.Column(db.String(255), nullable=False)
    criado_em = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Campos para recuperação de senha
    reset_token            = db.Column(db.String(100), nullable=True)
    reset_token_expires_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Campos de perfil estendido (adicionados em 0004_user_perfil_extra)
    telefone  = db.Column(db.String(20),  nullable=True)
    profissao = db.Column(db.String(100), nullable=True)

    # Contador usado para distribuir automaticamente as cores das labels de
    # currículo em sequência round-robin (ver Curriculo.CORES_PERMITIDAS).
    # Sempre incrementa, nunca decresce — garante que a sequência de cores
    # não se repita por causa de currículos apagados (ver
    # curriculo.proxima_cor_automatica).
    proximo_indice_cor = db.Column(db.Integer, nullable=False, default=0,
                                    server_default="0")

    analises      = db.relationship("Analise",     back_populates="user", lazy="dynamic")
    otimizacoes   = db.relationship("Otimizacao",  back_populates="user", lazy="dynamic")
    chat_sessions = db.relationship("ChatSession", back_populates="user", lazy="dynamic")
    entrevistas   = db.relationship("Entrevista",  back_populates="user", lazy="dynamic")
    curriculos    = db.relationship("Curriculo",   back_populates="user", lazy="dynamic")