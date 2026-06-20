from pathlib import Path

from environs import Env, EnvValidationError
from marshmallow.validate import OneOf

env = Env()
env.read_env(Path(__file__).resolve().parent.parent / ".env", recurse=False)

# ===== LLM Backend =====
LLM_BACKEND = env.str(
    "LLM_BACKEND", default="groq", validate=OneOf(["groq", "ollama"])
).lower()

# --- Groq ---
GROQ_API_KEY = env.str("GROQ_API_KEY", default="")
GROQ_MODEL = env.str("GROQ_MODEL", default="llama-3.3-70b-versatile")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

if LLM_BACKEND == "groq" and not GROQ_API_KEY:
    raise EnvValidationError("GROQ_API_KEY é obrigatória quando LLM_BACKEND=groq")

# --- Ollama (local) ---
_raw = env.str("OLLAMA_HOST", default="") or env.str("OLLAMA_URL", default="http://localhost:11434")
OLLAMA_HOST = _raw.rsplit("/api/", 1)[0] if "/api/" in _raw else _raw
OLLAMA_CHAT_URL = f"{OLLAMA_HOST}/api/chat"
OLLAMA_GENERATE_URL = f"{OLLAMA_HOST}/api/generate"

# --- Shared ---
MODEL = env.str("MODEL", default="qwen2.5:7b")
NUM_PREDICT = env.int("NUM_PREDICT", default=800)
TEMPERATURE = env.float("TEMPERATURE", default=0.1)
NUM_CTX = env.int("NUM_CTX", default=4096)
TIMEOUT = env.int("OLLAMA_TIMEOUT", default=300)

UPLOAD_FOLDER = env.str("UPLOAD_FOLDER", default="/tmp/uploads")
ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB

SECRET_KEY = env.str("SECRET_KEY", default=None)

# DATABASE_URL = env.str("DATABASE_URL", default="sqlite:///parcv.db")
DATABASE_URL = env.str("DATABASE_URL", default="postgresql://parcv:parcv@localhost:5432/parcv")

# ===== E-mail (recuperação de senha) =====
# Envio via SMTP tradicional (Gmail, Mailtrap, etc.)
MAIL_SERVER   = env.str("MAIL_SERVER", default="smtp.gmail.com")
MAIL_PORT     = env.int("MAIL_PORT", default=587)
MAIL_USE_TLS  = env.bool("MAIL_USE_TLS", default=True)
MAIL_USE_SSL  = env.bool("MAIL_USE_SSL", default=False)
MAIL_USERNAME = env.str("MAIL_USERNAME", default="")
MAIL_PASSWORD = env.str("MAIL_PASSWORD", default="")
# Remetente usado com SMTP — precisa ser a própria conta autenticada (MAIL_USERNAME)
MAIL_DEFAULT_SENDER = env.str("MAIL_DEFAULT_SENDER", default="") or MAIL_USERNAME or "noreply@parcv.app"