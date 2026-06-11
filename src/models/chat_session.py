import uuid
from datetime import datetime, timezone

from src.models.db import db


class ChatSession(db.Model):
    __tablename__ = "chat_session"

    id           = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    titulo       = db.Column(db.String(100), nullable=False, default="")
    criado_em    = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    atualizado_em = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    mensagens    = db.Column(db.JSON, nullable=False, default=list)
    fixado       = db.Column(db.Boolean, nullable=False, default=False)
    user_id      = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)

    user = db.relationship("User", back_populates="chat_sessions")
