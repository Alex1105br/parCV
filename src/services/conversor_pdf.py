"""
Serviço de conversão de arquivos não-PDF para PDF.

Suporta:
    - .docx  → extrai texto via python-docx e gera PDF com ReportLab
    - .txt   → lê o texto e gera PDF com ReportLab

PDFs já são retornados sem nenhuma conversão (fluxo da Task 1).

Uso:
    pdf_bytes, nome_pdf, erro = converter_para_pdf(caminho, filename)

    Se `erro` for None, `pdf_bytes` contém o PDF pronto para persistência.
"""
from __future__ import annotations

import os
from io import BytesIO

import docx
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from src.logging_config import logger


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _texto_para_pdf(texto: str) -> bytes:
    """Converte texto plano para PDF usando ReportLab.

    Cada linha não-vazia vira um parágrafo; linhas em branco viram
    espaços verticais, preservando a estrutura visual do documento.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    estilos = getSampleStyleSheet()
    estilo_normal = ParagraphStyle(
        "CurriculoNormal",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        spaceAfter=2,
    )

    elementos = []
    for linha in texto.splitlines():
        linha_limpa = linha.strip()
        if linha_limpa:
            # Escapa caracteres especiais do ReportLab
            linha_safe = (
                linha_limpa
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            elementos.append(Paragraph(linha_safe, estilo_normal))
        else:
            elementos.append(Spacer(1, 4 * mm))

    if not elementos:
        elementos.append(Paragraph("(documento vazio)", estilo_normal))

    doc.build(elementos)
    return buffer.getvalue()


def _extrair_texto_docx(caminho: str) -> str:
    """Extrai o texto de um .docx preservando parágrafos."""
    doc = docx.Document(caminho)
    return "\n".join(p.text for p in doc.paragraphs)


def _extrair_texto_txt(caminho: str) -> str:
    """Lê um .txt em UTF-8 (com fallback para latin-1)."""
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(caminho, "r", encoding="latin-1") as f:
            return f.read()


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def converter_para_pdf(
    caminho: str,
    filename: str,
) -> tuple[bytes | None, str | None, str | None]:
    """Converte um arquivo não-PDF para PDF.

    Parâmetros
    ----------
    caminho   : caminho completo do arquivo salvo em disco.
    filename  : nome original do arquivo (usado para determinar extensão
                e montar o nome do PDF gerado).

    Retorno
    -------
    (pdf_bytes, nome_pdf, erro)
        - pdf_bytes : bytes do PDF gerado, ou None em caso de erro.
        - nome_pdf  : nome sugerido para o arquivo (ex: "curriculo.pdf").
        - erro      : mensagem de erro, ou None em caso de sucesso.
    """
    ext = os.path.splitext(filename)[1].lower()
    base = os.path.splitext(filename)[0]
    nome_pdf = f"{base}.pdf"

    try:
        if ext == ".docx":
            texto = _extrair_texto_docx(caminho)
        elif ext == ".txt":
            texto = _extrair_texto_txt(caminho)
        else:
            # Extensão desconhecida — não deveria chegar aqui, mas retorna
            # erro descritivo em vez de crashar.
            return None, None, f"Conversão não suportada para o formato: {ext}"

        if not texto or not texto.strip():
            return None, None, "Arquivo vazio ou sem texto extraível."

        pdf_bytes = _texto_para_pdf(texto)
        return pdf_bytes, nome_pdf, None

    except Exception as exc:
        logger.error(
            "conversor_pdf_erro",
            extra={"filename": filename, "erro": str(exc)},
        )
        return None, None, f"Erro ao converter arquivo para PDF: {exc}"
