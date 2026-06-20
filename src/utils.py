import os
import re
import subprocess
from functools import wraps

import docx
from flask import session, redirect, url_for

from src.config import ALLOWED_EXTENSIONS


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def login_required(f):
    """Decorator: redireciona para /login se o usuário não estiver autenticado."""
    @wraps(f)
    def decorated(*args, **kwargs):
        """Wrapper que checa session["user_id"] antes de chamar a view
        original; devolve o redirect em vez de propagar a chamada se não
        houver sessão ativa."""
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def allowed_file(filename):
    """Checa se o nome do arquivo tem uma das extensões permitidas
    (definidas em config.ALLOWED_EXTENSIONS: txt, pdf, docx)."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def carregar_arquivo(caminho):
    """Extrai o texto de um arquivo .txt, .pdf ou .docx salvo em disco.
    PDF usa o binário externo `pdftotext` (precisa estar instalado no
    sistema); DOCX usa python-docx; TXT é lido direto como UTF-8.
    Retorna (texto, erro) — exatamente um dos dois é None."""
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
    """Escapa &, < e > para não quebrar o parser de XML/markup interno
    do ReportLab ao montar parágrafos do PDF."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def get_file_size(arquivo):
    """Calcula o tamanho em bytes de um arquivo enviado (FileStorage do
    Flask) sem consumir o stream — vai até o fim, lê a posição e volta
    pro início, deixando o arquivo pronto pra ser lido normalmente
    depois (ex: .save() ou .read())."""
    arquivo.seek(0, 2)
    size = arquivo.tell()
    arquivo.seek(0)
    return size


# ---------------------------------------------------------------------------
# Security helpers
# ---------------------------------------------------------------------------

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
    """Checagem determinística (regex) de padrões característicos de
    prompt injection, em português e inglês — ex: "ignore as instruções",
    "you are now", "[INST]", tokens de chat de sistema. Primeira camada
    de defesa, usada antes de qualquer texto livre do usuário ser
    enviado para a LLM (ver docs/ARQUITETURA.md, seção de segurança)."""
    return bool(_INJECTION_PATTERNS.search(text))


def sanitize_text(text, max_length=5000):
    """Remove tags HTML e caracteres de controle não-imprimíveis de um
    texto livre vindo do usuário, e trunca para max_length caracteres.
    Usada em todo input de texto antes de salvar no banco ou montar
    prompts para a LLM."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text[:max_length].strip()