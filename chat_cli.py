import requests
import json
import time
import argparse
import subprocess
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from src.config import OLLAMA_CHAT_URL, MODEL, NUM_PREDICT, TEMPERATURE, NUM_CTX


def carregar_arquivo(caminho):
    """Carrega conteúdo de um arquivo TXT ou PDF."""
    if not os.path.isabs(caminho):
        caminho = os.path.join("/workspace", caminho)

    if not os.path.isfile(caminho):
        print(f"❌ Arquivo não encontrado: {caminho}")
        return None

    ext = os.path.splitext(caminho)[1].lower()

    if ext == ".pdf":
        try:
            resultado = subprocess.run(
                ["pdftotext", caminho, "-"],
                capture_output=True, text=True, timeout=30
            )
            if resultado.returncode != 0:
                print(f"❌ Erro ao converter PDF: {resultado.stderr.strip()}")
                return None
            texto = resultado.stdout.strip()
        except FileNotFoundError:
            print("❌ pdftotext não encontrado. Instale com: apt install poppler-utils")
            return None
    elif ext == ".txt":
        with open(caminho, "r", encoding="utf-8") as f:
            texto = f.read().strip()
    else:
        print(f"❌ Formato não suportado: {ext} (use .txt ou .pdf)")
        return None

    if not texto:
        print("⚠️  Arquivo vazio ou sem texto extraível.")
        return None

    print(f"✅ Arquivo carregado: {os.path.basename(caminho)} ({len(texto)} caracteres)")
    return texto


def enviar_mensagem(historico, mensagem):
    """Envia mensagem para o modelo e faz streaming da resposta."""
    historico.append({"role": "user", "content": mensagem})

    inicio = time.time()

    resposta = requests.post(OLLAMA_CHAT_URL, json={
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


# ─── Argumentos de linha de comando ───────────────────────
parser = argparse.ArgumentParser(description="Chat com IA local (Qwen 2.5)")
parser.add_argument(
    "--arquivo",
    type=str,
    help="Caminho para um arquivo .txt ou .pdf para carregar como contexto inicial"
)
args = parser.parse_args()

# ─── Início do chat ──────────────────────────────────────
print("🤖 Chat com Qwen 2.5 — digite 'sair' para encerrar")
print("📎 Use #<caminho> para carregar um documento no chat (ex: #relatorio.pdf)\n")

historico = []

# Carregar arquivo via --arquivo (argumento CLI)
if args.arquivo:
    texto = carregar_arquivo(args.arquivo)
    if texto:
        contexto = f"O usuário forneceu o seguinte documento para referência:\n\n{texto}\n\nUse este documento para responder as próximas perguntas."
        historico.append({"role": "user", "content": contexto})
        historico.append({"role": "assistant", "content": "Documento recebido. Pode fazer suas perguntas sobre ele."})
        print(f"📄 Documento '{os.path.basename(args.arquivo)}' carregado como contexto.\n")

try:
    while True:
        pergunta = input("Você: ").strip()
        if pergunta.lower() == "sair":
            break
        if not pergunta:
            continue

        # Comando # para referenciar arquivo no chat
        if pergunta.startswith("#") and not pergunta.startswith("##"):
            caminho = pergunta[1:].strip()
            texto = carregar_arquivo(caminho)
            if texto:
                contexto = f"O usuário forneceu o seguinte documento para referência:\n\n{texto}\n\nUse este documento para responder as próximas perguntas."
                enviar_mensagem(historico, contexto)
            continue

        enviar_mensagem(historico, pergunta)
except (KeyboardInterrupt, EOFError):
    print("\n👋 Encerrando o chat. Até a próxima!")
