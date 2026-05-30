import os
import re
import subprocess

import docx

from src.config import ALLOWED_EXTENSIONS


def allowed_file(filename):
    """Check if filename has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def carregar_arquivo(caminho):
    """Load text content from a .txt or .pdf file. Returns (text, error)."""
    if not os.path.isfile(caminho):
        return None, "Arquivo não encontrado."

    ext = os.path.splitext(caminho)[1].lower()

    if ext == ".pdf":
        try:
            resultado = subprocess.run(
                ["pdftotext", caminho, "-"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if resultado.returncode != 0:
                return None, f"Erro ao converter PDF: {resultado.stderr.strip()}"
            texto = resultado.stdout.strip()
        except FileNotFoundError:
            return None, "pdftotext não encontrado."
    elif ext == ".docx":
        try:
            doc = docx.Document(caminho)
            texto = "\n".join(p.text for p in doc.paragraphs).strip()
        except Exception as e:
            return None, f"Erro ao ler DOCX: {e}"
    elif ext == ".txt":
        with open(caminho, "r", encoding="utf-8") as f:
            texto = f.read().strip()
    else:
        return None, f"Formato não suportado: {ext}"

    if not texto:
        return None, "Arquivo vazio ou sem texto extraível."

    return texto, None


def escape_xml(text):
    """Escape characters that break ReportLab's XML parser."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def get_file_size(arquivo):
    """Return file size in bytes without consuming the stream."""
    arquivo.seek(0, 2)
    size = arquivo.tell()
    arquivo.seek(0)
    return size


_INJECTION_PATTERNS = re.compile(
    r"ignore\s+(all\s+)?(previous|above|prior|these)?\s*(instructions?|rules?|context|prompt)"
    r"|(?:forget|disregard|override)\s+(?:everything|all|above|previous|prior|these|your)"
    r"|\byou\s+are\s+now\b|\bact\s+as\b"
    r"|\bpretend\s+(?:to\s+be|you\s+are)\b"
    r"|\byour\s+new\s+(?:role|task|persona|instructions?)\b"
    r"|\bignore\s+as\s+instru[cç][oõ]es\b|\besque[cç]a\b"
    r"|\bnovo\s+papel\b|\bfinja\s+(?:ser|que)\b"
    r"|\[/?INST\]|<\|(?:system|user|assistant)\|>"
    r"|\[(?:SYSTEM|USER|ASSISTANT)\]",
    re.IGNORECASE,
)


def has_prompt_injection(text):
    """Return True if text contains prompt injection patterns."""
    return bool(_INJECTION_PATTERNS.search(text))


def sanitize_text(text, max_length=5000):
    """Strip HTML tags and control characters. Limit length."""
    text = re.sub(r"<[^>]+>", "", text)
    # Remove null bytes and non-printable control chars (keep \t \n \r)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text[:max_length].strip()
