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
ALLOWED_EXTENSIONS = {"txt", "pdf"}

SECRET_KEY = env.str("SECRET_KEY", default=None)
