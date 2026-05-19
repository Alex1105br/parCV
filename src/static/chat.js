(function () {
    'use strict';

    const chatContainer = document.getElementById('chat-container');
    const msgInput = document.getElementById('msg-input');
    const sendBtn = document.getElementById('send-btn');
    const fileInput = document.getElementById('file-input');
    const fileNameLabel = document.getElementById('file-name');
    const welcome = document.getElementById('welcome');
    const form = document.getElementById('input-area');
    const btnLimpar = document.getElementById('btn-limpar');

    let selectedFile = null;

    function addMessage(content, role, tempo) {
        if (welcome) welcome.style.display = 'none';
        const div = document.createElement('div');
        div.classList.add('message', 'message--' + role);
        div.textContent = content;
        if (tempo) {
            const t = document.createElement('div');
            t.classList.add('message__time');
            t.textContent = '\u23F1 ' + tempo;
            div.appendChild(t);
        }
        chatContainer.appendChild(div);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        return div;
    }

    function setInputEnabled(enabled) {
        msgInput.disabled = !enabled;
        sendBtn.disabled = !enabled;
        if (enabled) msgInput.focus();
    }

    async function enviarMensagem() {
        const msg = msgInput.value.trim();
        if (!msg && !selectedFile) return;

        msgInput.value = '';
        if (msg) addMessage(msg, 'user');
        setInputEnabled(false);

        if (selectedFile) {
            await sendFileAndMessage(selectedFile, msg);
            return;
        }

        const assistantDiv = addMessage('', 'assistant');

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mensagem: msg })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let fullText = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const data = JSON.parse(line.substring(6));

                    if (data.error) {
                        assistantDiv.classList.replace('message--assistant', 'message--error');
                        assistantDiv.textContent = '\u274C ' + data.error;
                        break;
                    }

                    if (data.token) {
                        fullText += data.token;
                        assistantDiv.textContent = fullText;
                        chatContainer.scrollTop = chatContainer.scrollHeight;
                    }

                    if (data.done) {
                        const t = document.createElement('div');
                        t.classList.add('message__time');
                        t.textContent = '\u23F1 ' + data.tempo;
                        assistantDiv.appendChild(t);
                    }
                }
            }
        } catch (err) {
            assistantDiv.classList.replace('message--assistant', 'message--error');
            assistantDiv.textContent = '\u274C Erro de conexão: ' + err.message;
        }

        setInputEnabled(true);
    }

    async function sendFileAndMessage(file, msg) {
        const assistantDiv = msg ? addMessage('', 'assistant') : null;
        addMessage('\uD83D\uDCCE Enviando documento: ' + file.name + (msg ? ' e mensagem...' : '...'), 'system');

        const formData = new FormData();
        formData.append('arquivo', file);
        if (msg) formData.append('mensagem', msg);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const contentType = response.headers.get('Content-Type') || '';
            if (contentType.includes('text/event-stream')) {
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let fullText = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value, { stream: true });
                    const lines = chunk.split('\n');

                    for (const line of lines) {
                        if (!line.startsWith('data: ')) continue;
                        const data = JSON.parse(line.substring(6));

                        if (data.error) {
                            if (assistantDiv) {
                                assistantDiv.classList.replace('message--assistant', 'message--error');
                                assistantDiv.textContent = '\u274C ' + data.error;
                            } else {
                                addMessage('\u274C ' + data.error, 'error');
                            }
                            break;
                        }

                        if (data.token && assistantDiv) {
                            fullText += data.token;
                            assistantDiv.textContent = fullText;
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }

                        if (data.done && assistantDiv) {
                            const t = document.createElement('div');
                            t.classList.add('message__time');
                            t.textContent = '\u23F1 ' + data.tempo;
                            assistantDiv.appendChild(t);
                        }
                    }
                }
            } else {
                const data = await response.json();
                if (data.error) {
                    addMessage('\u274C ' + data.error, 'error');
                } else {
                    addMessage('\u2705 Documento "' + data.filename + '" carregado (' + data.chars + ' caracteres).', 'system');
                }
            }
        } catch (err) {
            if (assistantDiv) {
                assistantDiv.classList.replace('message--assistant', 'message--error');
                assistantDiv.textContent = '\u274C Erro de conexão: ' + err.message;
            } else {
                addMessage('\u274C Erro de conexão: ' + err.message, 'error');
            }
        }

        selectedFile = null;
        fileNameLabel.textContent = '';
        setInputEnabled(true);
    }

    async function limparChat() {
        try {
            await fetch('/limpar', { method: 'POST' });
            chatContainer.innerHTML = '';
            const w = document.createElement('div');
            w.classList.add('chat__welcome');
            w.id = 'welcome';
            w.innerHTML = '<h2>Bem-vindo ao Chat IA Local</h2><p>Digite uma mensagem ou envie um documento (.txt / .pdf) para começar.</p>';
            chatContainer.appendChild(w);
        } catch (err) {
            addMessage('\u274C Erro ao limpar: ' + err.message, 'error');
        }
    }

    // Event listeners
    form.addEventListener('submit', function (e) {
        e.preventDefault();
        enviarMensagem();
    });

    fileInput.addEventListener('change', function () {
        const file = fileInput.files[0];
        if (!file) return;
        selectedFile = file;
        fileNameLabel.textContent = file.name;
        fileInput.value = '';
    });

    btnLimpar.addEventListener('click', limparChat);

    msgInput.focus();
})();
