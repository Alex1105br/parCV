# Referência da API — parCV

Esta referência foi extraída diretamente do código-fonte das rotas (`src/routes/`), não escrita de memória — cada endpoint listado aqui corresponde a uma rota Flask real no projeto. Para o panorama arquitetural, veja [ARQUITETURA.md](./ARQUITETURA.md).

## Convenções gerais

- **Autenticação**: a maioria das rotas exige sessão de usuário logado (cookie de sessão Flask, criado em `/login`). Rotas marcadas com 🔒 exigem login; sem o marcador, são abertas. Sem sessão válida, rotas 🔒 redirecionam para `/login` (rotas HTML) — não devolvem JSON 401, pois usam o decorator `@login_required` baseado em redirect.
- **Rate limiting**: rotas marcadas com ⏱ têm limite de requisições por IP (via `flask-limiter`). Ao estourar o limite, a resposta é `429 Too Many Requests` com corpo `{"error": "Muitas requisições. Aguarde antes de tentar novamente."}`.
- **Formato de erro padrão**: a maioria dos erros JSON segue `{"error": "mensagem"}` com o status HTTP apropriado.
- **Upload de arquivos**: limite de 5 MB (`MAX_UPLOAD_BYTES`), extensões aceitas: `.txt`, `.pdf`, `.docx`.

---

## Autenticação (`src/routes/auth.py`)

### `GET/POST /login`
Tela de login. `GET` renderiza o formulário (`login.html`). `POST` autentica.

**Body (form-urlencoded, no POST):** `email`, `password`

**Sucesso:** redirect para `/` (home), com `session["user_id"]` e `session["user_name"]` definidos.
**Erro:** re-renderiza `login.html` com `error` (campos vazios, email inválido, ou "Email ou senha incorretos").

### `GET/POST /register`
Cadastro de novo usuário.

**Body (form-urlencoded, no POST):** `name`, `email`, `password`, `confirm_password`

**Validações:** todos os campos obrigatórios; email com formato válido; senha com 8+ caracteres; senhas coincidem; email ainda não cadastrado.
**Sucesso:** cria `User` (senha com `generate_password_hash`), inicia sessão, redirect para `/`.

### `POST /logout`
Encerra a sessão (`session.clear()`). Redirect para `/login`.

### `GET/POST /esqueci-senha`
Solicitação de recuperação de senha.

**Body (form-urlencoded, no POST):** `email`

**Comportamento:** sempre retorna a mesma mensagem genérica ("Se esse email estiver cadastrado..."), independente do email existir ou não — evita enumeração de usuários. Se o email existir, gera um token (`secrets.token_urlsafe(32)`, válido por 1h) e envia por e-mail via SMTP (Flask-Mail). Se um token recente (gerado há menos de 1 minuto) já existir, reutiliza-o em vez de gerar outro — evita reenvio em cliques duplicados/refresh.

### `GET/POST /redefinir-senha/<token>`
Tela de redefinição de senha a partir do link recebido por e-mail.

**Body (form-urlencoded, no POST):** `password`, `confirm_password`

**Token inválido/expirado:** renderiza `reset_password.html` com `expired=True`.
**Sucesso:** atualiza a senha (hash), invalida o token, redirect para `/login?reset=ok`.

---

## Home (`src/routes/home.py`)

### `GET /` 🔒
Página inicial pós-login (`home.html`).

---

## Análise e otimização de currículo (`src/routes/analisar.py`)

### `GET/POST /analisar` 🔒 ⏱ `(5/min; 30/hora, só no POST)`
`GET` renderiza a tela (`analisar.html`). `POST` executa a análise ATS.

**Body (multipart/form-data, no POST):**
- `arquivo` (obrigatório) — currículo em .txt/.pdf/.docx
- `vaga` (opcional) — descrição da vaga, texto livre

**Validações:** arquivo presente e extensão permitida; tamanho ≤ 5 MB; conteúdo extraído e `vaga` passam por `has_prompt_injection()` (rejeita com 422 se detectado).

**Resposta 200 (JSON):**
```json
{
  "id": "uuid",
  "score_total": 0,
  "criterios": {"estrutura": 0, "clareza": 0, "experiencia": 0, "palavras_chave": 0, "skills": 0, "compatibilidade": 0},
  "pontos_fortes": ["..."],
  "pontos_fracos": ["..."],
  "sugestoes": ["..."],
  "palavras_chave_faltando": ["..."],
  "certificados_sugeridos": [{"nome": "", "plataforma": "", "url": ""}],
  "texto_original": "..."
}
```

**Erros:** `400` (sem arquivo / arquivo inválido / erro ao extrair texto), `413` (arquivo grande demais), `422` (prompt injection detectado), `500` (erro ao chamar a LLM). Mesmo em erro de persistência no banco, a análise é devolvida ao usuário (erro fica só logado).

### `GET /analises` 🔒
Lista paginada das análises do usuário logado.

**Query params:** `page` (default 1), `per_page` (default 20, máx 50)

**Resposta 200:** `{"analises": [{id, score_total, criado_em, vaga}], "total", "page", "pages"}`

### `GET /historico` 🔒
Página HTML de histórico (`historico.html`).

### `GET /historico/<analise_id>` 🔒
Página HTML de detalhe de uma análise (`historico_detalhe.html`).

### `GET /analises/<analise_id>` 🔒
Dados completos de uma análise específica (JSON), só se pertencer ao usuário logado.

**Erros:** `404` se não existir ou pertencer a outro usuário.

### `POST /otimizar` 🔒 ⏱ `(5/min; 30/hora)`
Reescreve o currículo otimizado para a vaga informada.

**Body (multipart/form-data):** `arquivo` (obrigatório), `vaga` (opcional) — mesmas validações de `/analisar`.

**Resposta 200:**
```json
{
  "id": "uuid",
  "curriculo_original": "...",
  "curriculo_otimizado": "... (com marcadores ---SECAO:--- etc.)",
  "melhorias": ["..."]
}
```
O texto otimizado também fica salvo em `session["curriculo_otimizado"]`, usado pelo `GET /otimizar/pdf` sem precisar reenviar o texto.

### `GET/POST /otimizar/pdf` 🔒 ⏱ `(10/min, só no POST)`
Gera o PDF do currículo otimizado.

- **`GET`**: usa o texto salvo em `session["curriculo_otimizado"]` (fluxo normal: usuário acabou de otimizar e clica em exportar). Query param `template` (`classico`|`moderno`|`executivo`, default `classico`).
- **`POST`**: aceita texto explícito no body (`texto`, form-urlencoded/multipart) — útil se o usuário editou o texto antes de exportar. Aceita também `foto` (jpg/png, ≤2 MB) para incluir no cabeçalho do PDF e `template`.

**Resposta 200:** arquivo PDF (`Content-Type: application/pdf`, `as_attachment=True`).
**Erros:** `400` (sem texto disponível), `422` (prompt injection no texto enviado via POST), `500` (erro na geração).

---

## Chat de carreira (`src/routes/chat.py`)

### `GET /chat` 🔒
Página do chat (`chat.html`), com listas de sessões fixadas e recentes do usuário.

### `POST /chat` 🔒 ⏱ `(20/min; 100/hora)`
Envia uma mensagem e recebe a resposta da IA via **Server-Sent Events** (streaming).

**Body (JSON):** `{"mensagem": "..."}`

**Resposta:** `Content-Type: text/event-stream`. Cada evento é uma linha `data: {...}\n\n`:
- `{"token": "..."}` — pedaço de texto da resposta (chega vários, conforme a IA gera)
- `{"done": true, "tempo": "0m 3s", "full_response": "...", "session_id": "uuid", "titulo": "..." (opcional, só na 1ª mensagem da sessão)}` — evento final
- `{"error": "..."}` — em caso de falha

**Header de resposta:** `X-Session-Id` com o ID da `ChatSession` usada/criada.
**Erros (JSON normal, não SSE):** `400` (mensagem vazia), `422` (prompt injection).

### `POST /upload` 🔒 ⏱ `(10/min)`
Envia um arquivo (currículo ou outro documento) para o chat, com mensagem opcional.

**Body (multipart/form-data):** `arquivo` (obrigatório), `mensagem` (opcional)

**Comportamento:** se `mensagem` for enviada (e não tiver prompt injection), o comportamento é igual ao `/chat` — devolve um stream SSE. Se não houver mensagem, devolve JSON normal confirmando o upload: `{"success": true, "filename", "chars", "session_id", "titulo"}`.

### `POST /limpar` 🔒
Limpa as mensagens da sessão de chat atual (mantém a sessão, zera o histórico).

### `POST /chat/nova` 🔒
Inicia uma nova sessão de chat. Se a sessão anterior estava vazia (sem mensagens reais e sem título), ela é deletada em vez de ficar acumulando sessões vazias.

### `GET /chat/sessoes` 🔒
Lista todas as sessões de chat do usuário, ordenadas por atualização mais recente.

**Resposta 200:** `[{"id", "titulo", "fixado", "atualizado_em"}]`

### `POST /chat/sessao/<sid>` 🔒
Troca a sessão de chat ativa. Filtra mensagens internas (system prompt, marcador de "documento carregado") antes de devolver ao frontend.

**Resposta 200:** `{"id", "titulo", "mensagens": [...]}` (visíveis ao usuário)
**Erros:** `404` se a sessão não existir ou não pertencer ao usuário.

### `PATCH /chat/sessao/<sid>/titulo` 🔒
Renomeia manualmente o título de uma sessão.

**Body (JSON):** `{"titulo": "..."}`

**Resposta 200:** `{"id", "titulo"}`
**Erros:** `400` (título vazio), `404`.

### `PATCH /chat/sessao/<sid>/fixar` 🔒
Alterna o estado "fixado" de uma sessão (pin/unpin na lista lateral do chat).

**Resposta 200:** `{"id", "fixado"}`
**Erros:** `404`.

### `DELETE /chat/sessao/<sid>` 🔒
Exclui uma sessão de chat permanentemente. Se for a sessão ativa, limpa `session["chat_sid"]`.

**Resposta 200:** `{"success": true}`
**Erros:** `404`.

---

## Simulação de entrevista (`src/routes/entrevista.py`, prefixo `/entrevista`)

### `GET /entrevista/` 🔒
Página de planejamento (`entrevista_planejamento.html`).

### `POST /entrevista/gerar-plano` 🔒 ⏱ `(5/min)`
Gera um plano de entrevista (10 perguntas: 6 hard skills + 4 soft skills) a partir de currículo + vaga, e cria os registros `Entrevista`/`PerguntaEntrevista`.

**Body (multipart/form-data):** `curriculo` (arquivo, obrigatório), `vaga_descricao` (texto, obrigatório)

**Resposta 201:**
```json
{
  "entrevista_id": "uuid",
  "numero_perguntas": 10,
  "plano": {"topicos": [...], "estrategia": "...", "questoes": ["..." , "..."]}
}
```
**Erros:** `400` (sem currículo/vaga, arquivo inválido), `413` (arquivo grande), `422` (prompt injection na vaga ou no currículo), `500` (erro ao gerar plano).

### `GET /entrevista/<entrevista_id>/executar` 🔒
Página de execução da entrevista (`entrevista_execucao.html`). `404` (texto simples, não JSON) se a entrevista não existir/pertencer ao usuário.

### `GET /entrevista/<entrevista_id>` 🔒
Dados completos da entrevista, incluindo todas as perguntas e respostas já dadas.

**Resposta 200:** `{id, status, numero_perguntas, plano_entrevista, criado_em, relatorio_final, perguntas: [{numero_sequencial, pergunta_principal, resposta_usuario, respondido, avaliacao_resposta, score}]}`

### `GET /entrevista/<entrevista_id>/pergunta/<numero>` 🔒
Dados de uma pergunta específica pelo número sequencial (1-10).

**Resposta 200:** `{pergunta_id, numero_sequencial, pergunta_principal, resposta_anterior, aprofundamentos_pendentes, total_perguntas}`
**Erros:** `404` (entrevista ou pergunta não encontrada).

### `POST /entrevista/<entrevista_id>/responder` 🔒 ⏱ `(30/min)`
Salva a resposta do usuário a uma pergunta e dispara a avaliação por IA.

**Body (JSON):** `{"numero_sequencial": 1, "resposta": "..."}`

**Validações:** resposta não vazia e ≤ 2000 caracteres; checagem de prompt injection.
**Resposta 200:** `{"salvo": true, "feedback_ia": "...", "score": 0-10, "aprofundamentos": []}` (campo `aprofundamentos` sempre vazio — funcionalidade de aprofundamento foi removida, entrevista é direta com as perguntas fixas).
**Efeito colateral:** muda `Entrevista.status` de `em_planejamento` para `em_andamento` na primeira resposta.

### `POST /entrevista/<entrevista_id>/finalizar` 🔒
Marca a entrevista como concluída e gera o relatório executivo final (score geral, pareceres, pontos fortes/fracos, recomendações, recomendação ao gestor).

**Pré-condição:** todas as perguntas precisam ter sido respondidas, senão `400`.
**Resposta 200:** `{"finalizado": true, "relatorio": {score_geral, parecer_final, pontos_fortes, pontos_fracos, recomendacoes, recomendacao_gestor}}`

### `GET /entrevista/<entrevista_id>/relatorio` 🔒
Página HTML do relatório (`entrevista_relatorio.html`).

### `GET /entrevista/<entrevista_id>/exportar-pdf` 🔒
Exporta o relatório final em PDF.

**Resposta 200:** arquivo PDF (`as_attachment=True`, nome `relatorio_entrevista_<id>.pdf`).
**Erros:** `404` (entrevista não encontrada), `500` (erro na geração do PDF).

---

## Resumo de status HTTP usados no projeto

| Código | Significado neste projeto |
|---|---|
| 200 | Sucesso |
| 201 | Recurso criado (plano de entrevista) |
| 400 | Erro de validação de entrada (campo faltando/inválido) |
| 404 | Recurso não encontrado ou não pertence ao usuário logado |
| 413 | Arquivo excede 5 MB |
| 422 | Conteúdo rejeitado por suspeita de prompt injection |
| 429 | Rate limit excedido |
| 500 | Erro inesperado (geralmente falha ao chamar a LLM ou gerar PDF) |