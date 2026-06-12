# ⚡ Quick Reference - Simulador de Entrevistas

## 📋 Arquivos a Criar/Modificar

### ✅ CRIAR (Novos Arquivos)

```
src/models/entrevista.py                              # Models: Entrevista, PerguntaEntrevista
src/routes/entrevista.py                              # Routes: blueprint com 7 endpoints
src/templates/entrevista_planejamento.html            # Tela 1: Upload + Gerar Plano
src/templates/entrevista_execucao.html                # Tela 2: Execução interativa
src/templates/entrevista_relatorio.html               # Tela 3: Relatório + PDF
src/static/entrevista.css                             # Estilos
src/static/entrevista.js                              # JavaScript interativo
migrations/versions/XXXX_add_entrevista_tables.py     # Migration Alembic
```

### ✏️ MODIFICAR (Arquivos Existentes)

```
src/app.py
  ├─ import src.models.entrevista  (após linha 38)
  ├─ import src.routes.entrevista   (após linha 46)
  ├─ app.register_blueprint(entrevista_bp)  (após linha 49)

src/models/user.py
  ├─ entrevistas = db.relationship("Entrevista", back_populates="user", lazy="dynamic")
  
src/services/model.py
  ├─ def gerar_plano_entrevista(curriculo_text, vaga_descricao) -> dict
  ├─ def avaliar_resposta(pergunta, resposta, contexto) -> dict
  ├─ def gerar_relatorio_final(entrevista_id) -> dict

src/services/pdf.py
  ├─ def gerar_pdf_relatorio_entrevista(relatorio) -> bytes
```

---

## 🗄️ Models: Estrutura Essencial

### `src/models/entrevista.py`

```python
import uuid
from datetime import datetime, timezone
from src.models.db import db

class Entrevista(db.Model):
    __tablename__ = "entrevista"
    
    # PK
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # FK
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    
    # Dados
    curriculo_arquivo = db.Column(db.String(255), nullable=False)
    vaga_descricao = db.Column(db.Text, nullable=False)
    numero_perguntas = db.Column(db.Integer, nullable=False)
    plano_entrevista = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='em_planejamento')
    
    # Timestamps
    criado_em = db.Column(db.DateTime(timezone=True), nullable=False, 
                          default=lambda: datetime.now(timezone.utc))
    atualizado_em = db.Column(db.DateTime(timezone=True), nullable=False,
                              default=lambda: datetime.now(timezone.utc))
    finalizado_em = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # Resultado
    relatorio_final = db.Column(db.JSON, nullable=True)
    
    # Relationships
    user = db.relationship("User", back_populates="entrevistas")
    perguntas = db.relationship("PerguntaEntrevista", back_populates="entrevista", 
                                cascade="all, delete-orphan")


class PerguntaEntrevista(db.Model):
    __tablename__ = "pergunta_entrevista"
    
    # PK
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # FK
    entrevista_id = db.Column(db.String(36), db.ForeignKey("entrevista.id"), 
                              nullable=False)
    
    # Dados
    numero_sequencial = db.Column(db.Integer, nullable=False)
    pergunta_principal = db.Column(db.Text, nullable=False)
    resposta_usuario = db.Column(db.Text, nullable=True)
    avaliacao_resposta = db.Column(db.JSON, nullable=True)
    perguntas_aprofundamento = db.Column(db.JSON, nullable=True)
    
    # Timestamps
    criado_em = db.Column(db.DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))
    respondido_em = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # Relationships
    entrevista = db.relationship("Entrevista", back_populates="perguntas")
```

---

## 🔌 Endpoints: Assinatura Essencial

### `src/routes/entrevista.py`

```python
from flask import Blueprint, request, jsonify, render_template, session, send_file
from src.app import limiter
from src.models.db import db
from src.models.entrevista import Entrevista, PerguntaEntrevista
from src.services.model import (
    gerar_plano_entrevista,
    avaliar_resposta,
    gerar_relatorio_final
)
from src.services.pdf import gerar_pdf_relatorio_entrevista
from src.utils import login_required, allowed_file, carregar_arquivo, sanitize_text, has_prompt_injection

bp = Blueprint("entrevista", __name__, url_prefix="/entrevista")

# 1. POST /entrevista/gerar-plano
@bp.route("/gerar-plano", methods=["POST"])
@login_required
@limiter.limit("5 per minute")
def gerar_plano():
    """Recebe currículo + vaga, gera plano de entrevista"""
    # TODO: implementar
    pass

# 2. GET /entrevista/<id>
@bp.route("/<entrevista_id>", methods=["GET"])
@login_required
def get_entrevista(entrevista_id):
    """Retorna dados da entrevista"""
    # TODO: implementar
    pass

# 3. GET /entrevista/<id>/pergunta/<numero>
@bp.route("/<entrevista_id>/pergunta/<int:numero>", methods=["GET"])
@login_required
def get_pergunta(entrevista_id, numero):
    """Retorna próxima pergunta"""
    # TODO: implementar
    pass

# 4. POST /entrevista/<id>/responder
@bp.route("/<entrevista_id>/responder", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def responder_pergunta(entrevista_id):
    """Salva resposta e gera aprofundamentos"""
    # TODO: implementar
    pass

# 5. POST /entrevista/<id>/finalizar
@bp.route("/<entrevista_id>/finalizar", methods=["POST"])
@login_required
def finalizar_entrevista(entrevista_id):
    """Marca como concluída e gera relatório"""
    # TODO: implementar
    pass

# 6. GET /entrevista/<id>/relatorio
@bp.route("/<entrevista_id>/relatorio", methods=["GET"])
@login_required
def relatorio(entrevista_id):
    """Exibe página do relatório"""
    # TODO: implementar
    pass

# 7. GET /entrevista/<id>/exportar-pdf
@bp.route("/<entrevista_id>/exportar-pdf", methods=["GET"])
@login_required
def exportar_pdf(entrevista_id):
    """Retorna PDF do relatório"""
    # TODO: implementar
    pass

# Página inicial
@bp.route("/", methods=["GET"])
@login_required
def entrevista_page():
    """Exibe tela de planejamento"""
    return render_template("entrevista_planejamento.html")
```

---

## 🤖 Funções de IA: Assinatura

### `src/services/model.py` (adicionar estas funções)

```python
def gerar_plano_entrevista(curriculo_text: str, vaga_descricao: str) -> dict:
    """
    Analisa currículo + vaga e gera plano de entrevista.
    
    Returns:
    {
        "numero_perguntas": int (5-8),
        "topicos_principais": [str, ...],
        "estrategia_entrevista": str,
        "questoes_principais": [str, ...]  # N perguntas
    }
    """
    # TODO: implementar
    pass


def avaliar_resposta(pergunta: str, resposta: str, contexto: dict) -> dict:
    """
    IA avalia resposta do usuário.
    
    contexto = {
        "curriculo_resumo": str,
        "vaga_resumida": str,
        "pergunta_numero": int
    }
    
    Returns:
    {
        "feedback": str,
        "score": int (1-10),
        "deve_aprofundar": bool,
        "perguntas_aprofundamento": [str, str]  # até 2
    }
    """
    # TODO: implementar
    pass


def gerar_relatorio_final(entrevista_id: str) -> dict:
    """
    Coleta todas respostas e gera análise final.
    
    Returns:
    {
        "score_geral": float (1-10),
        "parecer_final": str,
        "pontos_fortes": [str, ...],
        "pontos_fracos": [str, ...],
        "recomendacoes": [str, ...],
        "recomendacao_gestor": str
    }
    """
    # TODO: implementar
    pass
```

---

## 📄 PDF Export: Função Essencial

### `src/services/pdf.py` (adicionar esta função)

```python
def gerar_pdf_relatorio_entrevista(entrevista: Entrevista) -> bytes:
    """
    Gera PDF do relatório de entrevista.
    
    Conteúdo:
    - Cabeçalho (data, candidato, vaga)
    - Score geral em destaque
    - Pontos fortes / fracos / recomendações
    - Cada pergunta com resposta e feedback
    - Rodapé
    
    Returns: bytes do PDF
    """
    # TODO: implementar
    pass
```

---

## 🔑 Prompts de IA (Groq)

### Prompt 1: Gerar Plano

```python
PROMPT_GERAR_PLANO = """
Você é um especialista em recrutamento e entrevistas técnicas.

Analise o currículo e a descrição da vaga fornecidos e gere um plano de entrevista estruturado.

CURRÍCULO:
{curriculo_text}

VAGA:
{vaga_descricao}

Retorne APENAS um JSON válido (sem explicações):
{{
  "numero_perguntas": <5-8>,
  "topicos_principais": ["tópico1", "tópico2", ...],
  "estrategia_entrevista": "<parágrafo breve com a abordagem>",
  "questoes_principais": ["pergunta1", "pergunta2", ...]
}}

Diretrizes:
- numero_perguntas: entre 5 e 8, baseado na complexidade
- questoes_principais: deve ter exatamente numero_perguntas itens
- Perguntas deve ser técnicas, comportamentais e sobre experiências
- Considere gaps entre CV e vaga
- Use linguagem clara e profissional
"""
```

### Prompt 2: Avaliar Resposta

```python
PROMPT_AVALIAR_RESPOSTA = """
Você é um entrevistador técnico experiente avaliando a resposta de um candidato.

PERGUNTA: {pergunta}
RESPOSTA DO CANDIDATO: {resposta}
CURRÍCULO (resumido): {curriculo_resumo}
VAGA (resumida): {vaga_resumida}

Retorne APENAS um JSON válido:
{{
  "feedback": "<feedback construtivo, 2-3 frases>",
  "score": <1-10>,
  "deve_aprofundar": <true/false>,
  "perguntas_aprofundamento": ["<pergunta1>", "<pergunta2>"]
}}

Critérios de Score:
- 1-3: Resposta incompleta, incorreta ou não relacionada
- 4-6: Resposta aceitável, mas com lacunas importantes
- 7-8: Resposta boa, bem estruturada e relevante
- 9-10: Resposta excelente, detalhada e exemplificada

Aprofundamento:
- Fazer apenas se score >= 7 ou se há pontos críticos não mencionados
- Máximo 2 perguntas
- Deve complementar/aprofundar aspecto específico mencionado na resposta
"""
```

### Prompt 3: Gerar Relatório Final

```python
PROMPT_GERAR_RELATORIO = """
Você é um especialista em recrutamento gerando um parecer final de entrevista.

CANDIDATO: {nome_candidato}
VAGA: {nome_vaga}
RESPOSTAS E AVALIAÇÕES:
{respostas_json_formatado}

Retorne APENAS um JSON válido:
{{
  "score_geral": <1.0-10.0>,
  "parecer_final": "<1 parágrafo conclusivo sobre o candidato>",
  "pontos_fortes": ["ponto1", "ponto2", "ponto3"],
  "pontos_fracos": ["fraco1", "fraco2", "fraco3"],
  "recomendacoes": ["rec1", "rec2", "rec3"],
  "recomendacao_gestor": "<contratável / reavaliável / não recomendado>"
}}

Diretrizes:
- score_geral: média ponderada dos scores individuais
- Seja honesto e construtivo
- Pontos fortes/fracos: máximo 5 cada
- Recomendações: ações concretas para o candidato melhorar
- Recomendação final: com base no score_geral e qualidade das respostas
"""
```

---

## 🎯 Fluxo de Implementação (Ordem Recomendada)

### Fase 1: Backend Base (1-2 horas)
1. ✅ Criar `models/entrevista.py`
2. ✅ Gerar migração Alembic
3. ✅ Aplicar migração
4. ✅ Modificar `user.py` (adicionar relationship)

### Fase 2: Endpoints Básicos (2-3 horas)
1. ✅ Criar `routes/entrevista.py` com 7 endpoints
2. ✅ Implementar validações básicas
3. ✅ Testar com Postman/curl

### Fase 3: Integração IA (2-3 horas)
1. ✅ Adicionar funções em `services/model.py`
2. ✅ Integrar Groq API
3. ✅ Testar prompts
4. ✅ Refinar respostas

### Fase 4: Frontend (3-4 horas)
1. ✅ Criar 3 templates HTML
2. ✅ Criar `entrevista.css` e `entrevista.js`
3. ✅ Testar fluxo de UX
4. ✅ Adicionar validações cliente

### Fase 5: PDF & Polish (1-2 horas)
1. ✅ Estender `pdf.py` para relatório
2. ✅ Testar exportação
3. ✅ Tratamento de erros
4. ✅ Testes finais

---

## 🧪 Testes Manuais

### Teste 1: Fluxo Completo
```
1. Login
2. Ir para /entrevista
3. Upload CV + vaga
4. Gerar plano (aguardar IA)
5. Iniciar entrevista
6. Responder 5 perguntas
7. Finalizar
8. Ver relatório
9. Exportar PDF
```

### Teste 2: Aprofundamentos
```
1. Parar em pergunta com score alto (7+)
2. Verificar se aparecem 1-2 aprofundamentos
3. Responder aprofundamentos
4. Verificar se foram salvos no relatório
```

### Teste 3: PDF Export
```
1. Concluir entrevista
2. Ver relatório
3. Clicar "Exportar PDF"
4. Abrir PDF
5. Verificar: cabeçalho, score, perguntas, aprofundamentos
```

---

## 🔒 Validações Críticas

### Backend
```
POST /gerar-plano:
  ✅ User autenticado (@login_required)
  ✅ Arquivo válido (allowed_file, < 5MB)
  ✅ Vaga não vazia
  ✅ Prompt injection check

POST /responder:
  ✅ User autenticado
  ✅ Entrevista pertence ao user
  ✅ Resposta não vazia
  ✅ Resposta < 2000 chars
  ✅ Pergunta existe e não foi respondida

POST /finalizar:
  ✅ User autenticado
  ✅ Todas perguntas respondidas
  ✅ Status em_andamento
```

### Frontend
```
entrevista_planejamento.html:
  ✅ Upload obrigatório
  ✅ Vaga obrigatória
  ✅ Validação tipo arquivo (client-side)

entrevista_execucao.html:
  ✅ Resposta não vazia
  ✅ Desabilitar botão durante envio
  ✅ Mostrar spinner
  ✅ Tratar erros de rede
```

---

## 🐛 Debugging Tips

### Problema: Plano não é gerado
- [ ] Verificar se Groq API key está configurada
- [ ] Verificar logs de requisição para Groq
- [ ] Testar currículo extraído (print)

### Problema: Aprofundamentos não aparecem
- [ ] Verificar JSON retornado (console.log)
- [ ] Verificar lógica de deve_aprofundar
- [ ] Testar com respostas que merecem score alto (7+)

### Problema: PDF não gera
- [ ] Verificar se Poppler está instalado (`apt list --installed | grep poppler`)
- [ ] Verificar erros em `services/pdf.py`
- [ ] Testar geração com dados mínimos

---

## 📦 Dependências (Já Existentes)

```
✅ Flask
✅ SQLAlchemy
✅ Alembic
✅ Groq (API)
✅ ReportLab (PDF)
✅ PIL (Imagens)
✅ werkzeug (Upload)
```

---

## 🚀 Deployment Checklist

- [ ] Migração Alembic executada em produção
- [ ] Groq API key em variável de ambiente
- [ ] Poppler instalado no servidor
- [ ] Permissões de pasta `logs/` e `uploads/`
- [ ] Rate limiting testado
- [ ] CORS (se frontend separado)
- [ ] Tests automatizados (opcional)

