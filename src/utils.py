import os
import subprocess

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
