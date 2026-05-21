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

    function escapeHtml(text) {
        var d = document.createElement('div');
        d.appendChild(document.createTextNode(text));
        return d.innerHTML;
    }

    function renderMarkdown(text) {
        var lines = text.split('\n');
        var html = '';
        var inList = false;

        for (var i = 0; i < lines.length; i++) {
            var line = lines[i];
            var trimmed = line.trim();

            // Numbered list: "1. item"
            var numMatch = trimmed.match(/^(\d+)\.\s+(.+)$/);
            if (numMatch) {
                if (!inList) { html += '<ol>'; inList = 'ol'; }
                html += '<li>' + formatInline(numMatch[2]) + '</li>';
                continue;
            }

            // Bullet list: "* item" or "- item"
            var bulletMatch = trimmed.match(/^[\*\-]\s+(.+)$/);
            if (bulletMatch) {
                if (!inList) { html += '<ul>'; inList = 'ul'; }
                html += '<li>' + formatInline(bulletMatch[1]) + '</li>';
                continue;
            }

            // Close open list
            if (inList) { html += '</' + inList + '>'; inList = false; }

            if (!trimmed) {
                html += '<br>';
            } else {
                html += '<p>' + formatInline(line) + '</p>';
            }
        }
        if (inList) { html += '</' + inList + '>'; }
        return html;
    }

    function formatInline(text) {
        var s = escapeHtml(text);
        s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
        return s;
    }

    function addMessage(content, role, tempo) {
        if (welcome) welcome.style.display = 'none';
        const div = document.createElement('div');
        div.classList.add('message', 'message--' + role);
        if (role === 'assistant') {
            div.innerHTML = renderMarkdown(content);
        } else {
            div.textContent = content;
        }
        if (role === 'user') {
            addCopyButton(div, content);
        }
        if (tempo) {
            const t = document.createElement('div');
            t.classList.add('message__time');
            t.textContent = tempo;
            div.appendChild(t);
        }
        chatContainer.appendChild(div);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        return div;
    }

    function addCopyButton(msgDiv, text) {
        const btn = document.createElement('button');
        btn.classList.add('message__copy');
        btn.title = 'Copiar';
        btn.innerHTML = '<i data-lucide="copy"></i>';
        btn.addEventListener('click', function () {
            navigator.clipboard.writeText(text).then(function () {
                btn.innerHTML = '<i data-lucide="check"></i>';
                if (window.lucide) lucide.createIcons({ nodes: [btn] });
                setTimeout(function () {
                    btn.innerHTML = '<i data-lucide="copy"></i>';
                    if (window.lucide) lucide.createIcons({ nodes: [btn] });
                }, 2000);
            });
        });
        msgDiv.appendChild(btn);
        if (window.lucide) lucide.createIcons({ nodes: [btn] });
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
                        assistantDiv.textContent = 'Erro: ' + data.error;
                        break;
                    }

                    if (data.token) {
                        fullText += data.token;
                        assistantDiv.innerHTML = renderMarkdown(fullText);
                        chatContainer.scrollTop = chatContainer.scrollHeight;
                    }

                    if (data.done) {
                        addCopyButton(assistantDiv, fullText);
                        const t = document.createElement('div');
                        t.classList.add('message__time');
                        t.textContent = data.tempo;
                        assistantDiv.appendChild(t);
                    }
                }
            }
        } catch (err) {
            assistantDiv.classList.replace('message--assistant', 'message--error');
            assistantDiv.textContent = 'Erro de conexão: ' + err.message;
        }

        setInputEnabled(true);
    }

    async function sendFileAndMessage(file, msg) {
        const assistantDiv = msg ? addMessage('', 'assistant') : null;
        addMessage('Enviando documento: ' + file.name + (msg ? ' e mensagem...' : '...'), 'system');

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
                                assistantDiv.textContent = 'Erro: ' + data.error;
                            } else {
                                addMessage('Erro: ' + data.error, 'error');
                            }
                            break;
                        }

                        if (data.token && assistantDiv) {
                            fullText += data.token;
                            assistantDiv.innerHTML = renderMarkdown(fullText);
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }

                        if (data.done && assistantDiv) {
                            addCopyButton(assistantDiv, fullText);
                            const t = document.createElement('div');
                            t.classList.add('message__time');
                            t.textContent = data.tempo;
                            assistantDiv.appendChild(t);
                        }
                    }
                }
            } else {
                const data = await response.json();
                if (data.error) {
                    addMessage('Erro: ' + data.error, 'error');
                } else {
                    addMessage('Documento "' + data.filename + '" carregado (' + data.chars + ' caracteres).', 'system');
                }
            }
        } catch (err) {
            if (assistantDiv) {
                assistantDiv.classList.replace('message--assistant', 'message--error');
                assistantDiv.textContent = 'Erro de conexão: ' + err.message;
            } else {
                addMessage('Erro de conexão: ' + err.message, 'error');
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
            w.innerHTML = '<i data-lucide="message-square" class="chat__welcome-icon"></i><h2>Chat</h2><p>Digite uma mensagem ou envie um documento para começar.</p>';
            if (window.lucide) lucide.createIcons({ nodes: [w] });
            chatContainer.appendChild(w);
        } catch (err) {
            addMessage('Erro ao limpar: ' + err.message, 'error');
        }
    }

    // Query history
    const history = [];
    let historyIdx = -1;
    let tempInput = '';

    function autoResize() {
        msgInput.style.height = 'auto';
        var maxH = window.innerHeight / 3;
        var scrollH = msgInput.scrollHeight;
        msgInput.style.height = Math.min(scrollH, maxH) + 'px';
        msgInput.style.overflowY = scrollH > maxH ? 'auto' : 'hidden';
    }

    // Event listeners
    form.addEventListener('submit', function (e) {
        e.preventDefault();
        const msg = msgInput.value.trim();
        if (msg) {
            history.push(msg);
            historyIdx = history.length;
        }
        enviarMensagem();
        msgInput.style.height = 'auto';
    });

    msgInput.addEventListener('input', autoResize);

    msgInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            form.requestSubmit();
            return;
        }
        if (e.key === 'ArrowUp' && msgInput.selectionStart === 0 && history.length) {
            e.preventDefault();
            if (historyIdx === history.length) tempInput = msgInput.value;
            historyIdx = Math.max(0, historyIdx - 1);
            msgInput.value = history[historyIdx];
            autoResize();
        }
        if (e.key === 'ArrowDown' && msgInput.selectionStart === msgInput.value.length && historyIdx < history.length) {
            e.preventDefault();
            historyIdx = Math.min(history.length, historyIdx + 1);
            msgInput.value = historyIdx === history.length ? tempInput : history[historyIdx];
            autoResize();
        }
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
