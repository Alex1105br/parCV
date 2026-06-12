# 🔄 Diagramas de Fluxo - Simulador de Entrevistas

## 1. Fluxo Geral da Aplicação

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SIMULADOR DE ENTREVISTAS                                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│  TELA 1:             │
│  PLANEJAMENTO        │
└──────────────────────┘
        │
        ├─ 1. Upload Currículo (PDF/DOC)
        ├─ 2. Descrição da Vaga (textarea)
        ├─ 3. Botão "Gerar Plano"
        │
        ↓
┌──────────────────────────────────────────┐
│  BACKEND: Análise (IA + Groq)            │
│  ├─ Extrai currículo (parser.py)        │
│  ├─ Envia currículo + vaga para IA      │
│  ├─ Recebe: N perguntas, tópicos        │
│  └─ Salva Entrevista (em_planejamento)  │
└──────────────────────────────────────────┘
        │
        ↓
┌──────────────────────────────────────────┐
│  Exibe Plano:                            │
│  "Vamos fazer 5 perguntas sobre..."      │
│  ├─ Tópico 1                            │
│  ├─ Tópico 2                            │
│  └─ Botão "Iniciar Entrevista"          │
└──────────────────────────────────────────┘
        │
        ↓
┌──────────────────────┐
│  TELA 2:             │
│  EXECUÇÃO            │
│  (POR PERGUNTA)      │
└──────────────────────┘
        │
        ├─ Pergunta 1 de 5
        │  ├─ Exibe pergunta principal
        │  ├─ Usuário responde
        │  │
        │  ↓
        │  ┌────────────────────────────────────┐
        │  │ IA Avalia:                         │
        │  │ ├─ Feedback                        │
        │  │ ├─ Score 1-10                      │
        │  │ └─ Deve aprofundar? (T/F)          │
        │  └────────────────────────────────────┘
        │  │
        │  ├─ [SIM] Faz até 2 aprofundamentos
        │  │   ├─ Aprofundamento 1
        │  │   └─ Aprofundamento 2
        │  │
        │  └─ [NÃO] Próxima pergunta
        │
        ├─ Pergunta 2 de 5 (idem)
        ├─ Pergunta 3 de 5 (idem)
        ├─ Pergunta 4 de 5 (idem)
        └─ Pergunta 5 de 5 (idem)
        │
        ↓
┌──────────────────────────────────────────┐
│  TELA 3:                                 │
│  RELATÓRIO                               │
└──────────────────────────────────────────┘
        │
        ├─ Score Geral: 7.5/10
        ├─ Pontos Fortes (3-5 itens)
        ├─ Pontos Fracos (3-5 itens)
        ├─ Recomendações (3-5 itens)
        ├─ Todas perguntas + respostas (acordeão)
        │
        └─ Botões:
           ├─ "Exportar PDF" → Download
           └─ "Nova Entrevista" → Volta para Tela 1
```

---

## 2. Fluxo Detalhado: Tela de Execução

```
┌─ PERGUNTA PRINCIPAL #N ─────────────────────────────┐
│                                                      │
│  Qual é sua experiência com Python?                 │
│  [TEXTAREA PARA RESPOSTA]                           │
│  [BOTÃO: Enviar Resposta]                           │
│                                                      │
└──────────────────────────────────────────────────────┘
         │
         ├─ Usuário escreve resposta
         ├─ Clica "Enviar Resposta"
         │
         ↓
    [REQUISIÇÃO POST]
    /entrevista/<id>/responder
    {
      "numero_sequencial": 1,
      "resposta": "...",
      "tipo": "principal"
    }
         │
         ↓
    [IA AVALIA]
    • Feedback construtivo
    • Score (1-10)
    • Decide: aprofundar? (algoritmo)
         │
         ↓
┌─ FEEDBACK EXIBIDO ──────────────────────────────────┐
│                                                      │
│  Feedback: "Boa resposta, você mencionou..."        │
│  Score: 8/10                                         │
│                                                      │
│  [SE VAI APROFUNDAR...]                            │
│                                                      │
└──────────────────────────────────────────────────────┘
         │
         ├─ [SIM] Vai Aprofundar
         │   │
         │   ↓
         │  ┌─ APROFUNDAMENTO #1 ───────────────────┐
         │  │                                         │
         │  │  Qual foi o maior desafio que          │
         │  │  você enfrentou com concorrência?      │
         │  │  [TEXTAREA PARA RESPOSTA]              │
         │  │  [BOTÃO: Responder]                    │
         │  │                                         │
         │  └─────────────────────────────────────────┘
         │   │
         │   ├─ Usuário responde
         │   ├─ IA avalia
         │   │
         │   ↓
         │  ┌─ APROFUNDAMENTO #2 ───────────────────┐
         │  │ (SE HOUVER)                            │
         │  │                                         │
         │  │  Como você resolveu esse desafio?      │
         │  │  [TEXTAREA PARA RESPOSTA]              │
         │  │  [BOTÃO: Responder]                    │
         │  │                                         │
         │  └─────────────────────────────────────────┘
         │   │
         │   └─ [FIM APROFUNDAMENTOS]
         │
         └─ [NÃO] Vai para próxima pergunta
         │
         ↓
    [DECISÃO] Há mais perguntas?
         │
         ├─ SIM: Próxima pergunta
         │   └─ Volta ao topo (PERGUNTA PRINCIPAL #N+1)
         │
         └─ NÃO: Última pergunta
             └─ Botão "Finalizar e Ver Relatório"
                 │
                 ↓
            POST /entrevista/<id>/finalizar
             │
             ↓
         IA GERA RELATÓRIO
         • Score geral
         • Pontos fortes/fracos
         • Recomendações
             │
             ↓
         Redireciona para /entrevista/<id>/relatorio
```

---

## 3. Estrutura de Dados (Banco)

```
USERS (já existe)
    │
    └─── ENTREVISTA (novo)
            │
            └─── PERGUNTA_ENTREVISTA (novo, múltiplas)


┌─────────────────────────────────┐
│         USERS                   │
├─────────────────────────────────┤
│ id (PK)                         │
│ name                            │
│ email                           │
│ password                        │
│ criado_em                       │
│                                 │
│ relationships:                  │
│ ├─ analises (1:N)              │
│ ├─ otimizacoes (1:N)           │
│ ├─ chat_sessions (1:N)         │
│ └─ entrevistas (1:N) [NOVO]    │
└─────────────────────────────────┘
         │ (user_id)
         │ (1:N)
         ↓
┌─────────────────────────────────────────────┐
│         ENTREVISTA (NOVO)                   │
├─────────────────────────────────────────────┤
│ id (PK, UUID)                              │
│ user_id (FK)                               │
│ curriculo_arquivo (String)                 │
│ vaga_descricao (Text)                      │
│ numero_perguntas (Integer)                 │
│ plano_entrevista (JSON)                    │
│ status (Enum)                              │
│ criado_em (DateTime)                       │
│ atualizado_em (DateTime)                   │
│ finalizado_em (DateTime, nullable)         │
│ relatorio_final (JSON, nullable)           │
│                                             │
│ relationships:                             │
│ └─ perguntas (1:N)                        │
└─────────────────────────────────────────────┘
         │ (entrevista_id)
         │ (1:N)
         ↓
┌───────────────────────────────────────────────┐
│    PERGUNTA_ENTREVISTA (NOVO, múltiplas)     │
├───────────────────────────────────────────────┤
│ id (PK, UUID)                                │
│ entrevista_id (FK)                           │
│ numero_sequencial (Integer, 1..N)            │
│ pergunta_principal (Text)                    │
│ resposta_usuario (Text, nullable)            │
│ avaliacao_resposta (JSON)                    │
│   ├─ feedback (String)                      │
│   ├─ score (Integer, 1-10)                  │
│   └─ aprofundar (Boolean)                   │
│ perguntas_aprofundamento (JSON, nullable)   │
│   ├─ [0]                                    │
│   │   ├─ pergunta (String)                  │
│   │   ├─ resposta (String, nullable)        │
│   │   └─ feedback (String, nullable)        │
│   └─ [1]                                    │
│       ├─ pergunta (String)                  │
│       ├─ resposta (String, nullable)        │
│       └─ feedback (String, nullable)        │
│ criado_em (DateTime)                        │
│ respondido_em (DateTime, nullable)          │
└───────────────────────────────────────────────┘
```

---

## 4. Fluxo de Estados: Entrevista

```
┌─────────────────────┐
│  CRIAÇÃO            │
│  (novo registro)    │
└─────────────────────┘
        │
        ↓
┌──────────────────────────────────┐
│  STATUS: em_planejamento         │
├──────────────────────────────────┤
│ • Usuário vê plano               │
│ • Pode iniciar entrevista        │
│ • Sem perguntas respondidas      │
│                                  │
│ [Ações possíveis]                │
│ └─ Clicar "Iniciar"              │
└──────────────────────────────────┘
        │
        ↓
┌──────────────────────────────────┐
│  STATUS: em_andamento            │
├──────────────────────────────────┤
│ • Usuário respondendo perguntas  │
│ • Pode parar/voltar?             │
│ • Perguntas sendo preenchidas    │
│                                  │
│ [Ações possíveis]                │
│ ├─ Responder próxima pergunta    │
│ └─ Finalizar (completa)          │
└──────────────────────────────────┘
        │
        ↓
┌──────────────────────────────────┐
│  STATUS: concluida               │
├──────────────────────────────────┤
│ • IA gerou relatório             │
│ • Usuário vê resumo + análise    │
│ • Pode exportar PDF              │
│ • Pode fazer nova entrevista     │
│                                  │
│ [Ações possíveis]                │
│ ├─ Exportar PDF                  │
│ └─ Nova entrevista               │
└──────────────────────────────────┘
```

---

## 5. Fluxo de Dados: Requisição/Resposta

### POST /entrevista/gerar-plano

```
[CLIENT]                              [SERVER]

┌─────────────────┐
│ Form-Data:      │
│ • curriculo     │ ─────────────────→ Recebe multipart/form-data
│   (PDF file)    │                     │
│ • vaga_desc     │                     ├─ Valida arquivo
│   (texto)       │                     ├─ Extrai texto (pdf → text)
└─────────────────┘                     ├─ Sanitiza vaga_descricao
                                        ├─ Verifica prompt injection
                                        ├─ Chama IA (Groq)
                                        │  ├─ Input: currículo + vaga
                                        │  └─ Output: plano JSON
                                        ├─ Cria registro Entrevista
                                        └─ Cria N registros PerguntaEntrevista
                                        │
                  ┌─────────────────────┴─────┐
                  │ Resposta JSON:              │
                  │ {                          │
                  │  "entrevista_id": "uuid"  │
                  │  "numero_perguntas": 5    │
                  │  "plano": {               │
                  │    "topicos": [...],      │
                  │    "estrategia": "...",   │
                  │    "questoes": [...]      │
                  │  }                        │
                  │ }                         │
                  └────────────────────→ [Exibe Plano]
```

### POST /entrevista/<id>/responder

```
[CLIENT]                              [SERVER]

┌──────────────────┐
│ JSON POST:       │
│ {                │
│  "numero_seq": 1 │ ────────────────→ Recebe resposta
│  "resposta": "..│                    │
│  "tipo": "prin" │                    ├─ Valida resposta (não vazia)
│ }                │                    ├─ Salva em DB
└──────────────────┘                    ├─ Chama IA
                                        │  ├─ Input: pergunta + resposta
                                        │  └─ Output: avaliação
                                        ├─ Salva avaliacao_resposta
                                        │
                                        ├─ [SE deve_aprofundar]
                                        │  └─ Gera 2 aprofundamentos
                                        │
                                        └─ Retorna feedback
                                        │
                  ┌──────────────────────┴──────┐
                  │ Resposta JSON:               │
                  │ {                           │
                  │  "salvo": true,             │
                  │  "feedback_ia": "...",      │
                  │  "score": 8,                │
                  │  "aprofundamentos": [       │
                  │    {                        │
                  │     "pergunta": "...",      │
                  │     "tipo": "aprofun_1"    │
                  │    }                        │
                  │  ]                          │
                  │ }                           │
                  └──────────────→ [Exibe Feedback + Aprofundamentos]
```

---

## 6. Hierarquia de Componentes Frontend

```
entrevista_planejamento.html
├─ .entrevista-container
│   ├─ form#form-planejamento
│   │   ├─ input[type=file] (currículo)
│   │   ├─ textarea (vaga)
│   │   └─ button[submit] (Gerar Plano)
│   │
│   └─ #resultado-plano (hidden)
│       ├─ .alert.alert-info
│       │   ├─ h3 (✅ Plano Gerado!)
│       │   ├─ p (Vamos fazer X perguntas)
│       │   └─ ul#topicos-list
│       │
│       └─ a.btn (Iniciar Entrevista)

entrevista_execucao.html
├─ .entrevista-container
│   ├─ .progresso-bar
│   │   ├─ #progresso-texto
│   │   └─ .barra > .preenchimento
│   │
│   ├─ .pergunta-card
│   │   ├─ h2#pergunta-titulo
│   │   └─ form#form-resposta
│   │       ├─ textarea#resposta-input
│   │       └─ button[submit]
│   │
│   ├─ #feedback-box (hidden)
│   │   ├─ h3
│   │   ├─ p#feedback-texto
│   │   └─ .score
│   │
│   ├─ #aprofundamento-box (hidden)
│   │   ├─ h3
│   │   ├─ p#pergunta-aprofundamento
│   │   └─ form#form-aprofundamento
│   │       ├─ textarea#resposta-aprofundamento
│   │       └─ button[submit]
│   │
│   └─ #proxima-pergunta (hidden)
│       └─ button (Próxima Pergunta →)

entrevista_relatorio.html
├─ .entrevista-container
│   ├─ .relatorio-header
│   │   ├─ h1
│   │   └─ .score-geral
│   │
│   ├─ .resumo
│   │   ├─ .coluna (Pontos Fortes)
│   │   ├─ .coluna (Pontos Fracos)
│   │   └─ .coluna (Recomendações)
│   │
│   ├─ .perguntas-detalhes
│   │   ├─ h2
│   │   └─ #perguntas-container
│   │       └─ .pergunta-acordeao (×N)
│   │           ├─ .pergunta-header
│   │           └─ .pergunta-conteudo (hidden)
│   │               ├─ resposta
│   │               ├─ feedback
│   │               └─ details (aprofundamentos)
│   │
│   └─ .botoes-finais
│       ├─ a.btn (Exportar PDF)
│       └─ a.btn (Nova Entrevista)
```

---

## 7. Ciclo de Vida de uma Entrevista

```
TIMELINE:

T0: Usuário acessa /entrevista
    ├─ Vê form para upload
    
T1: Clica "Gerar Plano"
    ├─ POST /entrevista/gerar-plano
    ├─ IA análise (3-5 segundos)
    ├─ DB: INSERT Entrevista (status='em_planejamento')
    ├─ DB: INSERT 5 × PerguntaEntrevista
    
T2: Exibe plano
    ├─ "Vamos fazer 5 perguntas"
    
T3: Clica "Iniciar Entrevista"
    ├─ Muda status para 'em_andamento'
    ├─ Redireciona para /entrevista/<id>/executar
    
T4-T23: Pergunta 1-5 (Tela de execução)
    ├─ Usuário vê pergunta
    ├─ Escreve resposta
    ├─ Clica "Enviar"
    ├─ POST /entrevista/<id>/responder
    ├─ IA avalia (2-3 segundos)
    ├─ [SE aprofundar]
    │   ├─ Mostra aprofundamento 1
    │   ├─ Usuário responde
    │   ├─ IA avalia
    │   ├─ Mostra aprofundamento 2 (se houver)
    │   ├─ Usuário responde
    │   ├─ IA avalia
    ├─ Botão "Próxima Pergunta"
    
T24: Última pergunta respondida
    ├─ Botão "Finalizar Entrevista"
    
T25: Clica "Finalizar"
    ├─ POST /entrevista/<id>/finalizar
    ├─ IA gera relatório (3-5 segundos)
    ├─ DB: UPDATE Entrevista
    │   ├─ status = 'concluida'
    │   ├─ relatorio_final = {...}
    │   ├─ finalizado_em = NOW()
    ├─ Redireciona para /entrevista/<id>/relatorio
    
T26: Exibe relatório
    ├─ Score geral em destaque
    ├─ Pontos fortes/fracos/recomendações
    ├─ Cada pergunta em acordeão
    
T27+: Usuário pode:
    ├─ "Exportar PDF" → GET /entrevista/<id>/exportar-pdf
    │   ├─ Gera PDF (2-3 segundos)
    │   └─ Download arquivo
    └─ "Nova Entrevista" → /entrevista
        └─ Volta ao início
```

---

## 8. Estados do Frontend: Tela de Execução

```
[PERGUNTA_VISÍVEL]
├─ form visível
├─ feedback hidden
├─ aprofundamento hidden
└─ proxima_pergunta hidden

    ↓ [Usuário responde]

[FEEDBACK_VISÍVEL]
├─ form hidden
├─ feedback visível
├─ aprofundamento [SIM/NÃO]
└─ proxima_pergunta hidden

    ├─ [SIM] ↓
    │ [APROFUNDAMENTO_1_VISÍVEL]
    │ ├─ form visível
    │ ├─ feedback hidden
    │ └─ proxima_pergunta hidden
    │     ↓ [Usuário responde]
    │ [APROFUNDAMENTO_2_VISÍVEL] (se houver)
    │ ├─ form visível
    │ └─ proxima_pergunta hidden
    │     ↓ [Usuário responde]
    │ [PROXIMA_PERGUNTA_VISÍVEL]
    │
    └─ [NÃO] ↓
    [PROXIMA_PERGUNTA_VISÍVEL]
    ├─ proxima_pergunta visível
    ├─ form hidden
    └─ feedback hidden

        ├─ [Há mais perguntas]
        │   ├─ Botão "Próxima Pergunta →"
        │   └─ Volta para [PERGUNTA_VISÍVEL]
        │
        └─ [Última pergunta]
            ├─ Botão "Finalizar e Ver Relatório →"
            └─ POST /finalizar → Redireciona
```

---

## 9. Casos de Uso

### Caso 1: Entrevista com Aprofundamentos Completos

```
Pergunta 1 → Resposta Boa (score 8) → Aprofundamento 1 → Aprofundamento 2 
    → Feedback IA → Próxima Pergunta
```

### Caso 2: Entrevista sem Aprofundamentos

```
Pergunta 1 → Resposta Fraca (score 4) → Sem Aprofundamento 
    → Feedback IA → Próxima Pergunta
```

### Caso 3: Entrevista Interrompida (em_andamento)

```
Usuário para de responder → Entrevista fica em_andamento 
→ Pode voltar /entrevista/<id>/executar para continuar
(implementar recuperação de estado)
```

---

## 10. Integração com Componentes Existentes

```
NOVO:
├─ models/
│   └─ entrevista.py (novo arquivo)
├─ routes/
│   └─ entrevista.py (novo arquivo)
├─ templates/
│   ├─ entrevista_planejamento.html (novo)
│   ├─ entrevista_execucao.html (novo)
│   └─ entrevista_relatorio.html (novo)
├─ static/
│   ├─ entrevista.css (novo)
│   └─ entrevista.js (novo)
└─ ESPECIFICACAO_SIMULADOR_ENTREVISTA.md (este arquivo)

MODIFICAÇÕES EXISTENTES:
├─ app.py
│   ├─ import src.models.entrevista
│   └─ app.register_blueprint(entrevista_bp)
├─ models/
│   └─ user.py
│       └─ entrevistas = db.relationship(...)
├─ services/
│   ├─ model.py (estender com funções IA)
│   └─ pdf.py (estender com gerar_relatorio_pdf)
└─ migrations/
    └─ versions/ (novo arquivo migração)

REUTILIZAÇÃO:
├─ services/pdf.py ✅ (PDF export)
├─ services/parser.py ✅ (extração currículo)
├─ services/model.py ✅ (IA/Groq)
├─ utils.py ✅ (sanitize, upload, etc)
├─ Sistema autenticação ✅
├─ Rate limiting ✅
└─ Base template ✅
```

