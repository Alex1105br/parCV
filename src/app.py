import os
import json
import time
import subprocess
import requests
from flask import Flask, render_template, request, Response, session, jsonify
from werkzeug.utils import secure_filename

# ─── Configurações globais ────────────────────────────────
OLLAMA_URL  = os.environ.get("OLLAMA_URL", "http://ollama:11434/api/chat")
MODEL       = "qwen2.5:7b"
NUM_PREDICT = 800
TEMPERATURE = 0.1
NUM_CTX     = 4096
UPLOAD_FOLDER = "/tmp/uploads"
ALLOWED_EXTENSIONS = {"txt", "pdf"}
# ─────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def carregar_arquivo(caminho):
    """Carrega conteúdo de um arquivo TXT ou PDF."""
    if not os.path.isfile(caminho):
        return None, "Arquivo não encontrado."

    ext = os.path.splitext(caminho)[1].lower()

    if ext == ".pdf":
        try:
            resultado = subprocess.run(
                ["pdftotext", caminho, "-"],
                capture_output=True, text=True, timeout=30
            )
            if resultado.returncode != 0:
                return None, f"Erro ao converter PDF: {resultado.stderr.strip()}"
            texto = resultado.stdout.strip()
        except FileNotFoundError:
            return None, "pdftotext não encontrado."
    elif ext == ".txt":
        with open(caminho, "r", encoding="utf-8") as f:
            texto = f.read().strip()
    else:
        return None, f"Formato não suportado: {ext}"

    if not texto:
        return None, "Arquivo vazio ou sem texto extraível."

    return texto, None


def stream_resposta(historico, mensagem):
    """Gera streaming da resposta da IA."""
    historico.append({"role": "user", "content": mensagem})

    inicio = time.time()

    try:
        resposta = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "messages": historico,
            "stream": True,
            "options": {
                "num_predict": NUM_PREDICT,
                "temperature": TEMPERATURE,
                "num_ctx": NUM_CTX
            }
        }, stream=True, timeout=300)

        conteudo = ""
        for linha in resposta.iter_lines():
            if linha:
                dados = json.loads(linha)
                token = dados.get("message", {}).get("content", "")
                conteudo += token
                yield f"data: {json.dumps({'token': token})}\n\n"
                if dados.get("done"):
                    break

        total = time.time() - inicio
        minutos = int(total // 60)
        segundos = int(total % 60)

        historico.append({"role": "assistant", "content": conteudo})

        yield f"data: {json.dumps({'done': True, 'tempo': f'{minutos}m {segundos}s ({total:.1f}s)', 'full_response': conteudo})}\n\n"

    except requests.exceptions.ConnectionError:
        yield f"data: {json.dumps({'error': 'Não foi possível conectar ao Ollama. Verifique se o serviço está rodando.'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

# ==============================
# 🧠 PROMPT ATS
# ==============================
def build_prompt_ats(curriculo, vaga=None):
    return f"""
    Você é um sistema ATS (Applicant Tracking System) profissional.

    Analise o currículo com base nos critérios:

    1. Estrutura e formatação (0-15)
    2. Clareza e escrita (0-15)
    3. Experiência profissional (0-20)
    4. Palavras-chave ATS (0-20)
    5. Skills técnicas (0-15)
    6. Compatibilidade com vaga (0-15)

    REGRAS:
    - Seja objetivo
    - Avalie como recrutador técnico
    - Não invente informações

    Retorne APENAS JSON válido:

    {{
        "score_total": int,
        "criterios": {{
            "estrutura": int,
            "clareza": int,
            "experiencia": int,
            "palavras_chave": int,
            "skills": int,
            "compatibilidade": int
        }},
        "pontos_fortes": [""],
        "pontos_fracos": [""],
        "sugestoes": [""]
    }}

    Currículo:
    {curriculo}

    Descrição da vaga:
    {vaga if vaga else "Não informada"}
    """

# ==============================
# 🤖 CHAMAR OLLAMA (SEM STREAM)
# ==============================
def analisar_ollama(prompt):
    try:
        response = requests.post(
            "http://ollama:11434/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_ctx": NUM_CTX
                }
            },
            timeout=300
        )

        data = response.json()

        # SEMPRE retorna 2 valores
        return data.get("response", ""), None

    except Exception as e:
        return None, str(e)
# ==============================
# 🔧 EXTRAIR JSON DA RESPOSTA
# ==============================
def extrair_json(texto):
    try:
        import re
        match = re.search(r"\{.*\}", texto, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass

    return {
        "error": "Falha ao interpretar resposta da IA",
        "raw": texto
    }

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/chat")
def chat_get():
    if "historico" not in session:
        session["historico"] = []
    return render_template("chat.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    mensagem = data.get("mensagem", "").strip()
    if not mensagem:
        return jsonify({"error": "Mensagem vazia"}), 400

    historico = session.get("historico", [])

    def generate():
        yield from stream_resposta(historico, mensagem)
        session["historico"] = historico

    return Response(generate(), mimetype="text/event-stream")


@app.route("/upload", methods=["POST"])
def upload():
    if "arquivo" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    arquivo = request.files["arquivo"]
    if arquivo.filename == "":
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400

    if not allowed_file(arquivo.filename):
        return jsonify({"error": "Formato não suportado. Use .txt ou .pdf"}), 400

    filename = secure_filename(arquivo.filename)
    caminho = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    arquivo.save(caminho)

    texto, erro = carregar_arquivo(caminho)
    os.remove(caminho)

    if erro:
        return jsonify({"error": erro}), 400

    historico = session.get("historico", [])
    contexto = f"O usuário forneceu o seguinte documento para referência:\n\n{texto}\n\nUse este documento para responder as próximas perguntas."
    historico.append({"role": "user", "content": contexto})
    historico.append({"role": "assistant", "content": "Documento recebido. Pode fazer suas perguntas sobre ele."})

    mensagem = request.form.get("mensagem", "").strip()
    if mensagem:
        def generate():
            yield from stream_resposta(historico, mensagem)
            session["historico"] = historico

        return Response(generate(), mimetype="text/event-stream")

    session["historico"] = historico
    return jsonify({
        "success": True,
        "filename": filename,
        "chars": len(texto)
    })

@app.route("/analisar", methods=["GET", "POST"])
def analisar():
    if request.method == "GET":
        return render_template("analisar.html")

    # ===== POST (análise ATS) =====
    if "arquivo" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    arquivo = request.files["arquivo"]
    vaga = request.form.get("vaga", "").strip()

    if arquivo.filename == "":
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400

    if not allowed_file(arquivo.filename):
        return jsonify({"error": "Formato não suportado. Use .txt ou .pdf"}), 400

    filename = secure_filename(arquivo.filename)
    caminho = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    arquivo.save(caminho)

    texto, erro = carregar_arquivo(caminho)
    os.remove(caminho)

    if erro:
        return jsonify({"error": erro}), 400

    prompt = build_prompt_ats(texto, vaga)

    resposta, erro = analisar_ollama(prompt)
    if erro:
        return jsonify({"error": erro}), 500

    resultado = extrair_json(resposta)

    return jsonify(resultado)

@app.route("/limpar", methods=["POST"])
def limpar():
    session["historico"] = []
    return jsonify({"success": True})






if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=True)
