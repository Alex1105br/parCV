import uuid
from datetime import datetime, timezone

from src.models.db import db


class Entrevista(db.Model):
    __tablename__ = "entrevista"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    
    curriculo_arquivo = db.Column(db.String(255), nullable=False)
    vaga_descricao = db.Column(db.Text, nullable=False)
    numero_perguntas = db.Column(db.Integer, nullable=False)
    plano_entrevista = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='em_planejamento')
    
    criado_em = db.Column(db.DateTime(timezone=True), nullable=False, 
                          default=lambda: datetime.now(timezone.utc))
    atualizado_em = db.Column(db.DateTime(timezone=True), nullable=False,
                              default=lambda: datetime.now(timezone.utc))
    finalizado_em = db.Column(db.DateTime(timezone=True), nullable=True)
    
    relatorio_final = db.Column(db.JSON, nullable=True)

    user = db.relationship("User", back_populates="entrevistas")
    perguntas = db.relationship("PerguntaEntrevista", back_populates="entrevista",
                                cascade="all, delete-orphan")


class PerguntaEntrevista(db.Model):
    __tablename__ = "pergunta_entrevista"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entrevista_id = db.Column(db.String(36), db.ForeignKey("entrevista.id"), nullable=False)
    
    numero_sequencial = db.Column(db.Integer, nullable=False)
    pergunta_principal = db.Column(db.Text, nullable=False)
    resposta_usuario = db.Column(db.Text, nullable=True)
    avaliacao_resposta = db.Column(db.JSON, nullable=True)
    perguntas_aprofundamento = db.Column(db.JSON, nullable=True)
    
    criado_em = db.Column(db.DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))
    respondido_em = db.Column(db.DateTime(timezone=True), nullable=True)

    entrevista = db.relationship("Entrevista", back_populates="perguntas")
