import uuid
from datetime import datetime, timezone

from src.models.db import db


class User(db.Model):
    __tablename__ = "users"

    id        = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name      = db.Column(db.String(100), nullable=False)
    email     = db.Column(db.String(255), unique=True, nullable=False)
    password  = db.Column(db.String(255), nullable=False)
    criado_em = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Campos para recuperação de senha
    reset_token            = db.Column(db.String(100), nullable=True)
    reset_token_expires_at = db.Column(db.DateTime(timezone=True), nullable=True)

    analises      = db.relationship("Analise",     back_populates="user", lazy="dynamic")
    otimizacoes   = db.relationship("Otimizacao",  back_populates="user", lazy="dynamic")
    chat_sessions = db.relationship("ChatSession", back_populates="user", lazy="dynamic")
    entrevistas   = db.relationship("Entrevista",  back_populates="user", lazy="dynamic")
