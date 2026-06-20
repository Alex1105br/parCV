import uuid
from datetime import datetime, timezone

from src.models.db import db


class ChatSession(db.Model):
    """Uma conversa do chat de carreira. `mensagens` guarda o histórico
    completo como JSON (lista de {role, content, ...}), incluindo a
    mensagem de system prompt — rotas de leitura (ex: GET
    /chat/sessao/<sid>) filtram o que é exibido ao usuário.
    `titulo_gerado` controla se o título já foi definido (manualmente ou
    pela IA, na primeira mensagem) para não ser sobrescrito depois.
    `fixado` controla a exibição na seção "fixadas" da barra lateral."""
    __tablename__ = "chat_session"

    id           = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    titulo       = db.Column(db.String(100), nullable=False, default="")
    titulo_gerado = db.Column(db.Boolean, nullable=False, default=False)
    criado_em    = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    atualizado_em = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    mensagens    = db.Column(db.JSON, nullable=False, default=list)
    fixado       = db.Column(db.Boolean, nullable=False, default=False)
    user_id      = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)

    user = db.relationship("User", back_populates="chat_sessions")