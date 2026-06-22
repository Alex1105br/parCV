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
    no momento do primeiro salvamento (ver curriculo_service.gerar_label).
    Deve ser única por usuário — se houver colisão, um sufixo numérico é
    adicionado automaticamente.

    `texto` armazena o texto extraído (sem o binário original) — conteúdo
    suficiente para reuso em análises/entrevistas futuras.

    `curriculo_id` em Analise e Entrevista referencia este model (nullable
    para registros criados antes desta feature existir).
    """
    __tablename__ = "curriculo"

    id            = db.Column(db.String(36),  primary_key=True,
                              default=lambda: str(uuid.uuid4()))
    user_id       = db.Column(db.String(36),  db.ForeignKey("users.id"), nullable=False)
    label         = db.Column(db.String(80),  nullable=False)
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

    # ── índice composto para tornar a busca de dedup instantânea ──────────
    __table_args__ = (
        db.Index("ix_curriculo_user_hash", "user_id", "hash_conteudo"),
        db.UniqueConstraint("user_id", "label", name="uq_curriculo_user_label"),
    )

    @staticmethod
    def calcular_hash(texto: str) -> str:
        """SHA-256 do texto normalizado (lowercase + espaços colapsados).
        Garante que variações insignificantes de espaçamento/capitalização
        não gerem duplicatas."""
        normalizado = " ".join(texto.lower().split())
        return hashlib.sha256(normalizado.encode("utf-8")).hexdigest()