import os
import io
import re
import json
import time
import subprocess
import requests
from flask import Flask, render_template, request, Response, session, jsonify, send_file
from werkzeug.utils import secure_filename

OLLAMA_URL    = os.environ.get("OLLAMA_URL", "http://ollama:11434/api/chat")
MODEL         = "qwen2.5:7b"
NUM_PREDICT   = 800
TEMPERATURE   = 0.1
NUM_CTX       = 4096
TIMEOUT       = 900
UPLOAD_FOLDER = "/tmp/uploads"
ALLOWED_EXTENSIONS = {"txt", "pdf"}

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def carregar_arquivo(caminho):
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
    historico.append({"role": "user", "content": mensagem})
    inicio = time.time()
    try:
        resposta = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "messages": historico,
            "stream": True,
            "options": {"num_predict": NUM_PREDICT, "temperature": TEMPERATURE, "num_ctx": NUM_CTX}
        }, stream=True, timeout=TIMEOUT)
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
        historico.append({"role": "assistant", "content": conteudo})
        yield f"data: {json.dumps({'done': True, 'tempo': f'{int(total//60)}m {int(total%60)}s', 'full_response': conteudo})}\n\n"
    except requests.exceptions.ConnectionError:
        yield f"data: {json.dumps({'error': 'Não foi possível conectar ao Ollama.'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


def extrair_json(texto):
    try:
        cleaned = re.sub(r"```json|```", "", texto).strip()
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass
    return {"error": "Falha ao interpretar resposta da IA", "raw": texto}


def extrair_texto_curriculo(raw):
    """Remove ```json ... ``` e extrai só o campo curriculo_otimizado."""
    cleaned = re.sub(r"```json|```", "", raw).strip()
    try:
        data = json.loads(cleaned)
        return data.get("curriculo_otimizado", raw), data.get("melhorias", [])
    except Exception:
        pass
    # Tenta pegar o campo via regex caso JSON esteja malformado
    m = re.search(r'"curriculo_otimizado"\s*:\s*"(.*?)"\s*,\s*"melhorias"', cleaned, re.DOTALL)
    if m:
        texto = m.group(1).replace("\\n", "\n").replace('\\"', '"')
        return texto, []
    return raw, []


# ── Geração de PDF profissional ───────────────────────────

def gerar_pdf_curriculo(texto_ou_json):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    texto, _ = extrair_texto_curriculo(texto_ou_json)

    FONT_DIR = "/usr/share/fonts/truetype/liberation/"
    pdfmetrics.registerFont(TTFont("Sans",        FONT_DIR + "LiberationSans-Regular.ttf"))
    pdfmetrics.registerFont(TTFont("Sans-Bold",   FONT_DIR + "LiberationSans-Bold.ttf"))
    pdfmetrics.registerFont(TTFont("Sans-Italic", FONT_DIR + "LiberationSans-Italic.ttf"))

    PRETO  = colors.HexColor("#1a1a1a")
    CINZA  = colors.HexColor("#555555")
    LINHA  = colors.HexColor("#cccccc")

    def S(name, **kw):
        d = dict(fontName="Sans", textColor=PRETO, spaceAfter=2, spaceBefore=0, leading=14)
        d.update(kw)
        return ParagraphStyle(name, **d)

    st_nome    = S("nome",    fontName="Sans-Bold",   fontSize=18, spaceAfter=2)
    st_titulo  = S("titulo",  fontName="Sans-Italic", fontSize=10, spaceAfter=1, textColor=CINZA)
    st_contato = S("contato", fontName="Sans",        fontSize=8.5, spaceAfter=8, textColor=CINZA)
    st_secao   = S("secao",   fontName="Sans-Bold",   fontSize=9,  spaceAfter=4, spaceBefore=14)
    st_empresa = S("empresa", fontName="Sans-Bold",   fontSize=9.5, spaceAfter=1, spaceBefore=8)
    st_cargo   = S("cargo",   fontName="Sans-Italic", fontSize=9,  spaceAfter=3, textColor=CINZA)
    st_bullet  = S("bullet",  fontName="Sans",        fontSize=9,  spaceAfter=2, leftIndent=10, leading=13)
    st_normal  = S("normal",  fontName="Sans",        fontSize=9,  spaceAfter=3, leading=13)

    SECOES = [
        "COMPETÊNCIAS", "COMPETENCIAS",
        "EXPERIÊNCIAS RELEVANTES", "EXPERIENCIAS RELEVANTES",
        "FORMAÇÃO ACADÊMICA", "FORMACAO ACADEMICA",
        "EXPERIÊNCIA EM PROJETOS", "EXPERIENCIA EM PROJETOS",
        "COMPETÊNCIAS-CHAVE", "COMPETENCIAS-CHAVE",
        "IDIOMAS"
    ]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=1.8*cm, rightMargin=1.8*cm,
                            topMargin=1.6*cm, bottomMargin=1.6*cm)

    story = []
    linhas = texto.strip().split("\n")
    cab = 0
    prev_empresa = False

    for i, linha in enumerate(linhas):
        linha = linha.strip()
        if not linha:
            prev_empresa = False
            continue

        # Cabeçalho
        if cab == 0:
            story.append(Paragraph(linha, st_nome)); cab = 1; continue
        if cab == 1:
            if "@" in linha or "linkedin" in linha.lower() or "github" in linha.lower():
                story.append(Paragraph(linha, st_contato))
                story.append(HRFlowable(width="100%", thickness=1, color=PRETO, spaceAfter=6))
                cab = 3; continue
            story.append(Paragraph(linha, st_titulo)); cab = 2; continue
        if cab == 2:
            story.append(Paragraph(linha, st_contato))
            story.append(HRFlowable(width="100%", thickness=1, color=PRETO, spaceAfter=6))
            cab = 3; continue

        # Seção
        upper = linha.upper()
        if any(upper == s or upper.startswith(s) for s in SECOES):
            story.append(Paragraph(linha.upper(), st_secao))
            story.append(HRFlowable(width="100%", thickness=0.4, color=LINHA, spaceAfter=4))
            prev_empresa = False; continue

        # Bullet
        if linha.startswith("•") or linha.startswith("-"):
            story.append(Paragraph(f"• {linha.lstrip('•- ').strip()}", st_bullet))
            prev_empresa = False; continue

        # Empresa (tem | e dígito)
        if "|" in linha and any(c.isdigit() for c in linha):
            story.append(Spacer(1, 2))
            story.append(Paragraph(linha, st_empresa))
            prev_empresa = True; continue

        # Cargo (linha curta após empresa)
        if prev_empresa and len(linha) < 70:
            story.append(Paragraph(linha, st_cargo))
            prev_empresa = False; continue

        story.append(Paragraph(linha, st_normal))
        prev_empresa = False

    doc.build(story)
    buffer.seek(0)
    return buffer


# ── Prompts ───────────────────────────────────────────────

def build_prompt_ats(curriculo, vaga=None):
    return f"""Você é um sistema ATS profissional.
Analise o currículo com base nos critérios:
1. Estrutura e formatação (0-15)
2. Clareza e escrita (0-15)
3. Experiência profissional (0-20)
4. Palavras-chave ATS (0-20)
5. Skills técnicas (0-15)
6. Compatibilidade com vaga (0-15)

Retorne APENAS JSON válido:
{{
    "score_total": int,
    "criterios": {{"estrutura": int, "clareza": int, "experiencia": int,
                   "palavras_chave": int, "skills": int, "compatibilidade": int}},
    "pontos_fortes": [""],
    "pontos_fracos": [""],
    "sugestoes": [""]
}}

Currículo: {curriculo}
Descrição da vaga: {vaga if vaga else "Não informada"}"""


OPTIMIZED_STRUCTURE_EXAMPLE = """
Nome Completo
Título Profissional
email | linkedin | github

COMPETÊNCIAS
Linguagens: ...
Tecnologias & Ferramentas: ...

EXPERIÊNCIAS RELEVANTES
Empresa | Mês Ano - Mês Ano
Cargo
• Bullet com verbo de ação no passado

FORMAÇÃO ACADÊMICA
Universidade | Curso | Ano - Ano (Previsão)

EXPERIÊNCIA EM PROJETOS
• Nome do Projeto (Ano): Descrição e tecnologias.

COMPETÊNCIAS-CHAVE
• Skill 1

IDIOMAS
• Português: Nativo
• Inglês: Nível intermediário
"""


def build_prompt_otimizar(curriculo, vaga=None):
    return f"""Você é um especialista em otimização de currículos para ATS.
Reescreva o currículo seguindo EXATAMENTE esta estrutura:

{OPTIMIZED_STRUCTURE_EXAMPLE}

REGRAS:
1. Apenas informações verídicas do original
2. Verbos de ação no passado nos bullets
3. Ordem exata das seções
4. Sem JSON, sem markdown — apenas o texto do currículo nas melhorias

Retorne APENAS JSON válido:
{{
    "curriculo_otimizado": "texto completo aqui",
    "melhorias": ["melhoria 1", "melhoria 2"]
}}

Currículo original: {curriculo}
Descrição da vaga: {vaga if vaga else "Não informada"}"""


def call_ollama(prompt, num_predict=800):
    try:
        response = requests.post(
            "http://ollama:11434/api/generate",
            json={"model": MODEL, "prompt": prompt, "stream": False,
                  "options": {"temperature": TEMPERATURE, "num_ctx": NUM_CTX, "num_predict": num_predict}},
            timeout=TIMEOUT
        )
        return response.json().get("response", ""), None
    except Exception as e:
        return None, str(e)


# ── Rotas ─────────────────────────────────────────────────

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
    if arquivo.filename == "" or not allowed_file(arquivo.filename):
        return jsonify({"error": "Arquivo inválido"}), 400
    filename = secure_filename(arquivo.filename)
    caminho = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    arquivo.save(caminho)
    texto, erro = carregar_arquivo(caminho)
    os.remove(caminho)
    if erro:
        return jsonify({"error": erro}), 400
    historico = session.get("historico", [])
    historico.append({"role": "user", "content": f"Documento:\n\n{texto}\n\nUse para responder."})
    historico.append({"role": "assistant", "content": "Documento recebido."})
    session["historico"] = historico
    return jsonify({"success": True, "filename": filename, "chars": len(texto)})


@app.route("/analisar", methods=["GET", "POST"])
def analisar():
    if request.method == "GET":
        return render_template("analisar.html")
    if "arquivo" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    arquivo = request.files["arquivo"]
    vaga = request.form.get("vaga", "").strip()
    if arquivo.filename == "" or not allowed_file(arquivo.filename):
        return jsonify({"error": "Arquivo inválido"}), 400
    filename = secure_filename(arquivo.filename)
    caminho = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    arquivo.save(caminho)
    texto, erro = carregar_arquivo(caminho)
    os.remove(caminho)
    if erro:
        return jsonify({"error": erro}), 400
    resposta, erro = call_ollama(build_prompt_ats(texto, vaga))
    if erro:
        return jsonify({"error": erro}), 500
    return jsonify(extrair_json(resposta))


@app.route("/otimizar", methods=["POST"])
def otimizar():
    if "arquivo" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    arquivo = request.files["arquivo"]
    vaga = request.form.get("vaga", "").strip()
    if arquivo.filename == "" or not allowed_file(arquivo.filename):
        return jsonify({"error": "Arquivo inválido"}), 400
    filename = secure_filename(arquivo.filename)
    caminho = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    arquivo.save(caminho)
    texto, erro = carregar_arquivo(caminho)
    os.remove(caminho)
    if erro:
        return jsonify({"error": erro}), 400

    resposta, erro = call_ollama(build_prompt_otimizar(texto, vaga), num_predict=2000)
    if erro:
        return jsonify({"error": f"Erro ao conectar ao modelo: {erro}"}), 500

    curriculo_texto, melhorias = extrair_texto_curriculo(resposta)

    # Guarda na sessão para o endpoint de download
    session["curriculo_otimizado"] = curriculo_texto

    return jsonify({"curriculo_otimizado": curriculo_texto, "melhorias": melhorias})


@app.route("/otimizar/pdf")
def otimizar_pdf():
    curriculo_texto = session.get("curriculo_otimizado")
    if not curriculo_texto:
        return jsonify({"error": "Nenhum currículo otimizado disponível."}), 400
    try:
        pdf_buffer = gerar_pdf_curriculo(curriculo_texto)
        return send_file(pdf_buffer, mimetype="application/pdf",
                         as_attachment=True, download_name="curriculo_otimizado.pdf")
    except Exception as e:
        return jsonify({"error": f"Erro ao gerar PDF: {str(e)}"}), 500


@app.route("/limpar", methods=["POST"])
def limpar():
    session["historico"] = []
    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=True)