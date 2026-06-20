import json
import logging
import logging.handlers
import os
import sys
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class StructuredFormatter(logging.Formatter):
    """Formatter de logging que emite cada registro como uma linha JSON
    (em vez do texto livre padrão do logging), com request_id embutido —
    facilita grep/parsing dos logs e correlação de várias linhas com a
    mesma requisição HTTP."""

    def format(self, record: logging.LogRecord) -> str:
        """Monta o payload JSON (timestamp, nível, request_id, mensagem,
        traceback se houver exceção) e inclui qualquer campo extra
        passado via logger.info(msg, extra={...}) que não seja um campo
        interno padrão do LogRecord."""
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "request_id": request_id_var.get(),
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        extra_keys = set(record.__dict__) - {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "taskName",
        }
        for key in extra_keys:
            payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str = "INFO", log_dir: str = "logs") -> None:
    """Configura o logger raiz com StructuredFormatter, escrevendo
    simultaneamente em stdout e em um arquivo rotativo (logs/parcv.log,
    10 MB por arquivo, 5 backups). Limpa handlers pré-existentes do
    logger raiz antes de adicionar os novos (evita log duplicado se
    chamada mais de uma vez). Também abaixa o nível do logger do
    werkzeug para WARNING, pra não poluir o log com cada request em
    formato não-estruturado. Chamada uma vez, dentro de create_app()."""
    os.makedirs(log_dir, exist_ok=True)
    fmt = StructuredFormatter()

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)

    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "parcv.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(stream_handler)
    root.addHandler(file_handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


logger = logging.getLogger("parcv")