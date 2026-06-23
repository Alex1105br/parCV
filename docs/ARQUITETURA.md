# Arquitetura — parCV

Este documento descreve como as peças do sistema se conectam. Para instruções de instalação e execução, veja o [README](../README.md). Para a referência completa de endpoints, veja [API.md](./API.md).

## Visão geral

parCV é uma aplicação **Flask monolítica** (não há separação front/back em serviços distintos): o mesmo processo serve páginas HTML renderizadas no servidor (Jinja2), endpoints JSON consumidos via `fetch()` pelo JavaScript das páginas, e respostas em streaming (SSE) para o chat. O banco é PostgreSQL via SQLAlchemy, com Alembic/Flask-Migrate para versionar o schema. A inteligência artificial (análise de currículo, otimização, chat, simulação de entrevista) é delegada a um provedor de LLM externo — Groq (nuvem) ou Ollama (local) — nunca executada localmente.

```
Browser
  │  HTML (Jinja2) + fetch() + EventSource (SSE)
  ▼
Flask app (src/app.py)
  │
  ├── Blueprints (src/routes/*.py) ── lógica de request/response, validação, orquestração
  │
  ├── Services (src/services/*.py) ── regras de negócio puras: prompts, parsing, PDF, chamadas LLM
  │
  └── Models (src/models/*.py) ── SQLAlchemy ORM
  ▼
PostgreSQL                              LLM externo (Groq API / Ollama local)
```

## Camadas e responsabilidades

### `src/app.py` — Application Factory

`create_app()` monta a aplicação Flask: carrega config, inicializa extensões (`SQLAlchemy`, `Flask-Mail`, `Flask-Migrate`, `Flask-Limiter`), registra os 7 blueprints e define:

- **`@app.before_request` / `@app.after_request`**: geram um `request_id` (UUID curto) por requisição, guardado em `g.request_id` e num `ContextVar` (`request_id_var`), usado pelo `StructuredFormatter` do logging para correlacionar logs da mesma requisição. O `after_request` também loga duração e status de cada chamada, e devolve o `request_id` no header `X-Request-Id`.
- **`@app.errorhandler(429)`**: resposta JSON padronizada quando o rate limiter bloqueia uma requisição.
- **Registro dos models** (`import src.models.X # noqa: F401`): necessário para que o SQLAlchemy/Alembic "veja" as tabelas mesmo sem uso direto da classe nesse arquivo — é um padrão comum em projetos Flask-SQLAlchemy, não código morto.

A instância de `Limiter` e `Mail` são globais no módulo (`limiter`, `mail`), inicializadas dentro de `create_app()` via `.init_app(app)` — por isso outros módulos importam `from src.app import limiter` para aplicar rate limit nas rotas.

### `src/config.py` — Configuração

Lê variáveis de ambiente (via `environs`) uma única vez, na importação do módulo. Decisão notável: se `LLM_BACKEND=groq` e `GROQ_API_KEY` estiver vazia, o módulo **levanta uma exceção na importação** — a aplicação se recusa a subir em vez de falhar silenciosamente depois, na primeira chamada à IA.

### `src/routes/` — Blueprints (camada HTTP)

Cada arquivo é um Blueprint Flask, registrado em `app.py`. Responsabilidade: receber a requisição, validar entrada, checar autenticação/autorização, orquestrar chamadas a services e models, devolver a resposta. **Não deveriam conter lógica de negócio pesada** (prompts de IA, parsing de PDF) — isso fica em `services/`.

| Blueprint | Prefixo de rota | Responsabilidade |
|---|---|---|
| `auth.py` | `/` | login, registro, logout, recuperação de senha |
| `home.py` | `/` | página inicial (apenas redireciona/renderiza) |
| `analisar.py` | `/` | análise ATS, otimização de currículo, histórico, export PDF |
| `chat.py` | `/` | chat de carreira com streaming SSE, sessões de conversa |
| `entrevista.py` | `/entrevista` | simulação de entrevista (plano → execução → relatório) |
| `curriculo.py` | `/curriculos` | CRUD de currículos salvos, visualização/download de PDF, paleta de cores |
| `conta.py` | `/` | dados de perfil do usuário, alteração de senha, exclusão de conta |

Toda rota que exige usuário logado usa o decorator `@login_required` (definido em `src/utils.py`), que verifica `"user_id" in session` e redireciona para `/login` caso contrário.

### `src/services/` — Regras de negócio

Funções puras (ou quase puras — algumas fazem I/O de rede para a LLM), sem acesso direto à `session`/`request` do Flask. Pensadas para serem testáveis isoladamente.

| Módulo | Responsabilidade |
|---|---|
| `model.py` | Abstrai os dois backends de LLM (Groq/Ollama) atrás de uma interface única: `call_model()` (síncrono) e `stream_resposta()` (streaming SSE). Também contém os prompts e o parsing de resposta específicos da simulação de entrevista (`gerar_plano_entrevista`, `avaliar_resposta`, `gerar_relatorio_final`). |
| `prompts.py` | Templates de prompt para análise ATS e otimização de currículo. Cada prompt embute o conteúdo do usuário em tags `<curriculo>`/`<vaga>` com instrução explícita para a IA tratá-las como dados, não comandos. |
| `parser.py` | Extrai JSON de respostas de LLM (que às vezes vêm com texto extra ou cercas ` ```json ` ), com fallback por regex se o JSON vier malformado. |
| `pdf.py` | Gera os PDFs (currículo otimizado em 3 templates visuais; relatório de entrevista) usando ReportLab. Faz parsing do texto com marcadores (`---SECAO:---` etc.) em blocos tipados antes de desenhar. |
| `curriculo.py` | Geração automática de label via LLM, garantia de unicidade de label por usuário, gerenciamento da paleta de cores (round-robin automático + seleção manual), deduplicação por hash SHA-256 do texto. |
| `conversor_pdf.py` | Converte currículos enviados em `.docx` ou `.txt` para PDF usando ReportLab, preservando a estrutura visual do documento. PDFs são armazenados diretamente sem conversão. |
| `conta.py` | Atualização de dados de perfil (nome, telefone, profissão), alteração de senha com verificação da senha atual, exclusão de conta e todos os dados relacionados. |

### `src/models/` — Persistência (SQLAlchemy)

Ver [schema completo](#schema-do-banco-de-dados) abaixo. Todos os IDs são UUID v4 em string (`db.String(36)`), gerados em Python (`default=lambda: str(uuid.uuid4())`), não pelo banco.

### `src/utils.py` — Helpers transversais

Concentra três famílias de funções usadas por múltiplas rotas:

- **Auth**: `login_required` (decorator).
- **Arquivos**: `allowed_file`, `carregar_arquivo` (extrai texto de .txt/.pdf/.docx — PDF via binário externo `pdftotext`, DOCX via `python-docx`), `get_file_size`.
- **Segurança**: `sanitize_text` (remove tags HTML e caracteres de controle, limita tamanho) e `has_prompt_injection` (ver seção dedicada abaixo).

## Defesa contra prompt injection

Como o sistema envia texto fornecido pelo usuário (currículo, descrição de vaga, mensagens de chat, respostas de entrevista) para uma LLM, qualquer um desses campos é um vetor potencial de *prompt injection* — texto que tenta instruir o modelo a ignorar seu prompt de sistema original.

A defesa tem duas camadas:

1. **Filtro determinístico** (`has_prompt_injection()` em `src/utils.py`): regex que procura padrões característicos ("ignore as instruções", "esqueça tudo", "you are now", "pretend to be", tokens de chat como `[INST]`/`<|system|>`, etc.) em português e inglês. Se encontrado, a rota rejeita a requisição com **HTTP 422** *antes* de gastar uma chamada à API da LLM. Está plugado em todos os pontos de entrada de texto livre: `/analisar`, `/otimizar`, `/otimizar/pdf`, `/entrevista/gerar-plano`, `/entrevista/<id>/responder`, `/chat`.
2. **Instrução defensiva no próprio prompt** (`prompts.py`, `model.py`): o conteúdo do usuário é embutido em tags (`<curriculo>`, `<vaga>`) com instrução explícita à IA para tratá-las apenas como dados.

O repositório inclui `prompt-injection.txt` como caso de teste manual dessa defesa — documentado em detalhe no [README](../README.md#teste-de-segurança-prompt-injection-prompt-injectiontxt).

## Fluxos principais

### Análise ATS (`POST /analisar`)

```
Browser envia arquivo + vaga
  → valida extensão/tamanho (utils.allowed_file, get_file_size)
  → extrai texto (utils.carregar_arquivo: pdftotext / python-docx / leitura direta)
  → sanitiza e checa prompt injection
  → salva/recupera Curriculo por hash SHA-256 (services.curriculo.obter_ou_criar_curriculo)
  → monta prompt (services.prompts.build_prompt_ats)
  → chama LLM (services.model.call_model)
  → extrai JSON da resposta (services.parser.extrair_json)
  → persiste em Analise (models.analise)
  → devolve JSON ao browser
```

### Chat (`POST /chat`) — streaming

Diferente das outras rotas, usa **Server-Sent Events**: a rota devolve uma `Response` cujo corpo é um generator (`generate()`), que vai fazendo `yield` de cada token conforme a LLM responde (`services.model.stream_resposta`). Isso permite que o frontend mostre a resposta sendo "digitada" em tempo real, em vez de esperar a resposta completa.

Detalhe de implementação relevante: como o generator pode continuar rodando depois que a função da rota já retornou (Flask consome o generator de forma lazy), o código salva o histórico da conversa no banco dentro de um bloco `finally`, usando `app.app_context()` explicitamente — necessário porque esse trecho roda fora do contexto de requisição original.

### Simulação de entrevista

Fluxo em 3 etapas, cada uma uma chamada separada à IA:

1. **`POST /entrevista/gerar-plano`** — currículo + vaga → IA gera 10 perguntas (6 hard skills + 4 soft skills) → cria `Entrevista` + 10 `PerguntaEntrevista`.
2. **`POST /entrevista/<id>/responder`** (uma vez por pergunta) — resposta do usuário → IA avalia (score 0-10 + feedback) → salva em `PerguntaEntrevista.avaliacao_resposta`.
3. **`POST /entrevista/<id>/finalizar`** — só permitido se todas as perguntas foram respondidas → IA gera relatório executivo final (separando hard/soft skills) → salva em `Entrevista.relatorio_final`.

O relatório final pode ser exportado em PDF via `GET /entrevista/<id>/exportar-pdf` (`services.pdf.gerar_pdf_relatorio_entrevista`).

### Gestão de currículos (`/curriculos`)

Currículos são persistidos na tabela `curriculo` com deduplicação automática por hash SHA-256 do texto extraído. Ao fazer upload de um novo currículo em qualquer tela (análise ou entrevista), o sistema verifica se um currículo com o mesmo conteúdo já existe para aquele usuário — se sim, reutiliza o registro existente em vez de criar um duplicado.

O arquivo PDF original (ou a versão convertida, para DOCX/TXT) é armazenado na coluna `arquivo_pdf` como `LargeBinary`, permitindo visualização e download fiel ao arquivo enviado.

## Schema do banco de dados

```
users
 ├─< analise (user_id)
 ├─< otimizacao (user_id)
 ├─< chat_session (user_id)
 ├─< entrevista (user_id)
 └─< curriculo (user_id)

analise
 ├─< otimizacao (analise_id, opcional)
 └─> curriculo (curriculo_id, opcional)

entrevista
 ├─< pergunta_entrevista (entrevista_id, cascade delete)
 └─> curriculo (curriculo_id, opcional)
```

| Tabela | Campos principais | Observações |
|---|---|---|
| `users` | `name`, `email` (único), `password` (hash), `reset_token`, `reset_token_expires_at`, `telefone`, `profissao`, `proximo_indice_cor` | Senha com `werkzeug.security.generate_password_hash`. Token de reset expira em 1h. `proximo_indice_cor` é um contador crescente para distribuição round-robin automática das cores de label dos currículos. |
| `curriculo` | `user_id` (FK), `label` (único por usuário), `cor`, `hash_conteudo` (SHA-256), `texto`, `arquivo_pdf` (LargeBinary), `arquivo_nome`, `arquivo_mimetype` | Paleta de 30 cores fixas. Índice composto `(user_id, hash_conteudo)` para deduplicação eficiente. Constraint única `(user_id, label)`. |
| `analise` | `score_total`, `criterios` (JSON), `pontos_fortes/fracos` (JSON), `sugestoes` (JSON), `palavras_chave_faltando` (JSON), `certificados_sugeridos` (JSON), `texto_original`, `vaga`, `titulo`, `curriculo_id` (FK opcional) | Resultado de uma análise ATS. `titulo` gerado automaticamente pela LLM. |
| `otimizacao` | `curriculo_original`, `curriculo_otimizado`, `melhorias` (JSON), `analise_id` (FK opcional) | Resultado de uma otimização de currículo. |
| `chat_session` | `titulo`, `titulo_gerado` (bool), `mensagens` (JSON — lista de `{role, content}`), `fixado` (bool), `fixado_em` (timestamp, null se não-fixada) | Uma sessão = uma conversa do chat. Título gerado automaticamente pela IA na primeira mensagem. A lista de conversas fixadas é ordenada por `fixado_em` (não por `atualizado_em`), para que enviar mensagens não mude a posição de uma conversa já fixada. |
| `entrevista` | `curriculo_arquivo`, `vaga_descricao`, `numero_perguntas`, `plano_entrevista` (JSON), `status` (`em_planejamento`/`em_andamento`/`concluida`), `relatorio_final` (JSON), `titulo`, `curriculo_id` (FK opcional) | `titulo` gerado automaticamente pela LLM. |
| `pergunta_entrevista` | `entrevista_id` (FK), `numero_sequencial`, `pergunta_principal`, `resposta_usuario`, `avaliacao_resposta` (JSON) | Perguntas 1-6 = hard skills, 7-10 = soft skills (convenção fixada no código, não numa coluna). |

Todas as tabelas usam campos `JSON` nativos do Postgres para estruturas semi-tabulares (listas de strings, dicts de critérios) — escolha que evita tabelas auxiliares para dados que não precisam de query relacional própria.

## Logging estruturado

`src/logging_config.py` define um `StructuredFormatter` que emite cada log como uma linha JSON (`ts`, `level`, `request_id`, `msg`, mais quaisquer campos `extra={...}` passados na chamada de log). Saída vai simultaneamente para stdout e para `logs/parcv.log` (rotação em 10 MB, 5 backups). O `request_id` é propagado via `ContextVar`, então logs de chamadas internas (ex: dentro de `services/model.py`) ficam automaticamente correlacionados ao log da requisição HTTP que os originou, sem precisar passar o ID manualmente em cada função.

## Decisões de design que vale registrar

- **Sem camada de "service objects" para auth/CRUD simples**: rotas como login/registro acessam o model diretamente. A separação rota/service só existe onde há lógica de negócio não-trivial (prompts de IA, parsing, geração de PDF, gestão de currículos).
- **IDs UUID gerados em Python, não pelo banco**: permite ter o ID disponível antes do `commit()` (útil em `entrevista.py`, que usa `db.session.flush()` para obter o ID da `Entrevista` antes de criar as `PerguntaEntrevista` filhas).
- **Rate limiting por rota, não global**: `default_limits=[]` no `Limiter` — cada rota sensível (chamadas à IA, principalmente) declara seu próprio limite via `@limiter.limit(...)`, em vez de um limite genérico para toda a aplicação.
- **`db_init.py` como alternativa a migrations em alguns ambientes**: roda `db.create_all()` (idempotente) e aplica `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` para colunas adicionadas depois da criação inicial — pensado para ambientes (ex. Supabase) onde rodar `alembic upgrade head` é menos direto que em um Postgres próprio. As migrations Alembic em `migrations/versions/` continuam sendo a fonte de verdade do schema.
- **Armazenamento do PDF original no banco**: a coluna `arquivo_pdf` em `curriculo` armazena o binário diretamente no Postgres (`LargeBinary`) em vez de em disco, simplificando o deploy (sem dependência de volume externo) ao custo de maior tamanho de banco — trade-off aceitável para um MVP.
- **Deduplicação de currículos por hash de conteúdo**: currículos com o mesmo texto (independente de nome de arquivo ou data) geram o mesmo SHA-256 e são compartilhados entre análises/entrevistas, evitando duplicatas e reduzindo consumo de armazenamento.
