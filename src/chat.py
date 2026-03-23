import requests
import json
import time

# ─── Configurações globais ────────────────────────────────
OLLAMA_URL  = "http://ollama:11434/api/chat"
MODEL       = "qwen2.5:7b"
NUM_PREDICT = 200    # máximo de tokens por resposta
TEMPERATURE = 0.1    # 0.0 = direto/preciso | 1.0 = criativo
NUM_CTX     = 512    # tamanho do contexto (memória do modelo)
# ─────────────────────────────────────────────────────────

print("🤖 Chat com Qwen 2.5 — digite 'sair' para encerrar\n")

historico = []

while True:
    pergunta = input("Você: ").strip()
    if pergunta.lower() == "sair":
        break
    if not pergunta:
        continue

    historico.append({"role": "user", "content": pergunta})

    inicio = time.time()

    resposta = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "messages": historico,
        "stream": True,
        "options": {
            "num_predict": NUM_PREDICT,
            "temperature": TEMPERATURE,
            "num_ctx":     NUM_CTX
        }
    }, stream=True)

    print("IA: ", end="", flush=True)
    conteudo = ""
    for linha in resposta.iter_lines():
        if linha:
            dados = json.loads(linha)
            token = dados.get("message", {}).get("content", "")
            print(token, end="", flush=True)
            conteudo += token
            if dados.get("done"):
                break

    total_segundos = time.time() - inicio
    minutos = int(total_segundos // 60)
    segundos = int(total_segundos % 60)
    print(f"\n\n⏱ Tempo de processamento: {minutos} minutos e {segundos} segundos ({total_segundos:.1f}s)\n")

    historico.append({"role": "assistant", "content": conteudo})