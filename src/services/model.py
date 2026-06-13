import json
import time
import requests

from src.logging_config import logger
from src.config import (
    LLM_BACKEND,
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_API_URL,
    OLLAMA_CHAT_URL,
    OLLAMA_GENERATE_URL,
    MODEL,
    NUM_PREDICT,
    TEMPERATURE,
    NUM_CTX,
    TIMEOUT,
)


# ===== Groq Backend =====

def _groq_stream(messages, max_tokens=None):
    """Stream chat completion from Groq API. Yields (token, done, error) tuples."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": TEMPERATURE,
        "max_tokens": max_tokens or NUM_PREDICT,
        "stream": True,
    }
    response = requests.post(
        GROQ_API_URL, headers=headers, json=payload, stream=True, timeout=TIMEOUT
    )
    if response.status_code != 200:
        error = response.json().get("error", {}).get("message", response.text)
        yield "", False, error
        return

    for line in response.iter_lines():
        if not line:
            continue
        line = line.decode("utf-8") if isinstance(line, bytes) else line
        if not line.startswith("data: "):
            continue
        data_str = line[6:]
        if data_str.strip() == "[DONE]":
            yield "", True, None
            return
        data = json.loads(data_str)
        delta = data.get("choices", [{}])[0].get("delta", {})
        token = delta.get("content", "")
        finish = data.get("choices", [{}])[0].get("finish_reason")
        if token:
            yield token, False, None
        if finish:
            yield "", True, None
            return


def _groq_call(prompt, max_tokens=None, timeout=None):
    """Synchronous single-prompt call via Groq. Returns (response_text, error)."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": TEMPERATURE,
        "max_tokens": max_tokens or NUM_PREDICT,
        "stream": False,
    }
    try:
        response = requests.post(
            GROQ_API_URL, headers=headers, json=payload, timeout=timeout or TIMEOUT
        )
        if response.status_code != 200:
            error = response.json().get("error", {}).get("message", response.text)
            return None, error
        content = response.json()["choices"][0]["message"]["content"]
        return content, None
    except Exception as e:
        return None, str(e)


# ===== Ollama Backend =====

def _ollama_stream(messages):
    """Stream chat via Ollama local API."""
    response = requests.post(
        OLLAMA_CHAT_URL,
        json={
            "model": MODEL,
            "messages": messages,
            "stream": True,
            "options": {
                "num_predict": NUM_PREDICT,
                "temperature": TEMPERATURE,
                "num_ctx": NUM_CTX,
            },
        },
        stream=True,
        timeout=TIMEOUT,
    )
    for linha in response.iter_lines():
        if not linha:
            continue
        dados = json.loads(linha)
        token = dados.get("message", {}).get("content", "")
        done = dados.get("done", False)
        yield token, done, None
        if done:
            return


def _ollama_call(prompt, num_predict=1200, timeout=None):
    """Synchronous single-prompt call via Ollama."""
    response = requests.post(
        OLLAMA_GENERATE_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": TEMPERATURE,
                "num_ctx": NUM_CTX,
                "num_predict": num_predict,
            },
        },
        timeout=timeout or TIMEOUT,
    )
    return response.json().get("response", ""), None


# ===== Public API =====

def stream_resposta(historico, mensagem, skip_append_user=False, session_id=None, titulo_ctx=None):
    """Streaming chat via SSE — yields 'data: {...}\\n\\n' chunks.

    titulo_ctx: optional dict {"doc_label": str|None} — se fornecido e a sessão
    ainda não tem título, gera o título de forma SÍNCRONA (na mesma thread do
    SSE) e o inclui no payload final 'done' como 'titulo'. Isso elimina a
    necessidade de polling/fetch separado no frontend, evitando race conditions
    com F5/reload.
    """
    if not skip_append_user:
        historico.append({"role": "user", "content": mensagem})
    inicio = time.time()

    try:
        api_msgs = [{"role": m["role"], "content": m["content"]} for m in historico]
        if LLM_BACKEND == "groq":
            stream = _groq_stream(api_msgs)
        else:
            stream = _ollama_stream(api_msgs)

        conteudo = ""
        for token, done, error in stream:
            if error:
                yield f"data: {json.dumps({'error': error})}\n\n"
                return
            if token:
                conteudo += token
                yield f"data: {json.dumps({'token': token})}\n\n"
            if done:
                break

        total = time.time() - inicio
        historico.append({"role": "assistant", "content": conteudo})
        logger.info("llm_stream_done", extra={"backend": LLM_BACKEND, "duration_ms": int(total * 1000), "chars": len(conteudo)})
        done_payload = {'done': True, 'tempo': f'{int(total//60)}m {int(total%60)}s', 'full_response': conteudo}
        if session_id:
            done_payload['session_id'] = session_id

        if titulo_ctx is not None:
            titulo = _gerar_titulo_sync(mensagem, titulo_ctx.get("doc_label"))
            if titulo:
                done_payload['titulo'] = titulo

        yield f"data: {json.dumps(done_payload)}\n\n"

    except requests.exceptions.ConnectionError:
        backend = "Groq" if LLM_BACKEND == "groq" else "Ollama"
        yield f"data: {json.dumps({'error': f'Não foi possível conectar ao {backend}.'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


def _gerar_titulo_sync(mensagem, doc_label):
    """Gera um título curto de forma síncrona (chamada dentro da thread do SSE).

    Não toca no banco — apenas retorna a string do título (ou None).
    A persistência fica a cargo do chamador (rota), dentro do app_context.
    """
    from src.utils import sanitize_text
    from datetime import datetime

    mensagem = (mensagem or "").strip()

    # Só arquivo sem mensagem: usa nome do arquivo, sem chamar IA
    if doc_label and not mensagem:
        return sanitize_text(doc_label)[:100]

    if not mensagem and not doc_label:
        return None

    context_parts = []
    if doc_label:
        context_parts.append(f"Documento: {doc_label}")
    if mensagem:
        context_parts.append(f"Mensagem: {mensagem}")
    context = "\n".join(context_parts)

    prompt = (
        "Crie um título curto (máximo 50 caracteres) para uma conversa "
        "que começa com o seguinte contexto. "
        "Responda APENAS com o título, sem aspas, sem explicações.\n\n"
        + context
    )

    titulo = None
    try:
        titulo_raw, error = call_model(prompt, num_predict=60, timeout=15)
        if not error and titulo_raw and titulo_raw.strip():
            titulo = sanitize_text(titulo_raw.strip().strip('"\''))[:100]
    except Exception:
        pass

    if not titulo:
        fallback = mensagem[:60].split('\n')[0].strip() or (doc_label or "")
        titulo = sanitize_text(fallback)[:100] if fallback else None

    if not titulo:
        titulo = datetime.now().strftime("Conversa %d/%m %H:%M")

    return titulo


def call_model(prompt, num_predict=1200, timeout=None):
    """Synchronous single-prompt call. Returns (response_text, error)."""
    t0 = time.time()
    try:
        if LLM_BACKEND == "groq":
            result, error = _groq_call(prompt, max_tokens=num_predict, timeout=timeout)
        else:
            result, error = _ollama_call(prompt, num_predict, timeout=timeout)
        duration_ms = int((time.time() - t0) * 1000)
        logger.info("llm_call_done", extra={"backend": LLM_BACKEND, "duration_ms": duration_ms, "error": error is not None})
        return result, error
    except Exception as e:
        duration_ms = int((time.time() - t0) * 1000)
        logger.error("llm_call_error", extra={"backend": LLM_BACKEND, "duration_ms": duration_ms, "exc": str(e)})
        return None, str(e)