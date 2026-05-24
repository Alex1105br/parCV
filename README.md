# 🚀 Guia de Execução — WSL

> Todos os comandos são executados dentro do **WSL (Windows Subsystem for Linux)**

---

## ⚡ Passo a passo

### 1. Abrir o WSL e navegar até o projeto

Navegue até a pasta onde você clonou o repositório. Exemplo:

```bash
cd /mnt/c/Users/<seu-usuario>/Downloads/SD_Trabalho
```

### 2. Criar o ambiente virtual

```bash
python3 -m venv venv
```

### 3. Ativar o venv

```bash
source venv/bin/activate
```

> 💡 O terminal vai mudar para `(venv) root@...` — isso confirma que está ativo.

### 4. Instalar as dependências

```bash
pip3 install -r requirements.txt
```

### 5. Instalar o Poppler (necessário para PDF)

```bash
sudo apt update && sudo apt install poppler-utils -y
```

### 6. Configurar a API Key do Groq

Antes de rodar, verifique se o arquivo `src/config.py` possui uma API Key do Groq preenchida:

```python
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "sua_api_key_aqui")
```

> 💡 Substitua `"sua_api_key_aqui"` pela sua chave real. Você pode obter uma em [console.groq.com](https://console.groq.com).
>
> ⚠️ Se o campo estiver vazio `("")`, o projeto **não vai funcionar corretamente**.

### 7. Rodar o projeto

```bash
python3 run.py
```

### 8. Acessar no navegador

Com o servidor rodando, abra o navegador do Windows e acesse:

```
http://localhost:5000/
```

---

## 🔁 Próximas vezes

Sempre que abrir um novo terminal WSL, ative o venv antes de rodar:

```bash
source venv/bin/activate
python3 run.py
```

Depois é só acessar **http://localhost:5000/** no navegador.

Para sair do venv:

```bash
deactivate
```

---

> ⚠️ **Lembre-se:** todos os comandos devem ser executados **dentro do WSL**, não no PowerShell ou CMD do Windows. O navegador é acessado normalmente pelo Windows.
