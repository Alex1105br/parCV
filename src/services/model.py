import json
import time
import requests

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


def _groq_call(prompt, max_tokens=None):
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
            GROQ_API_URL, headers=headers, json=payload, timeout=TIMEOUT
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


def _ollama_call(prompt, num_predict=1200):
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
        timeout=TIMEOUT,
    )
    return response.json().get("response", ""), None


# ===== Public API =====

def stream_resposta(historico, mensagem, skip_append_user=False):
    """Streaming chat via SSE — yields 'data: {...}\\n\\n' chunks."""
    if not skip_append_user:
        historico.append({"role": "user", "content": mensagem})
    inicio = time.time()

    try:
        if LLM_BACKEND == "groq":
            stream = _groq_stream(historico)
        else:
            stream = _ollama_stream(historico)

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
        yield f"data: {json.dumps({'done': True, 'tempo': f'{int(total//60)}m {int(total%60)}s', 'full_response': conteudo})}\n\n"

    except requests.exceptions.ConnectionError:
        backend = "Groq" if LLM_BACKEND == "groq" else "Ollama"
        yield f"data: {json.dumps({'error': f'Não foi possível conectar ao {backend}.'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


def call_model(prompt, num_predict=1200):
    """Synchronous single-prompt call. Returns (response_text, error)."""
    try:
        if LLM_BACKEND == "groq":
            return _groq_call(prompt, max_tokens=num_predict)
        else:
            return _ollama_call(prompt, num_predict)
    except Exception as e:
        return None, str(e)
