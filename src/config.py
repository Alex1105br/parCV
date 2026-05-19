import os

# ===== LLM Backend =====
# Set LLM_BACKEND to "groq" to use Groq Cloud, or "ollama" (default) for local.
LLM_BACKEND = os.environ.get("LLM_BACKEND", "groq").lower()

# --- Groq ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- Ollama (local) ---
_raw = os.environ.get("OLLAMA_HOST") or os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_HOST = _raw.rsplit("/api/", 1)[0] if "/api/" in _raw else _raw
OLLAMA_CHAT_URL = f"{OLLAMA_HOST}/api/chat"
OLLAMA_GENERATE_URL = f"{OLLAMA_HOST}/api/generate"

# --- Shared ---
MODEL = os.environ.get("MODEL", "qwen2.5:7b")
NUM_PREDICT = int(os.environ.get("NUM_PREDICT", "800"))
TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.1"))
NUM_CTX = int(os.environ.get("NUM_CTX", "4096"))
TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "300"))

UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "/tmp/uploads")
ALLOWED_EXTENSIONS = {"txt", "pdf"}

SECRET_KEY = os.environ.get("SECRET_KEY", None)
