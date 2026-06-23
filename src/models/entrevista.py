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
    recomendações).

    `titulo` é gerado automaticamente na criação (ver
    services/model.gerar_titulo_entrevista, mesmo padrão usado em
    Analise.titulo) e pode ser renomeado manualmente pelo usuário
    (PATCH /entrevista/<id>/titulo) — exibido e editável na aba
    "Entrevistas" do Histórico (GET /entrevista/lista)."""
    __tablename__ = "entrevista"
    __table_args__ = (
        # Cobre exatamente o padrão de list_entrevistas: filtra por
        # user_id e ordena por criado_em desc. Sem índice, cada chamada
        # de /entrevista/lista faz sequential scan na tabela inteira
        # (de todos os usuários) — o índice composto resolve filtro e
        # ordenação numa busca só, sem precisar de 2 índices separados.
        db.Index("ix_entrevista_user_criado", "user_id", "criado_em"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    titulo = db.Column(db.String(100), nullable=False, default="")
    curriculo_id = db.Column(db.String(36), db.ForeignKey("curriculo.id"), nullable=True)

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
    curriculo = db.relationship("Curriculo", back_populates="entrevistas")
    perguntas = db.relationship("PerguntaEntrevista", back_populates="entrevista",
                                cascade="all, delete-orphan",
                                order_by="PerguntaEntrevista.numero_sequencial")


class PerguntaEntrevista(db.Model):
    """Uma das 10 perguntas de uma Entrevista (numero_sequencial 1-6 =
    hard skills, 7-10 = soft skills — convenção fixada no código de
    services/model.py, exposta aqui via a property `tema`).
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

    # Limite fixo de perguntas de hard skills (1 a HARD_SKILLS_LIMITE) antes
    # de passar para soft skills — mesma convenção usada na geração do plano
    # (services/model.py) e no cálculo do relatório final.
    HARD_SKILLS_LIMITE = 6

    @property
    def tema(self) -> str:
        """Categoria da pergunta, derivada de numero_sequencial: 'Hard skills'
        para as 6 primeiras, 'Soft skills' para as demais. Não é uma coluna
        própria — é calculada para manter uma única fonte da verdade com a
        regra já usada no relatório final (ver gerar_relatorio_final)."""
        if self.numero_sequencial <= self.HARD_SKILLS_LIMITE:
            return "Hard skills"
        return "Soft skills"