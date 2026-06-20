import uuid
from datetime import datetime, timezone

from src.models.db import db


class Entrevista(db.Model):
    """Uma simulação de entrevista completa. Criada a partir de um
    currículo + descrição de vaga (POST /entrevista/gerar-plano), que a
    IA transforma em `plano_entrevista` (JSON com tópicos, estratégia e
    as 10 perguntas) e em 10 registros filhos `PerguntaEntrevista`
    (cascade delete: apagar a Entrevista apaga as perguntas).

    `status` segue em_planejamento -> em_andamento (na 1ª resposta) ->
    concluida (em /finalizar, que também preenche relatorio_final com o
    parecer executivo gerado pela IA: score geral, pontos fortes/fracos,
    recomendações)."""
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
    """Uma das 10 perguntas de uma Entrevista (numero_sequencial 1-6 =
    hard skills, 7-10 = soft skills — convenção fixada no código de
    services/model.py, não numa coluna própria desta tabela).
    `resposta_usuario` e `avaliacao_resposta` (JSON com score 0-10 e
    feedback da IA) ficam vazios até o usuário responder via POST
    /entrevista/<id>/responder. `perguntas_aprofundamento` existe no
    schema mas não é mais populada — a funcionalidade de perguntas de
    aprofundamento foi removida, a rota /responder sempre devolve
    aprofundamentos vazio."""
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