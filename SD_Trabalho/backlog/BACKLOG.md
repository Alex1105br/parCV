---
marp: true
theme: parcv
transition: slide
class: cover
---

# parCV — Backlog

---

## Sprint 1

| | título | label | pts |
| - | :- | :-: | :-: |
| ✓ | Configurar ambiente virtual e dependências básicas (Flask, API de LLM) | infra | 3 |
| ✓ | Criar validação de variáveis de ambiente no boot | infra | 3 |
| ✓ | Criar versão inicial da tela de análise | ux | 5 |
| ✓ | Criar versão inicial da tela de chat | ux | 5 |
| ✓ | Adotar paleta de cores consistente | ux | 3 |
| ✓ | Empregar LLM maior para agilizar análise e respostas | feature | 3 |

> Foco: infra mínima funcional + primeiras telas.

---

## Sprint 2

| | título | label | pts |
| - | :- | :-: | :-: |
| ✓ | Suporte a upload de DOCX (python-docx) | feature | 5 |
| ✓ | Sugestão de palavras-chave da vaga que estão faltando no CV | feature | 5 |
| ✓ | Comparação lado-a-lado: currículo original vs. otimizado com diff visual | feature | 5 |
| ✓ | Sugestão de certificados relevantes para a vaga | feature | 5 |
| ✓ | Score parcial em tempo real (progress bar animada) | ux | 3 |

> Foco: produto utilizável de ponta a ponta — upload, análise inteligente, resultado visual.

---

## Sprint 3

| | título | label | pts |
| - | :- | :-: | :-: |
| ✓ | Validação de tamanho máximo de upload e sanitização de input | security | 3 |
| ✓ | 3 templates visuais de PDF (clássico, moderno, executivo) | feature | 7 |
| ✓ | Edição manual do currículo otimizado antes de gerar PDF | feature | 5 |
| ✓ | Preview do PDF no navegador antes do download | ux | 3 |
| ✓ | Incluir foto e links clicáveis no PDF gerado | feature | 5 |
| ✓ | Rate limiting nas rotas /analisar e /otimizar | security | 3 |

> Foco: segurança e UX de PDF.

---

![rate-limits](rate-lims.png)

---

## Sprint 4 - Atual

| | título | label | pts |
| - | :- | :-: | :-: |
| ✓ | Adicionar logging estruturado (request ID, duração LLM) | infra | 3 |
| ✓ | Persistir análises e currículos otimizados em banco de dados | feature | 7 |
| ✓ | Endpoint GET /analises/\<id\> retornando JSON da análise | feature | 3 |
| ✓ | Tela Histórico de Análises com listagem e detalhes | feature | 5 |
| ✓ | Migrar sessão de chat do cookie para banco | feature | 5 |

> Foco: construir base de dados (persistência + histórico).

---

## Sprint 5

| | título | label | pts |
| - | :- | :-: | :-: |
| ✓ | Indicador de digitando e tratamento de erro inline no chat | ux | 3 |
| ✓ | sanitização de input + proteção contra *prompt injection* | security | 5 |
| ✓ | Botão Nova conversa e listagem de conversas na sidebar | ux | 5 |
| ✓ | Upload de currículo no chat para perguntas contextuais | feature | 5 |
| ✓ | Simulação de entrevista com IA | feature | 7 |
| ✓ | Sign-in/up | feature | 5 |

> Foco: UX de chat.

---

## Sprint 6 - Próxima

| | título | label | pts |
| - | :- | :-: | :-: |
| ✓ | Adicionando soft skills à simulação de entrevista. | feature | 5 |
| ✓ | Design final do projeto | ux | 5 |
| ✓ | README atualizado | docs | 3 |

> Foco: documentação.