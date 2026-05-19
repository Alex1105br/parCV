# 🤖 Projeto SD — Chat com IA Local

Ambiente de desenvolvimento com IA rodando **100% local**, sem depender de nenhuma API externa ou enviar dados para a nuvem. Utiliza [Ollama](https://ollama.com/) para servir o modelo de linguagem e [Docker](https://www.docker.com/) para orquestrar tudo.

---

## 📁 Estrutura do Projeto

~~~
projeto_sd/
├── src/
│   ├── app.py                 # interface web (Flask)
│   ├── chat.py                # interface de chat via terminal
│   ├── static/                # CSS e JS da interface web
│   └── templates/             # HTML das páginas
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
docker exec -it sd_trabalho-app-1 bash
~~~

Este comando abre um terminal **dentro** do container `app`, onde o ambiente está configurado com Python, Git e acesso direto ao Ollama na rede interna Docker.

### 4. Iniciar a interface web

Dentro do container:

~~~bash
python3 src/app.py
~~~

Abra o navegador em **http://localhost:5005**. A interface oferece:
- **Chat** com a IA (streaming)
- **Análise de currículo** (score ATS)
- **Otimização de currículo** com download em PDF

### 5. Ou usar o chat via terminal

~~~bash
python3 src/chat.py
~~~

Digite sua mensagem e pressione Enter. A IA responde com streaming (palavra por palavra). Digite `sair` para encerrar.

### 6. Carregar um documento (TXT ou PDF)

Você pode fornecer um arquivo como contexto de duas formas:

**Via argumento de linha de comando** (carrega o documento ao iniciar o chat):

~~~bash
python3 src/chat.py --arquivo meu_documento.pdf
python3 src/chat.py --arquivo notas.txt
~~~

**Via `#` no chat** (carrega o documento durante a conversa):

~~~
Você: #relatorio.pdf
Você: #resumo.txt
~~~

O caminho pode ser absoluto ou relativo ao `/workspace`. Formatos suportados: `.txt` e `.pdf`.

> ⚠️ Documentos muito grandes podem ultrapassar o limite de contexto do modelo (4096 tokens). Para documentos extensos, considere dividir em partes menores.

### 7. Como passar arquivos locais para o container

O `docker-compose.yml` monta a pasta do projeto como volume em `/workspace` dentro do container:

~~~yaml
volumes:
  - .:/workspace
~~~

Isso significa que **qualquer arquivo dentro da pasta do projeto já está acessível automaticamente** no container. Para usar um documento:

1. **Copie o arquivo para a pasta do projeto** (ou uma subpasta, ex: `docs/`):

~~~bash
# No seu terminal local (fora do container)
cp ~/Downloads/relatorio.pdf /caminho/do/projeto/
cp ~/Documents/notas.txt /caminho/do/projeto/docs/
~~~

2. **Referencie dentro do container** pelo caminho relativo:

~~~bash
# Via argumento CLI
python3 src/chat.py --arquivo relatorio.pdf
python3 src/chat.py --arquivo docs/notas.txt

# Ou dentro do chat
Você: #relatorio.pdf
Você: #docs/notas.txt
~~~

Alternativamente, para copiar um arquivo avulso **sem mover para a pasta do projeto**, use `docker cp`:

~~~bash
# Copia um arquivo do host para dentro do container
docker cp ~/Downloads/artigo.pdf sd_trabalho-app-1:/workspace/artigo.pdf
~~~

---

## ⚙️ Configuração do Modelo

As configurações do modelo ficam no topo do arquivo `src/app.py`:

~~~python
OLLAMA_URL  = "http://ollama:11434/api/chat"
MODEL       = "qwen2.5:7b"
NUM_PREDICT = 800    # máximo de tokens por resposta
TEMPERATURE = 0.1    # 0.0 = direto/preciso | 1.0 = criativo
NUM_CTX     = 4096   # tamanho do contexto (memória do modelo)
~~~

---

## 🐳 Containers

| Container | Função |
|---|---|
| `sd_trabalho-app-1` | Interface web Flask (porta 5005) |
| `sd_trabalho-ollama-1` | Servidor do modelo de IA |
| `sd_trabalho-ollama-init-1` | Baixa o modelo na primeira execução e encerra |

---

## 💻 Integração com VSCode (opcional)

Se quiser usar a IA diretamente no VSCode com autocomplete e chat integrado, instale a extensão [Continue](https://marketplace.visualstudio.com/items?itemName=Continue.continue) e abra o projeto com:

`Ctrl+Shift+P` → **Dev Containers: Reopen in Container**

A configuração da IA será aplicada automaticamente via `postCreateCommand`.

---

## 🔧 Solução de Problemas

### Port 5005 já está em uso

Se receber o erro `Port 5005 is in use by another program`, siga estes passos:

**1. Identificar o processo usando a porta:**

~~~bash
# Linux/Mac
lsof -i :5005

# Ou
netstat -tlnp | grep 5005
~~~

**2. Parar o programa:**

~~~bash
# Encerrar o processo (substitua PID pelo número encontrado acima)
kill -9 <PID>

# Ou parar todos os containers Docker
docker compose down
~~~

**3. Ou usar uma porta diferente:**

Edite `docker-compose.yml` e altere a porta do serviço:

~~~yaml
services:
  app:
    ports:
      - "5006:5005"  # muda de 5005 para 5006 no host
~~~

Depois reinicie:

~~~bash
docker compose up -d
~~~

### Container não inicia ou demora muito

- **Primeira execução:** normal demora 5-10 minutos (download do modelo ~4.7 GB)
- **Próximas execuções:** deve ser rápido (< 10 segundos)

Se ficar preso, verifique:

~~~bash
# Ver logs em tempo real
docker compose logs -f

# Reiniciar tudo do zero
docker compose down
docker system prune -a  # remove imagens antigas
docker compose up -d --build
~~~
