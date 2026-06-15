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


# ===== SIMULADOR DE ENTREVISTA =====

def gerar_plano_entrevista(curriculo_text, vaga_descricao):
    """
    Gera plano de entrevista com IA baseado em currículo e vaga.
    Retorna dict com: numero_perguntas, topicos_principais, estrategia_entrevista, questoes_principais
    """
    prompt = f"""Você é um recrutador técnico experiente. Analise o currículo e a descrição da vaga para gerar um plano de entrevista estruturado.

CURRÍCULO:
{curriculo_text[:2000]}

DESCRIÇÃO DA VAGA:
{vaga_descricao[:1000]}

Gere um JSON com a seguinte estrutura (APENAS JSON, sem outros textos):
{{
    "numero_perguntas": 5,
    "topicos_principais": [<lista de 3-5 tópicos técnicos principais>],
    "estrategia_entrevista": "<descrição breve da estratégia em 2-3 linhas>",
    "questoes_principais": [<lista de 5-8 perguntas técnicas bem estruturadas>]
}}"""
    
    response, error = call_model(prompt, num_predict=1500)
    
    if error or not response:
        logger.error(f"Erro ao gerar plano: {error}")
        return {
            "numero_perguntas": 5,
            "topicos_principais": ["Experiência Técnica", "Resolução de Problemas", "Trabalho em Equipe"],
            "estrategia_entrevista": "Avaliação técnica com foco em habilidades práticas e comportamentais",
            "questoes_principais": [
                "Descreva seu maior projeto técnico e o que você aprendeu com ele",
                "Como você aborda a resolução de um problema desconhecido?",
                "Qual é sua experiência com tecnologias relevantes para esta vaga?",
                "Conte sobre um conflito no trabalho e como você o resolveu",
                "Quais são seus objetivos profissionais para os próximos 2 anos?"
            ]
        }
    
    try:
        # Extrair JSON da resposta
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            json_str = response[json_start:json_end]
            plano = json.loads(json_str)
            
            # Validar campos
            plano.setdefault("numero_perguntas", 5)
            plano.setdefault("topicos_principais", [])
            plano.setdefault("estrategia_entrevista", "")
            plano.setdefault("questoes_principais", [])
            # Limit to exactly 5
            plano["numero_perguntas"] = 5
            plano["questoes_principais"] = plano["questoes_principais"][:5]
            
            return plano
    except json.JSONDecodeError as e:
        logger.warning(f"Erro ao parsear JSON do plano: {e}")
    
    return {
        "numero_perguntas": 5,
        "topicos_principais": ["Experiência Técnica", "Resolução de Problemas", "Trabalho em Equipe"],
        "estrategia_entrevista": "Avaliação técnica com foco em habilidades práticas e comportamentais",
        "questoes_principais": [
            "Descreva seu maior projeto técnico e o que você aprendeu com ele",
            "Como você aborda a resolução de um problema desconhecido?",
            "Qual é sua experiência com tecnologias relevantes para esta vaga?",
            "Conte sobre um conflito no trabalho e como você o resolveu",
            "Quais são seus objetivos profissionais para os próximos 2 anos?"
        ]
    }


def avaliar_resposta(pergunta, resposta, contexto):
    """
    Avalia resposta com IA.
    Retorna dict com: feedback, score (1-10), deve_aprofundar, perguntas_aprofundamento
    """
    prompt = f"""Você é um avaliador técnico experiente. Avalie a seguinte resposta de entrevista.

PERGUNTA: {pergunta}

RESPOSTA DO CANDIDATO: {resposta}

CONTEXTO: {json.dumps(contexto)}

Forneça avaliação em JSON (APENAS JSON):
{{
    "feedback": "<feedback construtivo e específico sobre a resposta - max 300 chars>",
    "score": <1-10>,
    "deve_aprofundar": false,
    "perguntas_aprofundamento": []
}}"""
    
    response, error = call_model(prompt, num_predict=800)
    
    if error or not response:
        logger.error(f"Erro ao avaliar resposta: {error}")
        return {
            "feedback": "Resposta adequada. Considere adicionar mais detalhes técnicos.",
            "score": 6,
            "deve_aprofundar": False,
            "perguntas_aprofundamento": []
        }
    
    try:
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            json_str = response[json_start:json_end]
            avaliacao = json.loads(json_str)
            
            # Validar campos
            avaliacao.setdefault("feedback", "Resposta recebida")
            avaliacao.setdefault("score", 5)
            avaliacao.setdefault("deve_aprofundar", False)
            avaliacao.setdefault("perguntas_aprofundamento", [])
            
            # Limitar score entre 1-10
            avaliacao["score"] = max(1, min(10, int(avaliacao["score"])))
            
            return avaliacao
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning(f"Erro ao parsear avaliação: {e}")
    
    return {
        "feedback": "Resposta recebida e avaliada",
        "score": 5,
        "deve_aprofundar": False,
        "perguntas_aprofundamento": []
    }


def gerar_relatorio_final(entrevista_id):
    """
    Gera relatório final de entrevista com IA.
    Retorna dict com: score_geral, parecer_final, pontos_fortes, pontos_fracos, recomendacoes, recomendacao_gestor
    """
    from src.models.entrevista import Entrevista
    
    entrevista = Entrevista.query.get(entrevista_id)
    if not entrevista:
        logger.error(f"Entrevista {entrevista_id} não encontrada")
        return _relatorio_padrao()
    
    # Compilar respostas e feedbacks
    perguntas_info = []
    scores_totais = []
    
    for pergunta in entrevista.perguntas:
        if pergunta.resposta_usuario and pergunta.avaliacao_resposta:
            score = pergunta.avaliacao_resposta.get("score", 5)
            scores_totais.append(score)
            perguntas_info.append({
                "pergunta": pergunta.pergunta_principal[:100],
                "resposta_resumida": pergunta.resposta_usuario[:150],
                "score": score,
                "feedback": pergunta.avaliacao_resposta.get("feedback", "")[:100]
            })
    
    # Calcular score médio
    score_medio = sum(scores_totais) / len(scores_totais) if scores_totais else 5.0
    
    prompt = f"""Você é um gestor de RH sênior. Gere um relatório executivo final de entrevista.

VAGA: {entrevista.vaga_descricao[:500]}

PLAN DA ENTREVISTA: {entrevista.plano_entrevista.get('estrategia_entrevista', '')}

DESEMPENHO:
- Score Médio: {score_medio:.1f}/10
- Perguntas Respondidas: {len(perguntas_info)}
- Detalhes: {json.dumps(perguntas_info[:3])}

Gere JSON (APENAS JSON):
{{
    "score_geral": <1.0-10.0>,
    "parecer_final": "<parecer executivo conciso - max 500 chars>",
    "pontos_fortes": [<lista 3-4 pontos fortes identificados>],
    "pontos_fracos": [<lista 3-4 pontos a melhorar>],
    "recomendacoes": [<lista 2-3 recomendações concretas>],
    "recomendacao_gestor": "<recomendação final - REJEITAR / ENTREVISTA_ADICIONAL / APROVAR>"
}}"""
    
    response, error = call_model(prompt, num_predict=1000)
    
    if error or not response:
        logger.error(f"Erro ao gerar relatório final: {error}")
        return _relatorio_padrao(score_medio)
    
    try:
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            json_str = response[json_start:json_end]
            relatorio = json.loads(json_str)
            
            # Validar campos
            relatorio.setdefault("score_geral", score_medio)
            relatorio.setdefault("parecer_final", "Candidato avaliado")
            relatorio.setdefault("pontos_fortes", [])
            relatorio.setdefault("pontos_fracos", [])
            relatorio.setdefault("recomendacoes", [])
            relatorio.setdefault("recomendacao_gestor", "ENTREVISTA_ADICIONAL")
            
            # Validar score
            relatorio["score_geral"] = max(1.0, min(10.0, float(relatorio["score_geral"])))
            
            return relatorio
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning(f"Erro ao parsear relatório final: {e}")
    
    return _relatorio_padrao(score_medio)


def _relatorio_padrao(score_medio=5.0):
    """Retorna relatório padrão de fallback"""
    return {
        "score_geral": score_medio,
        "parecer_final": "Candidato foi avaliado através da simulação de entrevista. Resultados precisam de análise adicional.",
        "pontos_fortes": ["Comunicação clara", "Engajamento na entrevista", "Disposição para aprender"],
        "pontos_fracos": ["Maior prática em casos técnicos", "Aprofundamento em conceitos", "Experiência específica"],
        "recomendacoes": ["Revisar fundamentação técnica", "Praticar casos de uso reais", "Estudar situações do setor"],
        "recomendacao_gestor": "ENTREVISTA_ADICIONAL"
    }
