# 🎯 Especificação: Simulador de Entrevistas

## 📌 Resumo Executivo

Reformulação do sistema de entrevistas de IA. O **chat existente é preservado** (pode ser renomeado para "Assistente Geral" ou "Chat Livre"). A **nova funcionalidade de simulação de entrevista** será uma jornada estruturada em 3 fases:

1. **Planejamento**: Usuário submete currículo + vaga → Sistema gera plano de entrevista
2. **Execução**: IA faz perguntas, usuário responde, IA faz até 2 aprofundamentos por pergunta
3. **Relatório**: Gera análise completa exportável em PDF

---

## 🏗️ Arquitetura de Banco de Dados

### Diagrama de Relacionamentos

```
users (existente)
    └── entrevista (novo)
            └── pergunta_entrevista (novo)
```

### Modelo: `Entrevista`

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `id` | UUID | ✅ | Chave primária |
| `user_id` | FK(users) | ✅ | Usuário proprietário |
| `curriculo_arquivo` | String(255) | ✅ | Caminho do arquivo carregado |
| `vaga_descricao` | Text | ✅ | Descrição da vaga (cópia para auditoria) |
| `numero_perguntas` | Integer | ✅ | Quantidade de perguntas principais (5-8 típico) |
| `plano_entrevista` | JSON | ✅ | Estrutura: `{topicos: [], estrategia: "", questoes: []}` |
| `status` | String | ✅ | Estados: `em_planejamento` → `em_andamento` → `concluida` |
| `criado_em` | DateTime | ✅ | Timestamp de criação |
| `atualizado_em` | DateTime | ✅ | Timestamp de última atualização |
| `finalizado_em` | DateTime | ❌ | Timestamp quando concluída (NULL se em andamento) |
| `relatorio_final` | JSON | ❌ | Análise final + scores (gerado ao finalizar) |

### Modelo: `PerguntaEntrevista`

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `id` | UUID | ✅ | Chave primária |
| `entrevista_id` | FK(entrevista) | ✅ | Referência à entrevista |
| `numero_sequencial` | Integer | ✅ | Ordem (1, 2, 3...) |
| `pergunta_principal` | Text | ✅ | A pergunta feita |
| `resposta_usuario` | Text | ❌ | Resposta do usuário (NULL até responder) |
| `avaliacao_resposta` | JSON | ❌ | `{feedback: "", score: 1-10, aprofundar: bool}` |
| `perguntas_aprofundamento` | JSON | ❌ | Array com até 2 itens: `[{pergunta: "", resposta: "", feedback: ""}]` |
| `criado_em` | DateTime | ✅ | Quando foi gerada |
| `respondido_em` | DateTime | ❌ | Quando o usuário respondeu |

---

## 🔄 Fluxo da Aplicação

### FASE 1: Planejamento (`/entrevista`)

```
[Tela] Planejamento
  ↓
  1. Upload Currículo (PDF/DOC/DOCX)
  2. Textarea: Cole a Descrição da Vaga
  3. Botão "Gerar Plano de Entrevista"
  ↓
[Backend] POST /entrevista/gerar-plano
  → Extrai texto do currículo (parser.py)
  → Envia currículo + vaga para IA (Groq)
  → Recebe: número de perguntas, tópicos, estratégia
  → Cria 5-8 perguntas principais (pré-geradas)
  → Salva como Entrevista (status='em_planejamento')
  → Cria PerguntaEntrevista (sem respostas ainda)
  ↓
[Tela] Exibe Plano
  → "Vamos fazer X perguntas sobre Y tópicos"
  → Lista tópicos
  → Botão "Iniciar Entrevista" (→ FASE 2)
```

### FASE 2: Execução (`/entrevista/<id>/executar`)

```
[Tela] Pergunta Atual (Pergunta 1/5)
  ↓
  1. Exibe pergunta principal
  2. Textarea: Usuário responde
  3. Botão "Enviar Resposta"
  ↓
[Backend] POST /entrevista/<id>/responder
  → Valida resposta (não vazia, < limite chars)
  → Salva em PerguntaEntrevista.resposta_usuario
  → Envia para IA: pergunta + resposta
  → IA retorna: feedback + score (1-10) + deve_aprofundar (bool)
  ↓
[Decisão] Se deve_aprofundar == true:
  → IA gera 2 perguntas de aprofundamento
  → Salva em PerguntaEntrevista.perguntas_aprofundamento
  → Tela exibe: "Pergunta de Aprofundamento 1/2"
  → Usuário responde
  → Repete para aprofundamento 2
  → IA gera feedback para cada aprofundamento
  ↓
[Loop] Se pergunta < numero_perguntas:
  → GET /entrevista/<id>/pergunta/2
  → Tela volta para passo 1 (nova pergunta)
  ↓
[Fim] Ao responder última pergunta:
  → Botão "Finalizar Entrevista"
```

### FASE 3: Relatório (`/entrevista/<id>/relatorio`)

```
[Backend] POST /entrevista/<id>/finalizar
  → Coleta todas respostas + feedbacks
  → IA gera análise geral
  → Calcula score_geral (média ponderada)
  → Identifica pontos_fortes, pontos_fracos, recomendacoes
  → Salva em Entrevista.relatorio_final (JSON)
  → Muda status para 'concluida'
  ↓
[Tela] Exibe Relatório
  → Cabeçalho: Score Geral (X/10)
  → Resumo: Pontos Fortes, Pontos Fracos, Recomendações
  → Cada Pergunta (acordeão):
    • Pergunta Principal
    • Resposta do Usuário
    • Score + Feedback
    • [Se houver] Aprofundamentos (também acordeão)
  ↓
[Botões]
  → "Exportar PDF" (→ GET /entrevista/<id>/exportar-pdf)
  → "Nova Entrevista"
```

---

## 🔌 Endpoints da API

### Planejamento

#### `POST /entrevista/gerar-plano`
**Autenticação:** ✅ Login obrigatório

**Payload:**
```json
{
  "curriculo": File,
  "vaga_descricao": "string (text area)"
}
```

**Response (200):**
```json
{
  "entrevista_id": "uuid",
  "numero_perguntas": 5,
  "plano": {
    "topicos": ["Experiência em Python", "Liderança técnica", "Projetos pessoais"],
    "estrategia": "Começar com questões técnicas...",
    "questoes_principais": ["Qual sua experiência com Python?", ...]
  }
}
```

**Errors:**
- `400`: Arquivo inválido ou texto vago vazio
- `422`: Prompt injection detectado
- `429`: Rate limit

---

#### `GET /entrevista/<id>`
**Autenticação:** ✅ User propriétário

**Response (200):**
```json
{
  "id": "uuid",
  "status": "em_planejamento",
  "numero_perguntas": 5,
  "plano_entrevista": {...},
  "criado_em": "2026-06-12T10:00:00Z",
  "perguntas": [
    {
      "numero_sequencial": 1,
      "pergunta_principal": "...",
      "respondido": false
    }
  ]
}
```

---

### Execução

#### `GET /entrevista/<id>/pergunta/<numero>`
**Autenticação:** ✅ User proprietário

**Response (200):**
```json
{
  "pergunta_id": "uuid",
  "numero_sequencial": 1,
  "pergunta_principal": "Qual é sua experiência com Python?",
  "resposta_anterior": null,
  "aprofundamentos_pendentes": 0,
  "total_perguntas": 5
}
```

---

#### `POST /entrevista/<id>/responder`
**Autenticação:** ✅ User proprietário

**Payload:**
```json
{
  "numero_sequencial": 1,
  "resposta": "string (texto da resposta)",
  "tipo": "principal" || "aprofundamento_1" || "aprofundamento_2"
}
```

**Response (200):**
```json
{
  "salvo": true,
  "feedback_ia": "Boa resposta. Você mencionou...",
  "score": 8,
  "aprofundamentos": [
    {
      "numero": 1,
      "pergunta": "Qual foi o maior desafio que você enfrentou com concorrência?",
      "tipo": "aprofundamento_1"
    }
  ]
}
```

---

#### `POST /entrevista/<id>/finalizar`
**Autenticação:** ✅ User proprietário

**Payload:** `{}`

**Response (200):**
```json
{
  "finalizado": true,
  "relatorio": {
    "score_geral": 7.5,
    "pontos_fortes": ["Conhecimento sólido", "Comunicação clara"],
    "pontos_fracos": ["Faltou menção a testes"],
    "recomendacoes": ["Estudar TDD", "Aprofundar em AWS"]
  }
}
```

---

### Relatório & Exportação

#### `GET /entrevista/<id>/relatorio`
**Autenticação:** ✅ User proprietário

**Response (200):** HTML renderizado com relatório completo

---

#### `GET /entrevista/<id>/exportar-pdf`
**Autenticação:** ✅ User proprietário

**Response:** Arquivo PDF com download

**Conteúdo PDF:**
- Cabeçalho (data, nome candidato)
- Resumo do plano (vaga, tópicos)
- Score geral em destaque
- Pontos fortes / fracos / recomendações
- Cada pergunta com resposta e feedback
- Rodapé (assinado por "Simulador IA")

---

## 🎨 Interface & Templates

### 1️⃣ `entrevista_planejamento.html`

```html
<div class="entrevista-container">
  <h1>Simulador de Entrevista</h1>
  
  <form id="form-planejamento" enctype="multipart/form-data">
    
    <div class="form-group">
      <label>Carregue seu Currículo</label>
      <input type="file" name="curriculo" accept=".pdf,.doc,.docx" required>
      <small>Máximo 5MB</small>
    </div>
    
    <div class="form-group">
      <label>Descrição da Vaga</label>
      <textarea name="vaga_descricao" placeholder="Cole a descrição completa da vaga aqui..." required></textarea>
    </div>
    
    <button type="submit" class="btn btn-primary">Gerar Plano de Entrevista</button>
  </form>
  
  <div id="resultado-plano" style="display:none;">
    <div class="alert alert-info">
      <h3>✅ Plano Gerado!</h3>
      <p>Vamos fazer <strong id="num-perguntas">5</strong> perguntas sobre os seguintes tópicos:</p>
      <ul id="topicos-list"></ul>
    </div>
    <a href="#" class="btn btn-success" id="btn-iniciar">Iniciar Entrevista →</a>
  </div>
</div>

<style>
.entrevista-container { max-width: 800px; margin: 0 auto; padding: 20px; }
.form-group { margin-bottom: 20px; }
textarea { width: 100%; min-height: 200px; }
</style>

<script>
document.getElementById('form-planejamento').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const formData = new FormData(e.target);
  const res = await fetch('/entrevista/gerar-plano', { method: 'POST', body: formData });
  const data = await res.json();
  
  // Salvar ID para próxima tela
  window.entrevistaId = data.entrevista_id;
  
  // Exibir plano
  document.getElementById('num-perguntas').textContent = data.numero_perguntas;
  document.getElementById('topicos-list').innerHTML = 
    data.plano.topicos.map(t => `<li>${t}</li>`).join('');
  
  document.getElementById('resultado-plano').style.display = 'block';
  document.getElementById('btn-iniciar').href = `/entrevista/${data.entrevista_id}/executar`;
});
</script>
```

---

### 2️⃣ `entrevista_execucao.html`

```html
<div class="entrevista-container">
  <div class="progresso-bar">
    <span id="progresso-texto">Pergunta 1 de 5</span>
    <div class="barra">
      <div class="preenchimento" id="barra-preenchimento" style="width: 20%"></div>
    </div>
  </div>
  
  <div class="pergunta-card">
    <h2 id="pergunta-titulo">Qual é sua experiência com Python?</h2>
    
    <form id="form-resposta">
      <textarea id="resposta-input" placeholder="Digite sua resposta aqui..." required></textarea>
      
      <div class="botoes">
        <button type="submit" class="btn btn-primary">Enviar Resposta</button>
      </div>
    </form>
  </div>
  
  <div id="feedback-box" style="display:none;">
    <h3>Feedback</h3>
    <p id="feedback-texto"></p>
    <div class="score">Score: <strong id="score-valor">8</strong>/10</div>
  </div>
  
  <div id="aprofundamento-box" style="display:none;">
    <h3>Pergunta de Aprofundamento</h3>
    <p id="pergunta-aprofundamento"></p>
    <form id="form-aprofundamento">
      <textarea id="resposta-aprofundamento" placeholder="Sua resposta..." required></textarea>
      <button type="submit" class="btn btn-primary">Responder</button>
    </form>
  </div>
  
  <div id="proxima-pergunta" style="display:none;">
    <button class="btn btn-success" onclick="proximaPergunta()">Próxima Pergunta →</button>
  </div>
</div>

<style>
.progresso-bar { margin-bottom: 30px; }
.barra { width: 100%; height: 10px; background: #eee; border-radius: 5px; }
.preenchimento { height: 100%; background: #007bff; transition: width 0.3s; }
.pergunta-card { background: #f9f9f9; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
textarea { width: 100%; min-height: 150px; }
.feedback-box { background: #d4edda; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
.score { font-size: 18px; margin-top: 10px; }
</style>

<script>
let entrevistaId = new URLSearchParams(window.location.search).get('id');
let perguntaAtual = 1;
let totalPerguntas = 5;
let contadorAprofundamentos = 0;

document.getElementById('form-resposta').addEventListener('submit', async (e) => {
  e.preventDefault();
  const resposta = document.getElementById('resposta-input').value;
  
  const res = await fetch(`/entrevista/${entrevistaId}/responder`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      numero_sequencial: perguntaAtual,
      resposta: resposta,
      tipo: 'principal'
    })
  });
  
  const data = await res.json();
  
  // Esconder formulário, mostrar feedback
  document.getElementById('form-resposta').style.display = 'none';
  document.getElementById('feedback-box').style.display = 'block';
  document.getElementById('feedback-texto').textContent = data.feedback_ia;
  document.getElementById('score-valor').textContent = data.score;
  
  // Se tem aprofundamentos
  if (data.aprofundamentos.length > 0) {
    contadorAprofundamentos = 0;
    mostrarAprofundamento(data.aprofundamentos);
  } else {
    // Mostrar botão próxima pergunta
    if (perguntaAtual < totalPerguntas) {
      document.getElementById('proxima-pergunta').style.display = 'block';
    } else {
      // Última pergunta - mostrar finalizar
      document.getElementById('proxima-pergunta').innerHTML = 
        '<button class="btn btn-success" onclick="finalizarEntrevista()">Finalizar e Ver Relatório →</button>';
      document.getElementById('proxima-pergunta').style.display = 'block';
    }
  }
});

function mostrarAprofundamento(aprofundamentos) {
  const ap = aprofundamentos[contadorAprofundamentos];
  document.getElementById('pergunta-aprofundamento').textContent = ap.pergunta;
  document.getElementById('aprofundamento-box').style.display = 'block';
  
  document.getElementById('form-aprofundamento').onsubmit = async (e) => {
    e.preventDefault();
    const resposta = document.getElementById('resposta-aprofundamento').value;
    
    // Salvar e passar para próximo aprofundamento ou próxima pergunta
    contadorAprofundamentos++;
    if (contadorAprofundamentos < aprofundamentos.length) {
      document.getElementById('resposta-aprofundamento').value = '';
      mostrarAprofundamento(aprofundamentos);
    } else {
      // Fim dos aprofundamentos
      document.getElementById('aprofundamento-box').style.display = 'none';
      if (perguntaAtual < totalPerguntas) {
        document.getElementById('proxima-pergunta').style.display = 'block';
      } else {
        document.getElementById('proxima-pergunta').innerHTML = 
          '<button class="btn btn-success" onclick="finalizarEntrevista()">Finalizar e Ver Relatório →</button>';
        document.getElementById('proxima-pergunta').style.display = 'block';
      }
    }
  };
}

async function proximaPergunta() {
  perguntaAtual++;
  const res = await fetch(`/entrevista/${entrevistaId}/pergunta/${perguntaAtual}`);
  const data = await res.json();
  
  // Resetar UI
  document.getElementById('form-resposta').style.display = 'block';
  document.getElementById('feedback-box').style.display = 'none';
  document.getElementById('aprofundamento-box').style.display = 'none';
  document.getElementById('proxima-pergunta').style.display = 'none';
  document.getElementById('resposta-input').value = '';
  
  // Atualizar conteúdo
  document.getElementById('pergunta-titulo').textContent = data.pergunta_principal;
  document.getElementById('progresso-texto').textContent = `Pergunta ${perguntaAtual} de ${totalPerguntas}`;
  document.getElementById('barra-preenchimento').style.width = `${(perguntaAtual / totalPerguntas) * 100}%`;
}

async function finalizarEntrevista() {
  const res = await fetch(`/entrevista/${entrevistaId}/finalizar`, { method: 'POST' });
  window.location.href = `/entrevista/${entrevistaId}/relatorio`;
}
</script>
```

---

### 3️⃣ `entrevista_relatorio.html`

```html
<div class="entrevista-container">
  <div class="relatorio-header">
    <h1>Relatório de Entrevista</h1>
    <div class="score-geral">
      <span class="numero" id="score-geral">7.5</span>
      <span class="texto">/10</span>
    </div>
  </div>
  
  <div class="resumo">
    <div class="coluna">
      <h3>✅ Pontos Fortes</h3>
      <ul id="pontos-fortes"></ul>
    </div>
    <div class="coluna">
      <h3>⚠️ Pontos a Melhorar</h3>
      <ul id="pontos-fracos"></ul>
    </div>
    <div class="coluna">
      <h3>💡 Recomendações</h3>
      <ul id="recomendacoes"></ul>
    </div>
  </div>
  
  <div class="perguntas-detalhes">
    <h2>Detalhes das Perguntas</h2>
    <div id="perguntas-container"></div>
  </div>
  
  <div class="botoes-finais">
    <a href="/entrevista/exportar-pdf?id=<entrevista_id>" class="btn btn-primary">📄 Exportar em PDF</a>
    <a href="/entrevista" class="btn btn-secondary">Nova Entrevista</a>
  </div>
</div>

<style>
.relatorio-header { text-align: center; margin-bottom: 40px; }
.score-geral { font-size: 48px; font-weight: bold; color: #007bff; }
.resumo { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-bottom: 40px; }
.coluna { background: #f9f9f9; padding: 15px; border-radius: 8px; }
.pergunta-acordeao { border: 1px solid #ddd; margin-bottom: 10px; border-radius: 8px; }
.pergunta-header { padding: 15px; background: #f0f0f0; cursor: pointer; }
.pergunta-conteudo { padding: 15px; display: none; }
.botoes-finais { text-align: center; margin-top: 40px; }
</style>

<script>
// Carrega relatório da API e popula HTML
async function carregarRelatorio() {
  const entrevistaId = new URLSearchParams(window.location.search).get('id');
  const res = await fetch(`/entrevista/${entrevistaId}`);
  const data = await res.json();
  
  const relatorio = data.relatorio_final;
  
  // Popula resumo
  document.getElementById('score-geral').textContent = relatorio.score_geral.toFixed(1);
  document.getElementById('pontos-fortes').innerHTML = 
    relatorio.pontos_fortes.map(p => `<li>${p}</li>`).join('');
  document.getElementById('pontos-fracos').innerHTML = 
    relatorio.pontos_fracos.map(p => `<li>${p}</li>`).join('');
  document.getElementById('recomendacoes').innerHTML = 
    relatorio.recomendacoes.map(r => `<li>${r}</li>`).join('');
  
  // Popula perguntas em acordeão
  const container = document.getElementById('perguntas-container');
  data.perguntas.forEach((p, i) => {
    const div = document.createElement('div');
    div.className = 'pergunta-acordeao';
    div.innerHTML = `
      <div class="pergunta-header" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none'">
        <strong>Pergunta ${i + 1}:</strong> ${p.pergunta_principal}
        <span style="float:right;">Score: ${p.avaliacao_resposta.score}/10</span>
      </div>
      <div class="pergunta-conteudo">
        <p><strong>Sua Resposta:</strong></p>
        <p>${p.resposta_usuario}</p>
        <p><strong>Feedback:</strong></p>
        <p>${p.avaliacao_resposta.feedback}</p>
        ${p.perguntas_aprofundamento.length > 0 ? `
          <details>
            <summary>Aprofundamentos</summary>
            ${p.perguntas_aprofundamento.map(ap => `
              <div style="margin-top: 10px; padding-left: 15px; border-left: 3px solid #ddd;">
                <p><strong>Pergunta:</strong> ${ap.pergunta}</p>
                <p><strong>Resposta:</strong> ${ap.resposta}</p>
                <p><strong>Feedback:</strong> ${ap.feedback}</p>
              </div>
            `).join('')}
          </details>
        ` : ''}
      </div>
    `;
    container.appendChild(div);
  });
}

carregarRelatorio();
</script>
```

---

## 🤖 Prompts de IA (Groq)

### 1. Gerar Plano de Entrevista

```
Você é um especialista em recrutamento e entrevistas técnicas.

Analise o currículo e a descrição da vaga fornecidos e gere um plano de entrevista.

CURRÍCULO:
{curriculo_text}

VAGA:
{vaga_descricao}

Retorne um JSON com:
{
  "numero_perguntas": <5-8>,
  "topicos_principais": [<lista de 3-5 tópicos>],
  "estrategia_entrevista": "<parágrafo curto explicando a abordagem>",
  "questoes_principais": [<lista de numero_perguntas perguntas>]
}

Importante:
- As perguntas devem ser técnicas, comportamentais e sobre experiências específicas
- Considere os gaps entre CV e vaga
- Use linguagem clara e profissional
```

### 2. Avaliar Resposta & Decidir Aprofundamento

```
Você é um entrevistador técnico experiente avaliando a resposta de um candidato.

PERGUNTA: {pergunta}
RESPOSTA DO CANDIDATO: {resposta}
CONTEXTO DO CURRÍCULO: {contexto_cv_resumido}
DESCRIÇÃO DA VAGA: {vaga_resumida}

Avalie a resposta e retorne um JSON:
{
  "feedback": "<feedback construtivo, 2-3 frases>",
  "score": <1-10>,
  "deve_aprofundar": <true/false>,
  "perguntas_aprofundamento": [
    "<pergunta 1 de aprofundamento, se relevante>",
    "<pergunta 2 de aprofundamento, se relevante>"
  ]
}

Critérios:
- Score 1-3: Resposta incompleta ou incorreta
- Score 4-6: Resposta ok, mas com lacunas
- Score 7-8: Resposta boa e bem estruturada
- Score 9-10: Resposta excelente e detalhada

Aprofundamento: fazer apenas se a resposta merecesse (7+) ou se há pontos críticos não mencionados.
Máximo 2 perguntas de aprofundamento.
```

### 3. Gerar Relatório Final

```
Você é um especialista em recrutamento gerando um parecer final de entrevista.

CANDIDATO: {nome_candidato}
VAGA: {nome_vaga}
RESPOSTAS COLETADAS:
{todasRespostasJson}

Gere um relatório JSON:
{
  "score_geral": <média ponderada 1-10>,
  "parecer_final": "<1 parágrafo conclusivo>",
  "pontos_fortes": [<3-5 pontos>],
  "pontos_fracos": [<3-5 pontos>],
  "recomendacoes": [<3-5 recomendações para o candidato>],
  "recomendacao_gestor": "<contratável, reavaliável, ou não recomendado>"
}

Seja honesto e construtivo.
```

---

## 📦 Implementação - Checklist

### Backend (Models & Migrations)
- [ ] Criar `src/models/entrevista.py` com classes Entrevista e PerguntaEntrevista
- [ ] Gerar migração Alembic: `alembic revision --autogenerate`
- [ ] Aplicar migração: `alembic upgrade head`
- [ ] Adicionar relacionamentos em `src/models/user.py`

### Backend (Routes)
- [ ] Criar `src/routes/entrevista.py` com blueprint
- [ ] Implementar endpoints em routes/entrevista.py:
  - [ ] `POST /entrevista/gerar-plano`
  - [ ] `GET /entrevista/<id>`
  - [ ] `GET /entrevista/<id>/pergunta/<numero>`
  - [ ] `POST /entrevista/<id>/responder`
  - [ ] `POST /entrevista/<id>/finalizar`
  - [ ] `GET /entrevista/<id>/relatorio`
  - [ ] `GET /entrevista/<id>/exportar-pdf`

### Backend (Services)
- [ ] Adicionar funções em `src/services/model.py`:
  - [ ] `gerar_plano_entrevista(curriculo_text, vaga_descricao)`
  - [ ] `avaliar_resposta(pergunta, resposta, contexto)`
  - [ ] `gerar_relatorio_final(todas_respostas)`
- [ ] Estender `src/services/pdf.py` para geração de PDF de relatório

### Frontend (Templates)
- [ ] Criar `src/templates/entrevista_planejamento.html`
- [ ] Criar `src/templates/entrevista_execucao.html`
- [ ] Criar `src/templates/entrevista_relatorio.html`

### Frontend (Assets)
- [ ] Criar `src/static/entrevista.css`
- [ ] Criar `src/static/entrevista.js`

### Integration
- [ ] Registrar blueprint em `src/app.py`
- [ ] Importar models em `src/app.py`
- [ ] Testar fluxo completo
- [ ] Atualizar README com nova funcionalidade

---

## 🔐 Segurança & Validação

- ✅ `@login_required` em todos endpoints
- ✅ Validação de `user_id` (usuário só vê suas entrevistas)
- ✅ Detecção de prompt injection (usar `has_prompt_injection()` existente)
- ✅ Rate limiting com `@limiter.limit()`
- ✅ Upload: validar tipo arquivo + tamanho (max 5MB)
- ✅ Sanitização de inputs (usar `sanitize_text()` existente)
- ✅ Máximo chars por resposta (ex: 2000)

---

## 📊 Estrutura de Dados (JSON)

### `entrevista.plano_entrevista`
```json
{
  "topicos": ["Python avançado", "Liderança técnica", "DevOps"],
  "estrategia": "Começar com questões técnicas...",
  "questoes_principais": ["Qual sua experiência?", ...]
}
```

### `pergunta_entrevista.avaliacao_resposta`
```json
{
  "feedback": "Excelente resposta, cobriu...",
  "score": 8,
  "aprofundar": true
}
```

### `pergunta_entrevista.perguntas_aprofundamento`
```json
[
  {
    "pergunta": "Qual foi o maior desafio?",
    "resposta": "...",
    "feedback": "..."
  },
  {
    "pergunta": "Como você resolveu?",
    "resposta": "...",
    "feedback": "..."
  }
]
```

### `entrevista.relatorio_final`
```json
{
  "score_geral": 7.5,
  "parecer_final": "Candidato com bom potencial...",
  "pontos_fortes": ["Experiência sólida", "Boa comunicação"],
  "pontos_fracos": ["Falta DevOps"],
  "recomendacoes": ["Cursos em Docker", "Prática com Kubernetes"],
  "recomendacao_gestor": "Contratável"
}
```

---

## 🚀 Roadmap Sugerido

**Sprint 1: Backend + DB**
- Modelos + Migrations
- Endpoints básicos
- Integração IA (Groq)

**Sprint 2: Frontend UI**
- Templates + CSS
- JavaScript interativo
- Testes manuais

**Sprint 3: Polimento**
- PDF export
- Tratamento erros
- UX melhorias
- Testes finais

---

## 📝 Notas

- Chat existente é **preservado** e pode ser renomeado
- Reutilizar: `services/pdf.py`, `services/parser.py`, `services/model.py`, autenticação
- Máximo **2 aprofundamentos** por pergunta (como solicitado)
- PDF usa gerador existente (estender classe)
- Rate limit: 20 req/min, 100/hora (padrão do projeto)

