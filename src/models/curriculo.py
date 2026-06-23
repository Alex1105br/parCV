import uuid
import hashlib
from datetime import datetime, timezone

from src.models.db import db


class Curriculo(db.Model):
    """Currículo armazenado centralizado de um usuário.

    A deduplicação é feita por `hash_conteudo` (SHA-256 do texto extraído,
    normalizado) — independente de nome de arquivo, data ou tamanho.
    Dois currículos com conteúdo 100% idêntico geram o mesmo hash e apenas
    um registro é mantido.

    `label` é uma tag curta (máx 80 chars) gerada automaticamente pela LLM
    no momento do primeiro salvamento (ver curriculo.gerar_label).
    Deve ser única por usuário — se houver colisão, um sufixo numérico é
    adicionado automaticamente.

    `texto` armazena o texto extraído (sem o binário original) — conteúdo
    suficiente para reuso em análises/entrevistas futuras.

    `cor` é a cor da label/tag escolhida pelo usuário, em hexadecimal
    (ex: '#6366f1'). Deve ser um dos valores da paleta fixa definida em
    `CORES_PERMITIDAS`. O padrão é sempre o roxo da marca (COR_PADRAO).

    `curriculo_id` em Analise e Entrevista referencia este model (nullable
    para registros criados antes desta feature existir).
    """
    __tablename__ = "curriculo"

    # ── Paleta de cores disponível para a label ────────────────────────────
    # 30 cores fixas que o usuário pode escolher para identificar visualmente
    # cada currículo. A primeira (índice 0) é o roxo padrão da marca, usado
    # automaticamente em todo novo currículo até que o usuário altere.
    COR_PADRAO = "#6366f1"
    CORES_PERMITIDAS = [
        "#6366f1",  # roxo / índigo (padrão)
        "#8b5cf6",  # violeta
        "#a855f7",  # púrpura
        "#c026d3",  # fúcsia
        "#d946ef",  # magenta
        "#ec4899",  # rosa
        "#f43f5e",  # rosa avermelhado
        "#ef4444",  # vermelho
        "#dc2626",  # vermelho escuro
        "#f97316",  # laranja
        "#ea580c",  # laranja escuro
        "#f59e0b",  # âmbar
        "#a16207",  # âmbar escuro
        "#eab308",  # amarelo
        "#84cc16",  # lima
        "#4d7c0f",  # verde-oliva
        "#22c55e",  # verde
        "#15803d",  # verde escuro
        "#10b981",  # esmeralda
        "#14b8a6",  # verde-azulado
        "#0f766e",  # verde-azulado escuro
        "#06b6d4",  # ciano
        "#0ea5e9",  # azul-claro
        "#3b82f6",  # azul
        "#1d4ed8",  # azul escuro
        "#64748b",  # ardósia
        "#78716c",  # pedra
        "#374151",  # cinza-chumbo
        "#7e22ce",  # púrpura escuro
        "#be185d",  # rosa escuro
    ]

    id            = db.Column(db.String(36),  primary_key=True,
                              default=lambda: str(uuid.uuid4()))
    user_id       = db.Column(db.String(36),  db.ForeignKey("users.id"), nullable=False)
    label         = db.Column(db.String(80),  nullable=False)
    cor           = db.Column(db.String(7),   nullable=False, default=COR_PADRAO,
                              server_default=COR_PADRAO)
    hash_conteudo = db.Column(db.String(64),  nullable=False)   # SHA-256 hex
    texto         = db.Column(db.Text,        nullable=False)
    criado_em     = db.Column(db.DateTime(timezone=True), nullable=False,
                              default=lambda: datetime.now(timezone.utc))

    # ── Arquivo PDF original ───────────────────────────────────────────────
    # Quando o usuário envia um PDF, o binário exato enviado é preservado
    # aqui (sem conversão/reprocessamento). Para outros formatos suportados
    # (docx/doc/txt) este campo é populado com o PDF gerado a partir da
    # conversão (ver Task 2 / src.services.conversao) — nunca fica vazio
    # após o fluxo completo de upload.
    arquivo_pdf      = db.Column(db.LargeBinary, nullable=True)
    arquivo_nome     = db.Column(db.String(255), nullable=True)
    arquivo_mimetype = db.Column(db.String(100), nullable=True, default="application/pdf")

    user      = db.relationship("User",     back_populates="curriculos")
    analises  = db.relationship("Analise",  back_populates="curriculo", lazy="dynamic")
    entrevistas = db.relationship("Entrevista", back_populates="curriculo", lazy="dynamic")

    # ── índices ─────────────────────────────────────────────────────────
    # ix_curriculo_user_hash: usado na dedup (busca por user_id+hash_conteudo).
    # ix_curriculo_user_criado: cobre listar()/listar_api() (WHERE user_id
    # = ... ORDER BY criado_em DESC) — mesmo padrão usado em Analise e
    # Entrevista (ver models/analise.py e models/entrevista.py).
    __table_args__ = (
        db.Index("ix_curriculo_user_hash", "user_id", "hash_conteudo"),
        db.Index("ix_curriculo_user_criado", "user_id", "criado_em"),
        db.UniqueConstraint("user_id", "label", name="uq_curriculo_user_label"),
    )

    @staticmethod
    def calcular_hash(texto: str) -> str:
        """SHA-256 do texto normalizado (lowercase + espaços colapsados).
        Garante que variações insignificantes de espaçamento/capitalização
        não gerem duplicatas."""
        normalizado = " ".join(texto.lower().split())
        return hashlib.sha256(normalizado.encode("utf-8")).hexdigest()