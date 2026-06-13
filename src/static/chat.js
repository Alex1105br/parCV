(function () {
    'use strict';

    const chatContainer = document.getElementById('chat-container');
    const msgInput = document.getElementById('msg-input');
    const fileInput = document.getElementById('file-input');
    const fileNameLabel = document.getElementById('file-name');
    const welcome = document.getElementById('welcome');
    const form = document.getElementById('input-area');
    const btnNovaConversa = document.getElementById('btn-nova-conversa');
    const sessionList = document.getElementById('session-list');
    const pinnedList = document.getElementById('pinned-list');
    const sidebar = document.getElementById('sidebar');
    const btnToggleSidebar = document.getElementById('btn-toggle-sidebar');

    let selectedFile = null;
    const uploadedFileNames = new Set();
    let messageCount = 0;
    let isSending = false;
    let isCreatingSession = false;
    let pendingSid = null;
    const titledSids = new Set(); // rastrea quais sids já tiveram título gerado

    const welcomeMsgs = [
        'Como posso ajudar?',
        'No que posso ajudar hoje?',
        'Olá! Pronto para melhorar seu currículo?',
        'Vamos otimizar sua candidatura?',
        'Em que posso te ajudar?',
    ];

    const welcomeTips = [
        'Pergunte sobre uma vaga...',
        'Cole a descrição de uma vaga para análise',
        'Envie seu currículo em PDF ou TXT',
        'Peça sugestões de palavras-chave',
        'Pergunte como destacar sua experiência',
        'Peça dicas para entrevistas',
        'Pergunte sobre certificações relevantes',
    ];

    function randomItem(arr) { return arr[Math.floor(Math.random() * arr.length)]; }

    function showWelcome() {
        var msgEl = document.getElementById('welcome-msg');
        if (msgEl) msgEl.textContent = randomItem(welcomeMsgs);
        msgInput.placeholder = randomItem(welcomeTips);
    }
    showWelcome();

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

    function activateChat() {
        var w = document.getElementById('welcome');
        if (w) w.remove();
        // Move input to bottom of chat-main if not already there
        var chatMain = chatContainer.parentElement;
        if (form.parentElement !== chatMain) {
            chatMain.appendChild(form);
            form.classList.add('input-area--bottom');
        }
    }

    function addMessage(content, role, tempo) {
        activateChat();
        const div = document.createElement('div');
        div.classList.add('message', 'message--' + role);
        if (role === 'assistant') {
            div.innerHTML = renderMarkdown(content);
        } else {
            div.textContent = content;
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
        if (enabled) msgInput.focus();
    }

    function showTypingIndicator() {
        const div = document.createElement('div');
        div.classList.add('typing-indicator');
        div.innerHTML = '<span></span><span></span><span></span>';
        chatContainer.appendChild(div);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        return div;
    }

    async function enviarMensagem() {
        const msg = msgInput.value.trim();
        if (!msg && !selectedFile) return;
        if (isSending) return;
        isSending = true;

        msgInput.value = '';
        if (msg && !selectedFile) {
            addMessage(msg, 'user');
            messageCount++;
        }
        setInputEnabled(false);

        if (selectedFile) {
            await sendFileAndMessage(selectedFile, msg);
            return;
        }

        const typingDiv = showTypingIndicator();
        const assistantDiv = addMessage('', 'assistant');

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mensagem: msg })
            });

            const headerSid = response.headers.get('X-Session-Id');
            if (headerSid) {
                pendingSid = headerSid;
                var jaExiste = document.querySelector('[data-sid="' + headerSid + '"]');
                setActiveSession(headerSid, jaExiste ? null : 'Gerando título...', false);
            }

            if (!response.ok) {
                typingDiv.remove();
                try {
                    const errData = await response.json();
                    assistantDiv.classList.replace('message--assistant', 'message--error');
                    assistantDiv.textContent = 'Erro: ' + (errData.error || 'Erro desconhecido');
                } catch (_) {
                    assistantDiv.remove();
                }
                setInputEnabled(true);
                return;
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let fullText = '';
            let sseSid = null;
            let sseBuffer = '';

            while (true) {
                const { done, value } = await reader.read();

                if (value) {
                    sseBuffer += decoder.decode(value, { stream: !done });
                }
                const lines = sseBuffer.split('\n');
                sseBuffer = done ? '' : lines.pop();

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    let data;
                    try { data = JSON.parse(line.substring(6)); } catch (_) { continue; }

                    if (data.error) {
                        assistantDiv.classList.replace('message--assistant', 'message--error');
                        assistantDiv.textContent = 'Erro: ' + data.error;
                        break;
                    }

                    if (data.token) {
                        if (typingDiv.parentNode) typingDiv.remove();
                        fullText += data.token;
                        assistantDiv.innerHTML = renderMarkdown(fullText);
                        chatContainer.scrollTop = chatContainer.scrollHeight;
                    }

                    if (data.done) {
                        if (data.session_id) {
                            sseSid = data.session_id;
                            pendingSid = sseSid;
                            var jaExisteSse = document.querySelector('[data-sid="' + sseSid + '"]');
                            setActiveSession(sseSid, jaExisteSse ? null : 'Gerando título...', false);
                        }
                        if (data.titulo) {
                            _applyTitle(sseSid || headerSid, data.titulo);
                        }
                        addCopyButton(assistantDiv, fullText);
                        const t = document.createElement('div');
                        t.classList.add('message__time');
                        t.textContent = data.tempo;
                        assistantDiv.appendChild(t);
                    }
                }
                if (done) break;
            }

            typingDiv.remove();
            if (!fullText && assistantDiv.classList.contains('message--assistant')) {
                assistantDiv.remove();
            }
        } catch (err) {
            typingDiv.remove();
            assistantDiv.classList.replace('message--assistant', 'message--error');
            assistantDiv.textContent = 'Erro de conexão: ' + err.message;
        }

        isSending = false;
        setInputEnabled(true);
    }

    async function sendFileAndMessage(file, msg) {
        let assistantDiv = null;
        // addMessage('Enviando documento: ' + file.name + (msg ? ' e mensagem...' : '...'), 'system');

        uploadedFileNames.add(file.name);
        const formData = new FormData();
        formData.append('arquivo', file);
        if (msg) formData.append('mensagem', msg);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const contentType = response.headers.get('Content-Type') || '';
            const uploadSessionId = response.headers.get('X-Session-Id');
            const thisUploadSid = uploadSessionId || null;
            if (uploadSessionId) {
                pendingSid = uploadSessionId;
                // Insere imediatamente na sidebar com placeholder; _applyTitle atualiza depois
                var jaExisteUpload = document.querySelector('[data-sid="' + uploadSessionId + '"]');
                setActiveSession(uploadSessionId, jaExisteUpload ? null : 'Gerando título...', false);
            }

            if (contentType.includes('text/event-stream')) {
                addMessage('"' + file.name + '" carregado.', 'system');
                if (msg) { addMessage(msg, 'user'); messageCount++; }
                const typingDiv = showTypingIndicator();
                assistantDiv = addMessage('', 'assistant');
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let fullText = '';
                let uploadSseSid = null;
                let uploadSseBuffer = '';

                while (true) {
                    const { done, value } = await reader.read();

                    if (value) {
                        uploadSseBuffer += decoder.decode(value, { stream: !done });
                    }
                    const lines = uploadSseBuffer.split('\n');
                    uploadSseBuffer = done ? '' : lines.pop();

                    for (const line of lines) {
                        if (!line.startsWith('data: ')) continue;
                        let data;
                        try { data = JSON.parse(line.substring(6)); } catch (_) { continue; }

                        if (data.error) {
                            typingDiv.remove();
                            if (assistantDiv) {
                                assistantDiv.classList.replace('message--assistant', 'message--error');
                            } else {
                                addMessage('Erro: ' + data.error, 'error');
                            }
                            break;
                        }

                        if (data.token && assistantDiv) {
                            if (typingDiv.parentNode) typingDiv.remove();
                            fullText += data.token;
                            assistantDiv.innerHTML = renderMarkdown(fullText);
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }

                        if (data.done) {
                            console.log('[SSE upload done] session_id=', data.session_id, 'uploadSseSid antes=', uploadSseSid, 'thisUploadSid=', thisUploadSid);
                            if (data.session_id) {
                                uploadSseSid = data.session_id;
                                pendingSid = uploadSseSid;
                                var jaExisteSseUp = document.querySelector('[data-sid="' + uploadSseSid + '"]');
                                setActiveSession(uploadSseSid, jaExisteSseUp ? null : 'Gerando título...', false);
                            }
                            if (data.titulo) {
                                _applyTitle(uploadSseSid || thisUploadSid, data.titulo);
                            }
                            if (assistantDiv) {
                                addCopyButton(assistantDiv, fullText);
                                const t = document.createElement('div');
                                t.classList.add('message__time');
                                t.textContent = data.tempo;
                                assistantDiv.appendChild(t);
                            }
                        }
                    }
                    if (done) break;
                }
                typingDiv.remove();
            } else {
                const data = await response.json();
                const uploadOnlySid = data.session_id || null;
                if (uploadOnlySid) {
                    pendingSid = uploadOnlySid;
                    var jaExisteOnly = document.querySelector('[data-sid="' + uploadOnlySid + '"]');
                    setActiveSession(uploadOnlySid, jaExisteOnly ? null : 'Gerando título...', false);
                }
                if (data.error) {
                    addMessage('Erro: ' + data.error, 'error');
                } else {
                    addMessage('"' + file.name + '" carregado.', 'system');
                    if (data.titulo) {
                        _applyTitle(uploadOnlySid, data.titulo);
                    }
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

        setSelectedFile(null);
        isSending = false;
        setInputEnabled(true);
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

    function setSelectedFile(file) {
        selectedFile = file;
        if (!file) {
            fileNameLabel.textContent = '';
            fileNameLabel.innerHTML = '';
            return;
        }
        fileNameLabel.textContent = file.name;
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'input-area__filename-clear';
        btn.setAttribute('aria-label', 'Remover arquivo');
        btn.innerHTML = '&times;';
        btn.addEventListener('click', function () { setSelectedFile(null); });
        fileNameLabel.appendChild(btn);
    }

    function showDuplicateToast(name) {
        const existing = document.getElementById('duplicate-toast');
        if (existing) existing.remove();
        const toast = document.createElement('div');
        toast.id = 'duplicate-toast';
        toast.className = 'duplicate-toast';
        toast.textContent = '"' + name + '" já foi enviado antes.';
        document.body.appendChild(toast);
        requestAnimationFrame(function () { toast.classList.add('duplicate-toast--show'); });
        setTimeout(function () {
            toast.classList.remove('duplicate-toast--show');
            toast.addEventListener('transitionend', function () { toast.remove(); }, { once: true });
        }, 3000);
    }

    fileInput.addEventListener('change', function () {
        const file = fileInput.files[0];
        if (!file) return;
        if (uploadedFileNames.has(file.name)) {
            showDuplicateToast(file.name);
            fileInput.value = '';
            return;
        }
        setSelectedFile(file);
        fileInput.value = '';
    });

    // --- Sidebar logic ---
    const sidebarOverlay = document.getElementById('sidebar-overlay');

    function isMobile() { return window.innerWidth <= 768; }

    btnToggleSidebar.addEventListener('click', function () {
        if (isMobile()) {
            sidebar.classList.toggle('sidebar--mobile-open');
            sidebarOverlay.classList.toggle('sidebar-overlay--visible');
        } else {
            sidebar.classList.toggle('sidebar--collapsed');
        }
    });

    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', function () {
            sidebar.classList.remove('sidebar--mobile-open');
            sidebarOverlay.classList.remove('sidebar-overlay--visible');
        });
    }

    function allSessionItems() {
        var items = Array.from(sessionList.querySelectorAll('.sidebar__item'));
        if (pinnedList) items = Array.from(pinnedList.querySelectorAll('.sidebar__item')).concat(items);
        return items;
    }

    async function novaConversa() {
        if (isCreatingSession) return;
        isCreatingSession = true;
        try {
            await fetch('/chat/nova', { method: 'POST' });
            allSessionItems().forEach(function (el) {
                el.classList.remove('sidebar__item--active');
            });
            pendingSid = null;
            // Não limpa titledSids — cada sid é único, não precisa resetar
            messageCount = 0;
            clearChatUI();
        } catch (err) {
            addMessage('Erro ao criar conversa: ' + err.message, 'error');
        } finally {
            isCreatingSession = false;
        }
    }

    btnNovaConversa.addEventListener('click', novaConversa);

    // Close any open action menus when clicking outside
    document.addEventListener('click', function (e) {
        if (!e.target.closest('.sidebar__item-menu') && !e.target.closest('.sidebar__item-actions')) {
            document.querySelectorAll('.sidebar__item-actions--open').forEach(function (el) {
                el.classList.remove('sidebar__item-actions--open');
            });
        }
    });

    async function handleSidebarClick(e) {
        // 3-dot menu button
        const menuBtn = e.target.closest('.sidebar__item-menu');
        if (menuBtn) {
            e.stopPropagation();
            document.querySelectorAll('.sidebar__item-actions--open').forEach(function (el) {
                el.classList.remove('sidebar__item-actions--open');
            });
            const actions = menuBtn.nextElementSibling;
            if (actions) actions.classList.toggle('sidebar__item-actions--open');
            return;
        }

        // Pin/unpin action
        const pinBtn = e.target.closest('.sidebar__action--pin');
        if (pinBtn) {
            e.stopPropagation();
            const item = pinBtn.closest('.sidebar__item');
            const sid = item.dataset.sid;
            pinBtn.closest('.sidebar__item-actions').classList.remove('sidebar__item-actions--open');
            try {
                const res = await fetch('/chat/sessao/' + sid + '/fixar', { method: 'PATCH' });
                const data = await res.json();
                if (data.error) return;
                moveItemToList(item, data.fixado);
            } catch (_) {}
            return;
        }

        // Rename action
        const renameBtn = e.target.closest('.sidebar__action--rename');
        if (renameBtn) {
            e.stopPropagation();
            const item = renameBtn.closest('.sidebar__item');
            const sid = item.dataset.sid;
            const titleEl = item.querySelector('.sidebar__item-title');
            renameBtn.closest('.sidebar__item-actions').classList.remove('sidebar__item-actions--open');
            startInlineRename(item, sid, titleEl);
            return;
        }

        // Delete action
        const deleteBtn = e.target.closest('.sidebar__action--delete');
        if (deleteBtn) {
            e.stopPropagation();
            const item = deleteBtn.closest('.sidebar__item');
            const sid = item.dataset.sid;
            try {
                await fetch('/chat/sessao/' + sid, { method: 'DELETE' });
                const wasActive = item.classList.contains('sidebar__item--active');
                item.remove();
                if (wasActive) clearChatUI();
            } catch (err) {
                addMessage('Erro ao excluir: ' + err.message, 'error');
            }
            return;
        }

        // Click on item itself → switch session
        const item = e.target.closest('.sidebar__item');
        if (!item || e.target.closest('.sidebar__item-actions')) return;

        const sid = item.dataset.sid;
        try {
            const res = await fetch('/chat/sessao/' + sid, { method: 'POST' });
            const data = await res.json();
            if (data.error) {
                addMessage('Erro: ' + data.error, 'error');
                return;
            }
            const tituloExibido = data.titulo || item.querySelector('.sidebar__item-title').textContent;
            setActiveSession(data.id, tituloExibido, item.dataset.fixado === 'true');
            if (data.titulo) titledSids.add(data.id);
            loadMessages(data.mensagens);
            // Fecha sidebar no mobile
            if (isMobile()) {
                sidebar.classList.remove('sidebar--mobile-open');
                if (sidebarOverlay) sidebarOverlay.classList.remove('sidebar-overlay--visible');
            }
        } catch (err) {
            addMessage('Erro ao trocar conversa: ' + err.message, 'error');
        }
    }

    sessionList.addEventListener('click', handleSidebarClick);
    if (pinnedList) pinnedList.addEventListener('click', handleSidebarClick);

    function buildItemHTML(titulo, fixado) {
        var pinIcon = fixado ? '<i data-lucide="pin" class="sidebar__item-pin-icon"></i>' : '';
        var pinLabel = fixado ? 'Desafixar' : 'Fixar';
        var pinLucide = fixado ? 'pin-off' : 'pin';
        return pinIcon +
            '<span class="sidebar__item-title">' + escapeHtml(titulo) + '</span>' +
            '<button class="sidebar__item-menu" title="Opções" aria-label="Opções da conversa"><i data-lucide="ellipsis"></i></button>' +
            '<div class="sidebar__item-actions">' +
                '<button class="sidebar__action sidebar__action--pin" title="' + pinLabel + '"><i data-lucide="' + pinLucide + '"></i><span>' + pinLabel + '</span></button>' +
                '<button class="sidebar__action sidebar__action--rename" title="Renomear"><i data-lucide="pencil"></i><span>Renomear</span></button>' +
                '<button class="sidebar__action sidebar__action--delete" title="Excluir"><i data-lucide="trash-2"></i><span>Excluir</span></button>' +
            '</div>';
    }

    function moveItemToList(item, fixado) {
        item.dataset.fixado = fixado ? 'true' : 'false';
        item.innerHTML = buildItemHTML(item.querySelector('.sidebar__item-title').textContent, fixado);
        if (window.lucide) lucide.createIcons({ nodes: [item] });
        var targetList = fixado ? pinnedList : sessionList;
        if (!targetList) return;
        targetList.prepend(item);
        updatePinnedSectionVisibility();
    }

    function updatePinnedSectionVisibility() {
        if (!pinnedList) return;
        var section = pinnedList.previousElementSibling;
        if (pinnedList.children.length === 0) {
            if (section) section.style.display = 'none';
            pinnedList.style.display = 'none';
        } else {
            if (section) section.style.display = '';
            pinnedList.style.display = '';
        }
    }

    function setActiveSession(sid, titulo, fixado) {
        allSessionItems().forEach(function (el) {
            el.classList.remove('sidebar__item--active');
        });
        var isPinned = fixado === true;
        var existing = document.querySelector('[data-sid="' + sid + '"]');
        if (!existing) {
            existing = document.createElement('li');
            existing.classList.add('sidebar__item');
            existing.dataset.sid = sid;
            existing.dataset.fixado = isPinned ? 'true' : 'false';
            existing.innerHTML = buildItemHTML(titulo || 'Carregando título...', isPinned);
            sessionList.prepend(existing);
            if (window.lucide) lucide.createIcons({ nodes: [existing] });
        } else {
            // Move para o topo da lista se não estiver lá
            var targetList = isPinned ? pinnedList : sessionList;
            if (targetList && existing.parentElement !== targetList) {
                targetList.prepend(existing);
            } else if (existing.previousElementSibling) {
                existing.parentElement.prepend(existing);
            }
            // Só atualiza o título se o novo não for vazio
            if (titulo) {
                existing.querySelector('.sidebar__item-title').textContent = titulo;
            }
        }
        existing.classList.add('sidebar__item--active');
    }

    function startInlineRename(item, sid, titleEl) {
        if (item.querySelector('.sidebar__item-rename-input')) return;
        const currentTitle = titleEl.textContent;
        const input = document.createElement('input');
        input.type = 'text';
        input.value = currentTitle;
        input.className = 'sidebar__item-rename-input';
        item.appendChild(input);
        input.focus();
        input.select();

        let done = false;

        async function commit() {
            if (done) return;
            done = true;
            const novoTitulo = input.value.trim();
            input.remove();
            if (novoTitulo && novoTitulo !== currentTitle) {
                try {
                    await fetch('/chat/sessao/' + sid + '/titulo', {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ titulo: novoTitulo })
                    });
                    titleEl.textContent = novoTitulo;
                } catch (_) {}
            }
        }

        function cancel() {
            if (done) return;
            done = true;
            input.remove();
        }

        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') { e.preventDefault(); commit(); }
            if (e.key === 'Escape') { e.preventDefault(); cancel(); }
        });
        input.addEventListener('blur', commit);
    }

    function clearChatUI() {
        chatContainer.innerHTML = '';
        const w = document.createElement('div');
        w.classList.add('chat__welcome');
        w.id = 'welcome';
        w.innerHTML = '<h2 id="welcome-msg"></h2>';
        w.appendChild(form);
        form.classList.remove('input-area--bottom');
        if (window.lucide) lucide.createIcons({ nodes: [w] });
        chatContainer.appendChild(w);
        showWelcome();
        messageCount = 0;
    }

    function loadMessages(mensagens) {
        chatContainer.innerHTML = '';
        messageCount = 0;
        if (!mensagens || mensagens.length === 0) {
            clearChatUI();
            return;
        }
        var welcomeEl = document.getElementById('welcome');
        if (welcomeEl) welcomeEl.style.display = 'none';
        mensagens.forEach(function (m) {
            if (m.role === 'user' || m.role === 'assistant' || m.role === 'system') {
                var msgDiv = addMessage(m.content, m.role);
                if (m.role === 'user') messageCount++;
                if (m.role === 'assistant') addCopyButton(msgDiv, m.content);
            }
        });
    }

    // ── Título da conversa ───────────────────────────────────────────────────
    // O título agora é gerado de forma SÍNCRONA no backend (dentro da própria
    // thread do SSE) e enviado no payload final 'done' como 'titulo'.
    // _applyTitle apenas aplica o valor recebido na sidebar.
    function _applyTitle(sid, titulo) {
        if (!sid || !titulo || !titulo.trim()) return;
        titledSids.add(sid);
        var item = document.querySelector('[data-sid="' + sid + '"]');
        if (item) {
            item.querySelector('.sidebar__item-title').textContent = titulo;
        } else {
            setActiveSession(sid, titulo, false);
        }
        if (pendingSid === sid) pendingSid = null;
    }

    msgInput.focus();
})();