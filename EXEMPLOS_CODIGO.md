# 💻 Exemplos de Código - Simulador de Entrevistas

## 1. Model Completo: `src/models/entrevista.py`

```python
import uuid
from datetime import datetime, timezone

from src.models.db import db


class Entrevista(db.Model):
    __tablename__ = "entrevista"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    
    curriculo_arquivo = db.Column(db.String(255), nullable=False)
    vaga_descricao = db.Column(db.Text, nullable=False)
    numero_perguntas = db.Column(db.Integer, nullable=False)
    plano_entrevista = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='em_planejamento')
    
    criado_em = db.Column(db.DateTime(timezone=True), nullable=False, 
                          default=lambda: datetime.now(timezone.utc))
    atualizado_em = db.Column(db.DateTime(timezone=True), nullable=False,
                              default=lambda: datetime.now(timezone.utc))
    finalizado_em = db.Column(db.DateTime(timezone=True), nullable=True)
    
    relatorio_final = db.Column(db.JSON, nullable=True)

    user = db.relationship("User", back_populates="entrevistas")
    perguntas = db.relationship("PerguntaEntrevista", back_populates="entrevista",
                                cascade="all, delete-orphan")


class PerguntaEntrevista(db.Model):
    __tablename__ = "pergunta_entrevista"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entrevista_id = db.Column(db.String(36), db.ForeignKey("entrevista.id"), nullable=False)
    
    numero_sequencial = db.Column(db.Integer, nullable=False)
    pergunta_principal = db.Column(db.Text, nullable=False)
    resposta_usuario = db.Column(db.Text, nullable=True)
    avaliacao_resposta = db.Column(db.JSON, nullable=True)
    perguntas_aprofundamento = db.Column(db.JSON, nullable=True)
    
    criado_em = db.Column(db.DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))
    respondido_em = db.Column(db.DateTime(timezone=True), nullable=True)

    entrevista = db.relationship("Entrevista", back_populates="perguntas")
```

---

## 2. Atualizar User Model

**Adicionar ao fim de `src/models/user.py`:**

```python
    entrevistas = db.relationship("Entrevista", back_populates="user", lazy="dynamic")
```

**Resultado completo:**

```python
import uuid
from datetime import datetime, timezone

from src.models.db import db


class User(db.Model):
    __tablename__ = "users"

    id        = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name      = db.Column(db.String(100), nullable=False)
    email     = db.Column(db.String(255), unique=True, nullable=False)
    password  = db.Column(db.String(255), nullable=False)
    criado_em = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    analises    = db.relationship("Analise",     back_populates="user", lazy="dynamic")
    otimizacoes = db.relationship("Otimizacao",  back_populates="user", lazy="dynamic")
    chat_sessions = db.relationship("ChatSession", back_populates="user", lazy="dynamic")
    entrevistas = db.relationship("Entrevista", back_populates="user", lazy="dynamic")  # NOVO
```

---

## 3. Funções de IA: `src/services/model.py`

**Adicionar estas funções ao fim do arquivo:**

```python
import json
from src.config import GROQ_API_KEY

def gerar_plano_entrevista(curriculo_text: str, vaga_descricao: str) -> dict:
    """
    Analisa currículo + vaga e gera plano de entrevista usando IA.
    """
    from groq import Groq
    
    client = Groq(api_key=GROQ_API_KEY)
    
    prompt = f"""Você é um especialista em recrutamento e entrevistas técnicas.

Analise o currículo e a descrição da vaga fornecidos e gere um plano de entrevista estruturado.

CURRÍCULO:
{curriculo_text}

VAGA:
{vaga_descricao}

Retorne APENAS um JSON válido (sem explicações):
{{
  "numero_perguntas": <5-8>,
  "topicos_principais": ["tópico1", "tópico2", "tópico3"],
  "estrategia_entrevista": "<parágrafo breve com a abordagem>",
  "questoes_principais": ["pergunta1", "pergunta2", ...]
}}

Diretrizes:
- numero_perguntas: entre 5 e 8, baseado na complexidade
- questoes_principais: deve ter exatamente numero_perguntas itens
- Perguntas técnicas, comportamentais e sobre experiências
- Considere gaps entre CV e vaga
- Linguagem clara e profissional"""
    
    message = client.messages.create(
        model="mixtral-8x7b-32768",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
    )
    
    try:
        response_text = message.content[0].text.strip()
        # Remover markdown code blocks se houver
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        
        plano = json.loads(response_text)
        return plano
    except json.JSONDecodeError:
        logger.error(f"Erro ao parsear JSON da IA: {response_text}")
        raise ValueError("IA retornou JSON inválido")


def avaliar_resposta(pergunta: str, resposta: str, contexto: dict) -> dict:
    """
    IA avalia resposta do usuário.
    
    contexto = {
        "curriculo_resumo": str,
        "vaga_resumida": str,
        "pergunta_numero": int
    }
    """
    from groq import Groq
    
    client = Groq(api_key=GROQ_API_KEY)
    
    prompt = f"""Você é um entrevistador técnico experiente avaliando a resposta de um candidato.

PERGUNTA: {pergunta}
RESPOSTA DO CANDIDATO: {resposta}
CURRÍCULO (resumido): {contexto.get('curriculo_resumo', '')}
VAGA (resumida): {contexto.get('vaga_resumida', '')}

Retorne APENAS um JSON válido:
{{
  "feedback": "<feedback construtivo, 2-3 frases>",
  "score": <1-10>,
  "deve_aprofundar": <true/false>,
  "perguntas_aprofundamento": ["<pergunta1>", "<pergunta2>"]
}}

Critérios de Score:
- 1-3: Resposta incompleta, incorreta ou não relacionada
- 4-6: Resposta aceitável, mas com lacunas
- 7-8: Resposta boa, bem estruturada
- 9-10: Resposta excelente, detalhada

Aprofundamento:
- Fazer apenas se score >= 7 ou pontos críticos não mencionados
- Máximo 2 perguntas
- Complementar aspectos específicos da resposta"""
    
    message = client.messages.create(
        model="mixtral-8x7b-32768",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512,
    )
    
    try:
        response_text = message.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        
        avaliacao = json.loads(response_text)
        
        # Validar
        avaliacao["score"] = max(1, min(10, avaliacao.get("score", 5)))
        avaliacao["deve_aprofundar"] = avaliacao.get("deve_aprofundar", False)
        avaliacao["perguntas_aprofundamento"] = avaliacao.get("perguntas_aprofundamento", [])[:2]
        
        return avaliacao
    except json.JSONDecodeError:
        logger.error(f"Erro ao parsear JSON da IA (avaliação): {response_text}")
        return {
            "feedback": "Resposta recebida.",
            "score": 5,
            "deve_aprofundar": False,
            "perguntas_aprofundamento": []
        }


def gerar_relatorio_final(entrevista_id: str) -> dict:
    """
    Coleta todas respostas e gera análise final usando IA.
    """
    from groq import Groq
    from src.models.entrevista import Entrevista
    
    client = Groq(api_key=GROQ_API_KEY)
    
    # Carregar entrevista
    entrevista = Entrevista.query.get(entrevista_id)
    if not entrevista:
        raise ValueError("Entrevista não encontrada")
    
    # Montar JSON com todas respostas
    respostas_formatadas = []
    for p in entrevista.perguntas:
        item = {
            "numero": p.numero_sequencial,
            "pergunta": p.pergunta_principal,
            "resposta": p.resposta_usuario,
            "score": p.avaliacao_resposta.get("score", 5) if p.avaliacao_resposta else 5,
            "feedback": p.avaliacao_resposta.get("feedback", "") if p.avaliacao_resposta else ""
        }
        if p.perguntas_aprofundamento:
            item["aprofundamentos"] = p.perguntas_aprofundamento
        respostas_formatadas.append(item)
    
    # Extrair nome do currículo (do primeiro parágrafo ou assumir "Candidato")
    nome_candidato = entrevista.user.name or "Candidato"
    # Extrair nome da vaga (primeira linha da descrição ou "Vaga")
    nome_vaga = entrevista.vaga_descricao.split('\n')[0][:50] if entrevista.vaga_descricao else "Vaga"
    
    prompt = f"""Você é um especialista em recrutamento gerando um parecer final de entrevista.

CANDIDATO: {nome_candidato}
VAGA: {nome_vaga}
RESPOSTAS E AVALIAÇÕES:
{json.dumps(respostas_formatadas, ensure_ascii=False, indent=2)}

Retorne APENAS um JSON válido:
{{
  "score_geral": <1.0-10.0>,
  "parecer_final": "<1 parágrafo conclusivo>",
  "pontos_fortes": ["ponto1", "ponto2", "ponto3"],
  "pontos_fracos": ["fraco1", "fraco2", "fraco3"],
  "recomendacoes": ["rec1", "rec2", "rec3"],
  "recomendacao_gestor": "<contratável / reavaliável / não recomendado>"
}}

Diretrizes:
- score_geral: média dos scores individuais (1-10)
- Parecer: honesto e construtivo, 3-5 frases
- Pontos/Recomendações: máximo 5 cada
- Recomendação final: contratável (7+), reavaliável (4-6), não recomendado (<4)"""
    
    message = client.messages.create(
        model="mixtral-8x7b-32768",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
    )
    
    try:
        response_text = message.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        
        relatorio = json.loads(response_text)
        return relatorio
    except json.JSONDecodeError:
        logger.error(f"Erro ao parsear JSON da IA (relatório): {response_text}")
        # Fallback: calcular média simples
        scores = [p.avaliacao_resposta.get("score", 5) if p.avaliacao_resposta else 5 
                  for p in entrevista.perguntas]
        return {
            "score_geral": sum(scores) / len(scores) if scores else 5,
            "parecer_final": "Candidato avaliado com sucesso.",
            "pontos_fortes": ["Participação ativa", "Respostas claras"],
            "pontos_fracos": ["Algumas lacunas identificadas"],
            "recomendacoes": ["Aprofundar conhecimentos"],
            "recomendacao_gestor": "reavaliável"
        }
```

---

## 4. Routes Completo: `src/routes/entrevista.py`

```python
import os
import json
from datetime import datetime, timezone
from io import BytesIO

from flask import Blueprint, request, jsonify, render_template, session, send_file
from werkzeug.utils import secure_filename

from src.app import limiter
from src.config import UPLOAD_FOLDER, MAX_UPLOAD_BYTES
from src.logging_config import logger
from src.models.db import db
from src.models.entrevista import Entrevista, PerguntaEntrevista
from src.services.model import (
    gerar_plano_entrevista,
    avaliar_resposta,
    gerar_relatorio_final
)
from src.services.parser import extrair_texto_curriculo
from src.services.pdf import gerar_pdf_relatorio_entrevista
from src.utils import (
    login_required, allowed_file, carregar_arquivo, 
    sanitize_text, has_prompt_injection, get_file_size
)

bp = Blueprint("entrevista", __name__, url_prefix="/entrevista")


def _get_entrevista_or_404(entrevista_id: str):
    """Helper: pega entrevista ou 404"""
    entrevista = Entrevista.query.get(entrevista_id)
    if not entrevista or entrevista.user_id != session.get("user_id"):
        return None
    return entrevista


@bp.route("/", methods=["GET"])
@login_required
def entrevista_page():
    """Página inicial de planejamento"""
    return render_template("entrevista_planejamento.html")


@bp.route("/gerar-plano", methods=["POST"])
@login_required
@limiter.limit("5 per minute")
def gerar_plano():
    """Gera plano de entrevista a partir de currículo + vaga"""
    
    # Validar multipart
    if "curriculo" not in request.files:
        return jsonify({"error": "Currículo não fornecido"}), 400
    
    vaga_descricao = request.form.get("vaga_descricao", "").strip()
    if not vaga_descricao:
        return jsonify({"error": "Descrição da vaga não fornecida"}), 400
    
    if has_prompt_injection(vaga_descricao):
        return jsonify({"error": "Conteúdo inválido detectado"}), 422
    
    arquivo = request.files["curriculo"]
    if arquivo.filename == "":
        return jsonify({"error": "Arquivo vazio"}), 400
    
    # Validar arquivo
    if not allowed_file(arquivo.filename):
        return jsonify({"error": "Tipo de arquivo não permitido"}), 400
    
    # Validar tamanho
    file_size = get_file_size(arquivo)
    if file_size > MAX_UPLOAD_BYTES:
        return jsonify({"error": "Arquivo muito grande"}), 413
    
    try:
        # Salvar arquivo
        filename = secure_filename(arquivo.filename)
        caminho = os.path.join(UPLOAD_FOLDER, filename)
        arquivo.save(caminho)
        
        # Extrair texto
        curriculo_text = extrair_texto_curriculo(caminho)
        if not curriculo_text:
            return jsonify({"error": "Não foi possível extrair texto do currículo"}), 400
        
        # Chamar IA para gerar plano
        logger.info("Gerando plano de entrevista com IA")
        plano = gerar_plano_entrevista(curriculo_text, vaga_descricao)
        
        # Criar registro Entrevista
        entrevista = Entrevista(
            user_id=session["user_id"],
            curriculo_arquivo=filename,
            vaga_descricao=vaga_descricao,
            numero_perguntas=plano["numero_perguntas"],
            plano_entrevista=plano,
            status="em_planejamento"
        )
        db.session.add(entrevista)
        db.session.flush()  # Get ID antes de commit
        
        # Criar PerguntaEntrevista para cada pergunta
        for i, pergunta_text in enumerate(plano["questoes_principais"], 1):
            pergunta = PerguntaEntrevista(
                entrevista_id=entrevista.id,
                numero_sequencial=i,
                pergunta_principal=pergunta_text
            )
            db.session.add(pergunta)
        
        db.session.commit()
        
        logger.info(f"Plano gerado para entrevista {entrevista.id}")
        
        return jsonify({
            "entrevista_id": entrevista.id,
            "numero_perguntas": plano["numero_perguntas"],
            "plano": {
                "topicos": plano["topicos_principais"],
                "estrategia": plano["estrategia_entrevista"],
                "questoes": plano["questoes_principais"]
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao gerar plano: {str(e)}")
        return jsonify({"error": "Erro ao gerar plano"}), 500


@bp.route("/<entrevista_id>", methods=["GET"])
@login_required
def get_entrevista(entrevista_id):
    """Retorna dados da entrevista"""
    entrevista = _get_entrevista_or_404(entrevista_id)
    if not entrevista:
        return jsonify({"error": "Entrevista não encontrada"}), 404
    
    return jsonify({
        "id": entrevista.id,
        "status": entrevista.status,
        "numero_perguntas": entrevista.numero_perguntas,
        "plano_entrevista": entrevista.plano_entrevista,
        "criado_em": entrevista.criado_em.isoformat(),
        "perguntas": [
            {
                "numero_sequencial": p.numero_sequencial,
                "pergunta_principal": p.pergunta_principal,
                "respondido": p.resposta_usuario is not None,
                "score": p.avaliacao_resposta.get("score") if p.avaliacao_resposta else None
            }
            for p in entrevista.perguntas
        ]
    }), 200


@bp.route("/<entrevista_id>/pergunta/<int:numero>", methods=["GET"])
@login_required
def get_pergunta(entrevista_id, numero):
    """Retorna pergunta específica"""
    entrevista = _get_entrevista_or_404(entrevista_id)
    if not entrevista:
        return jsonify({"error": "Entrevista não encontrada"}), 404
    
    pergunta = PerguntaEntrevista.query.filter_by(
        entrevista_id=entrevista_id,
        numero_sequencial=numero
    ).first()
    
    if not pergunta:
        return jsonify({"error": "Pergunta não encontrada"}), 404
    
    return jsonify({
        "pergunta_id": pergunta.id,
        "numero_sequencial": pergunta.numero_sequencial,
        "pergunta_principal": pergunta.pergunta_principal,
        "resposta_anterior": pergunta.resposta_usuario,
        "aprofundamentos_pendentes": len(pergunta.perguntas_aprofundamento or []) if pergunta.perguntas_aprofundamento else 0,
        "total_perguntas": entrevista.numero_perguntas
    }), 200


@bp.route("/<entrevista_id>/responder", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def responder_pergunta(entrevista_id):
    """Salva resposta e gera aprofundamentos se necessário"""
    entrevista = _get_entrevista_or_404(entrevista_id)
    if not entrevista:
        return jsonify({"error": "Entrevista não encontrada"}), 404
    
    data = request.get_json()
    numero_seq = data.get("numero_sequencial")
    resposta = sanitize_text(data.get("resposta", ""))
    tipo_resposta = data.get("tipo", "principal")
    
    if not resposta or len(resposta) > 2000:
        return jsonify({"error": "Resposta inválida"}), 400
    
    if has_prompt_injection(resposta):
        return jsonify({"error": "Conteúdo inválido"}), 422
    
    try:
        # Encontrar pergunta
        pergunta = PerguntaEntrevista.query.filter_by(
            entrevista_id=entrevista_id,
            numero_sequencial=numero_seq
        ).first()
        
        if not pergunta:
            return jsonify({"error": "Pergunta não encontrada"}), 404
        
        # Atualizar status
        if entrevista.status == "em_planejamento":
            entrevista.status = "em_andamento"
        
        # Salvar resposta
        pergunta.resposta_usuario = resposta
        pergunta.respondido_em = datetime.now(timezone.utc)
        db.session.add(pergunta)
        db.session.commit()
        
        # Chamar IA para avaliar
        logger.info(f"Avaliando pergunta {numero_seq} da entrevista {entrevista_id}")
        
        contexto = {
            "curriculo_resumo": entrevista.plano_entrevista.get("estrategia_entrevista", "")[:500],
            "vaga_resumida": entrevista.vaga_descricao[:500],
            "pergunta_numero": numero_seq
        }
        
        avaliacao = avaliar_resposta(
            pergunta.pergunta_principal,
            resposta,
            contexto
        )
        
        # Salvar avaliação
        pergunta.avaliacao_resposta = {
            "feedback": avaliacao.get("feedback", ""),
            "score": avaliacao.get("score", 5),
            "aprofundar": avaliacao.get("deve_aprofundar", False)
        }
        
        # Gerar e salvar aprofundamentos se necessário
        aprofundamentos_resposta = []
        if avaliacao.get("deve_aprofundar") and avaliacao.get("perguntas_aprofundamento"):
            pergunta.perguntas_aprofundamento = [
                {
                    "pergunta": ap,
                    "resposta": None,
                    "feedback": None
                }
                for ap in avaliacao["perguntas_aprofundamento"][:2]
            ]
            
            aprofundamentos_resposta = [
                {
                    "numero": i + 1,
                    "pergunta": ap,
                    "tipo": f"aprofundamento_{i+1}"
                }
                for i, ap in enumerate(avaliacao["perguntas_aprofundamento"][:2])
            ]
        
        db.session.commit()
        
        return jsonify({
            "salvo": True,
            "feedback_ia": avaliacao.get("feedback", ""),
            "score": avaliacao.get("score", 5),
            "aprofundamentos": aprofundamentos_resposta
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao responder pergunta: {str(e)}")
        return jsonify({"error": "Erro ao processar resposta"}), 500


@bp.route("/<entrevista_id>/finalizar", methods=["POST"])
@login_required
def finalizar_entrevista(entrevista_id):
    """Marca entrevista como concluída e gera relatório final"""
    entrevista = _get_entrevista_or_404(entrevista_id)
    if not entrevista:
        return jsonify({"error": "Entrevista não encontrada"}), 404
    
    # Verificar se todas perguntas foram respondidas
    nao_respondidas = PerguntaEntrevista.query.filter_by(
        entrevista_id=entrevista_id
    ).filter(PerguntaEntrevista.resposta_usuario == None).count()
    
    if nao_respondidas > 0:
        return jsonify({"error": "Ainda há perguntas não respondidas"}), 400
    
    try:
        # Gerar relatório
        logger.info(f"Gerando relatório final para entrevista {entrevista_id}")
        relatorio = gerar_relatorio_final(entrevista_id)
        
        # Atualizar entrevista
        entrevista.status = "concluida"
        entrevista.relatorio_final = relatorio
        entrevista.finalizado_em = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            "finalizado": True,
            "relatorio": relatorio
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao finalizar entrevista: {str(e)}")
        return jsonify({"error": "Erro ao gerar relatório"}), 500


@bp.route("/<entrevista_id>/relatorio", methods=["GET"])
@login_required
def relatorio(entrevista_id):
    """Exibe página do relatório"""
    entrevista = _get_entrevista_or_404(entrevista_id)
    if not entrevista:
        return jsonify({"error": "Entrevista não encontrada"}), 404
    
    if entrevista.status != "concluida":
        return jsonify({"error": "Entrevista ainda não foi concluída"}), 400
    
    return render_template("entrevista_relatorio.html", entrevista_id=entrevista_id)


@bp.route("/<entrevista_id>/exportar-pdf", methods=["GET"])
@login_required
def exportar_pdf(entrevista_id):
    """Exporta relatório em PDF"""
    entrevista = _get_entrevista_or_404(entrevista_id)
    if not entrevista:
        return jsonify({"error": "Entrevista não encontrada"}), 404
    
    if entrevista.status != "concluida":
        return jsonify({"error": "Entrevista ainda não foi concluída"}), 400
    
    try:
        pdf_bytes = gerar_pdf_relatorio_entrevista(entrevista)
        
        return send_file(
            BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"relatorio_entrevista_{entrevista.id}.pdf"
        )
    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {str(e)}")
        return jsonify({"error": "Erro ao gerar PDF"}), 500
```

---

## 5. Atualizar `src/app.py`

**Adicionar após linha 38 (imports de models):**

```python
    import src.models.entrevista       # noqa: F401
```

**Adicionar após linha 46 (imports de routes):**

```python
    from src.routes.entrevista import bp as entrevista_bp
```

**Adicionar após linha 49 (register blueprints):**

```python
    app.register_blueprint(entrevista_bp)
```

**Resultado (linhas 36-51):**

```python
    # Registra todos os models com o Alembic
    import src.models.user          # noqa: F401
    import src.models.analise       # noqa: F401
    import src.models.otimizacao    # noqa: F401
    import src.models.chat_session  # noqa: F401
    import src.models.entrevista    # noqa: F401  <- NOVO

    limiter.init_app(app)

    # ... código ...

    from src.routes.auth import bp as auth_bp
    from src.routes.home import bp as home_bp
    from src.routes.chat import bp as chat_bp
    from src.routes.analisar import bp as analisar_bp
    from src.routes.entrevista import bp as entrevista_bp  # <- NOVO

    app.register_blueprint(auth_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(analisar_bp)
    app.register_blueprint(entrevista_bp)  # <- NOVO
```

---

## 6. Função PDF: `src/services/pdf.py`

**Adicionar ao fim do arquivo:**

```python
def gerar_pdf_relatorio_entrevista(entrevista) -> bytes:
    """
    Gera PDF do relatório de entrevista.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    
    # Criar PDF em memória
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm)
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=10,
        alignment=TA_CENTER
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c5282'),
        spaceAfter=6,
        spaceBefore=12
    )
    
    # Conteúdo
    content = []
    
    # Cabeçalho
    content.append(Paragraph("Relatório de Entrevista", title_style))
    content.append(Spacer(1, 0.3*cm))
    
    # Informações gerais
    info_style = ParagraphStyle(
        'Info',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    from datetime import datetime
    data_str = datetime.now().strftime("%d/%m/%Y às %H:%M")
    content.append(Paragraph(f"Gerado em {data_str}", info_style))
    content.append(Spacer(1, 0.5*cm))
    
    # Score geral em destaque
    score = entrevista.relatorio_final.get("score_geral", 0)
    score_color = colors.green if score >= 7 else (colors.orange if score >= 4 else colors.red)
    score_table = Table([
        [Paragraph(f"<font size=32 color='{score_color.hexval()}'>{score:.1f}</font>/10", 
                   ParagraphStyle('Score', parent=styles['Normal'], alignment=TA_CENTER))]
    ], colWidths=[17*cm])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f0f0')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
        ('TOPPADDING', (0, 0), (-1, -1), 20),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
        ('BORDER', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    content.append(score_table)
    content.append(Spacer(1, 0.5*cm))
    
    # Parecer final
    content.append(Paragraph("Parecer", heading_style))
    parecer = entrevista.relatorio_final.get("parecer_final", "")
    content.append(Paragraph(parecer, ParagraphStyle('Normal', parent=styles['Normal'], alignment=TA_JUSTIFY)))
    content.append(Spacer(1, 0.3*cm))
    
    # Pontos fortes
    content.append(Paragraph("Pontos Fortes", heading_style))
    pontos_fortes = entrevista.relatorio_final.get("pontos_fortes", [])
    for ponto in pontos_fortes:
        content.append(Paragraph(f"• {ponto}", styles['Normal']))
    content.append(Spacer(1, 0.3*cm))
    
    # Pontos fracos
    content.append(Paragraph("Pontos a Melhorar", heading_style))
    pontos_fracos = entrevista.relatorio_final.get("pontos_fracos", [])
    for ponto in pontos_fracos:
        content.append(Paragraph(f"• {ponto}", styles['Normal']))
    content.append(Spacer(1, 0.3*cm))
    
    # Recomendações
    content.append(Paragraph("Recomendações", heading_style))
    recomendacoes = entrevista.relatorio_final.get("recomendacoes", [])
    for rec in recomendacoes:
        content.append(Paragraph(f"• {rec}", styles['Normal']))
    content.append(Spacer(1, 0.5*cm))
    
    # Perguntas e respostas
    content.append(PageBreak())
    content.append(Paragraph("Detalhes das Perguntas", heading_style))
    
    for p in entrevista.perguntas:
        # Cabeçalho da pergunta
        pergunta_header = f"Pergunta {p.numero_sequencial}: "
        if p.avaliacao_resposta:
            score_p = p.avaliacao_resposta.get("score", 5)
            pergunta_header += f"(Score: {score_p}/10)"
        
        content.append(Paragraph(pergunta_header, 
                                ParagraphStyle('PerguntaHeader', parent=styles['Normal'], 
                                             fontSize=11, textColor=colors.HexColor('#2c5282'))))
        content.append(Paragraph(p.pergunta_principal, styles['Normal']))
        content.append(Spacer(1, 0.1*cm))
        
        # Resposta
        content.append(Paragraph("<b>Resposta:</b>", 
                                ParagraphStyle('Bold', parent=styles['Normal'])))
        content.append(Paragraph(p.resposta_usuario or "[Não respondida]", styles['Normal']))
        content.append(Spacer(1, 0.1*cm))
        
        # Feedback
        if p.avaliacao_resposta:
            feedback = p.avaliacao_resposta.get("feedback", "")
            content.append(Paragraph("<b>Feedback:</b>", 
                                    ParagraphStyle('Bold', parent=styles['Normal'])))
            content.append(Paragraph(feedback, styles['Normal']))
        
        # Aprofundamentos
        if p.perguntas_aprofundamento:
            content.append(Spacer(1, 0.1*cm))
            content.append(Paragraph("<i>Aprofundamentos</i>", 
                                    ParagraphStyle('Italic', parent=styles['Normal'], 
                                                 textColor=colors.grey)))
            for i, ap in enumerate(p.perguntas_aprofundamento, 1):
                content.append(Paragraph(f"<b>Aprofundamento {i}:</b> {ap.get('pergunta', '')}", 
                                        styles['Normal']))
                if ap.get('resposta'):
                    content.append(Paragraph(f"Resposta: {ap['resposta']}", styles['Normal']))
                if ap.get('feedback'):
                    content.append(Paragraph(f"Feedback: {ap['feedback']}", styles['Normal']))
        
        content.append(Spacer(1, 0.3*cm))
    
    # Rodapé
    content.append(Spacer(1, 0.5*cm))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    content.append(Paragraph("Documento gerado automaticamente pelo Simulador de Entrevistas", 
                            footer_style))
    
    # Gerar PDF
    doc.build(content)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()
```

---

## 7. Migração Alembic

**Executar no terminal:**

```bash
cd /mnt/c/Users/<seu-usuario>/SD_Trabalho
source venv/bin/activate
alembic revision --autogenerate -m "Add entrevista and pergunta_entrevista tables"
alembic upgrade head
```

Isso vai criar um arquivo em `migrations/versions/` automaticamente.

