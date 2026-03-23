# 🤖 Projeto SD — Chat com IA Local

Ambiente de desenvolvimento com IA rodando **100% local**, sem depender de nenhuma API externa ou enviar dados para a nuvem. Utiliza [Ollama](https://ollama.com/) para servir o modelo de linguagem e [Docker](https://www.docker.com/) para orquestrar tudo.

---

## 📁 Estrutura do Projeto

~~~
projeto_sd/
├── .devcontainer/
│   ├── continue-config.json   # configuração da IA no VSCode (extensão Continue)
│   └── devcontainer.json      # configuração do Dev Container
├── src/
│   └── chat.py                # interface de chat com a IA via terminal
├── docker-compose.yml         # orquestração dos containers
├── Dockerfile                 # imagem do ambiente de desenvolvimento
└── README.md
~~~

---

## 🧠 Modelo de IA — Qwen 2.5 7B

O modelo utilizado é o **Qwen 2.5 7B**, desenvolvido pela Alibaba Cloud. É um modelo de linguagem com 7,6 bilhões de parâmetros, quantizado em Q4_K_M para rodar eficientemente em CPU sem GPU dedicada.

### ✅ O que ele consegue fazer

- Responder perguntas e explicar conceitos técnicos
- Auxiliar na escrita e revisão de código
- Resumir textos e documentos
- Manter contexto ao longo de uma conversa
- Responder em português e outros idiomas

### ❌ O que ele não consegue fazer

- Acessar a internet ou informações em tempo real
- Processar imagens, áudio ou vídeo
- Executar código diretamente
- Ter desempenho equivalente a modelos maiores (GPT-4, Claude Opus) em raciocínio complexo
- Respostas instantâneas rodando só em CPU — espere entre 1 e 3 minutos por resposta dependendo do hardware

---

## 🚀 Como rodar

### Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) instalado
- [Docker Compose](https://docs.docker.com/compose/) instalado

### 1. Subir o ambiente

~~~bash
docker compose up -d
~~~

Na **primeira execução** este comando vai:
- Baixar a imagem do Ollama (~1 GB)
- Buildar a imagem do container `app`
- Baixar o modelo Qwen 2.5 7B (~4.7 GB) automaticamente

Nas execuções seguintes tudo já estará em cache e levará menos de 10 segundos.

### 2. Rebuildar após mudanças no Dockerfile

Se você modificar o `Dockerfile` (adicionar dependências, por exemplo), é necessário rebuildar a imagem:

~~~bash
docker compose down
docker compose up -d --build
~~~

O `--build` força o Docker a reconstruir a imagem do zero com as novas configurações. Sem ele, o Docker reutiliza a imagem antiga e as mudanças não são aplicadas.

### 3. Entrar no container

~~~bash
docker exec -it sd_trabalho-main-app-1 bash
~~~

Este comando abre um terminal **dentro** do container `app`, onde o ambiente está configurado com Python, Git e acesso direto ao Ollama na rede interna Docker.

### 4. Iniciar o chat com a IA

Dentro do container:

~~~bash
python3 src/chat.py
~~~

Digite sua mensagem e pressione Enter. A IA responde com streaming (palavra por palavra). Digite `sair` para encerrar.

---

## ⚙️ Configuração do Chat

As configurações do modelo ficam no topo do arquivo `src/chat.py`:

~~~python
OLLAMA_URL  = "http://ollama:11434/api/chat"
MODEL       = "qwen2.5:7b"
NUM_PREDICT = 200    # máximo de tokens por resposta
TEMPERATURE = 0.1    # 0.0 = direto/preciso | 1.0 = criativo
NUM_CTX     = 512    # tamanho do contexto (memória do modelo)
~~~

---

## 🐳 Containers

| Container | Função |
|---|---|
| `projeto_sd-app-1` | Ambiente de desenvolvimento principal |
| `projeto_sd-ollama-1` | Servidor do modelo de IA |
| `projeto_sd-ollama-init-1` | Baixa o modelo na primeira execução e encerra |

---

## 💻 Integração com VSCode (opcional)

Se quiser usar a IA diretamente no VSCode com autocomplete e chat integrado, instale a extensão [Continue](https://marketplace.visualstudio.com/items?itemName=Continue.continue) e abra o projeto com:

`Ctrl+Shift+P` → **Dev Containers: Reopen in Container**

A configuração da IA será aplicada automaticamente via `postCreateCommand`.
