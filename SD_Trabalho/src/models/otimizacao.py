import uuid
from datetime import datetime, timezone

from src.models.db import db


class Otimizacao(db.Model):
    """Resultado de uma otimização/reescrita de currículo (rota POST
    /otimizar). Guarda o texto original e o texto otimizado (já com os
    marcadores ---SECAO:--- etc., consumidos por services/pdf.py para
    gerar o PDF) e a lista de melhorias aplicadas pela IA. analise_id é
    opcional — vincula a otimização a uma Analise prévia quando o
    usuário passou primeiro pelo fluxo de análise ATS, mas a otimização
    também pode ser feita isoladamente."""
    __tablename__ = "otimizacao"

    id                  = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    criado_em           = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    analise_id          = db.Column(db.String(36), db.ForeignKey("analise.id"), nullable=True)
    curriculo_original  = db.Column(db.Text, nullable=False)
    curriculo_otimizado = db.Column(db.Text, nullable=False)
    melhorias           = db.Column(db.JSON, nullable=False)
    vaga                = db.Column(db.Text, nullable=True)
    user_id             = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)

    analise = db.relationship("Analise", back_populates="otimizacoes")
    user    = db.relationship("User", back_populates="otimizacoes")