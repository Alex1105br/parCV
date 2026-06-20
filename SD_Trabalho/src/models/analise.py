import uuid
from datetime import datetime, timezone

from src.models.db import db


class Analise(db.Model):
    """Resultado de uma análise ATS de currículo (rota POST /analisar).
    Guarda o score e o detalhamento devolvidos pela LLM: critérios
    avaliados (cada um com nota E motivo — ver build_prompt_ats), pontos
    fortes/fracos, sugestões, veredito (parecer direto sobre o real
    encaixe do candidato na vaga, com recomendação de outros perfis de
    vaga), palavras-chave da vaga ausentes no currículo e certificações
    sugeridas — todos como JSON, já que são listas/dicts de tamanho
    variável sem necessidade de query relacional própria.
    `veredito` é nullable porque análises feitas antes dessa funcionalidade
    existir não têm esse campo — o frontend trata a ausência dele
    simplesmente não exibindo a seção. user_id é opcional (nullable) para
    suportar análises feitas antes de qualquer vínculo de usuário ser
    obrigatório no fluxo."""
    __tablename__ = "analise"

    id                     = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    criado_em              = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    titulo                 = db.Column(db.String(100), nullable=False, default="")
    score_total            = db.Column(db.Integer, nullable=False)
    criterios              = db.Column(db.JSON, nullable=False)
    pontos_fortes          = db.Column(db.JSON, nullable=False)
    pontos_fracos          = db.Column(db.JSON, nullable=False)
    sugestoes              = db.Column(db.JSON, nullable=False)
    veredito               = db.Column(db.JSON, nullable=True)
    palavras_chave_faltando = db.Column(db.JSON, nullable=False)
    certificados_sugeridos = db.Column(db.JSON, nullable=False)
    texto_original         = db.Column(db.Text, nullable=False)
    vaga                   = db.Column(db.Text, nullable=True)
    user_id                = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)

    user        = db.relationship("User", back_populates="analises")
    otimizacoes = db.relationship("Otimizacao", back_populates="analise", lazy="dynamic")