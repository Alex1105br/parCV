(function () {
    'use strict';

    var container = document.getElementById('curriculos-container');

    // ── Helpers ─────────────────────────────────────────────────────────
    function esc(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function formatDate(iso) {
        var d = new Date(iso);
        return d.toLocaleDateString('pt-BR', { day:'2-digit', month:'2-digit', year:'numeric' })
             + ' ' + d.toLocaleTimeString('pt-BR', { hour:'2-digit', minute:'2-digit' });
    }

    // ── Render ───────────────────────────────────────────────────────────
    function renderEmpty() {
        container.innerHTML =
            '<div class="curriculos-empty">' +
                '<i data-lucide="file-x"></i>' +
                '<p class="curriculos-empty__title">Nenhum currículo salvo</p>' +
                '<p class="curriculos-empty__sub">Os currículos são salvos automaticamente quando você usa Analisar currículo ou Simulação de entrevista.</p>' +
            '</div>';
        if (window.lucide) lucide.createIcons({ nodes: [container] });
    }

    function renderList(curriculos) {
        if (!curriculos || curriculos.length === 0) { renderEmpty(); return; }

        var html = '<ul class="curriculos-list">';
        curriculos.forEach(function (c) {
            var nomeArquivo = c.arquivo_nome || (c.label + '.pdf');
            html +=
                '<li class="curriculo-card" data-id="' + esc(c.id) + '">' +
                    '<div class="curriculo-card__icon"><i data-lucide="file-text"></i></div>' +
                    '<div class="curriculo-card__body">' +
                        '<div class="curriculo-card__top">' +
                            '<span class="curriculo-label" data-id="' + esc(c.id) + '" title="Clique duas vezes para editar">' +
                                esc(c.label) +
                            '</span>' +
                            '<span class="curriculo-card__date">' + esc(formatDate(c.criado_em)) + '</span>' +
                        '</div>' +
                        '<p class="curriculo-card__preview">' + esc(nomeArquivo) + '</p>' +
                    '</div>' +
                    '<div class="curriculo-card__actions">' +
                        '<button type="button" class="curriculo-card__btn" data-action="visualizar" data-id="' + esc(c.id) + '" data-label="' + esc(c.label) + '" title="Visualizar PDF">' +
                            '<i data-lucide="eye"></i>' +
                        '</button>' +
                        '<button type="button" class="curriculo-card__btn" data-action="baixar" data-id="' + esc(c.id) + '" data-label="' + esc(c.label) + '" title="Baixar PDF">' +
                            '<i data-lucide="download"></i>' +
                        '</button>' +
                        '<button type="button" class="curriculo-card__btn curriculo-card__btn--danger" data-action="deletar" data-id="' + esc(c.id) + '" data-label="' + esc(c.label) + '" title="Apagar">' +
                            '<i data-lucide="trash-2"></i>' +
                        '</button>' +
                    '</div>' +
                '</li>';
        });
        html += '</ul>';
        container.innerHTML = html;
        if (window.lucide) lucide.createIcons({ nodes: [container] });

        // Duplo clique na label → edição inline
        container.querySelectorAll('.curriculo-label').forEach(function (labelEl) {
            labelEl.addEventListener('dblclick', function () {
                startEditLabel(labelEl);
            });
        });
    }

    // ── Edição inline da label ──────────────────────────────────────────
    function startEditLabel(labelEl) {
        if (labelEl.dataset.editing) return;
        labelEl.dataset.editing = 'true';
        var id = labelEl.dataset.id;
        var atual = labelEl.textContent.trim();

        labelEl.classList.add('curriculo-label--editing');
        labelEl.innerHTML =
            '<input class="curriculo-label__input" type="text" value="' + esc(atual) + '" maxlength="50">';
        var input = labelEl.querySelector('input');
        input.focus();
        input.select();

        var done = false;
        function commit() {
            if (done) return;
            done = true;
            var novo = input.value.trim();
            if (!novo || novo === atual) {
                resetLabel(labelEl, atual, id);
                return;
            }
            saveLabel(labelEl, id, novo, atual);
        }

        input.addEventListener('blur', commit);
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
            if (e.key === 'Escape') { done = true; resetLabel(labelEl, atual, id); }
        });
    }

    function resetLabel(labelEl, texto, id) {
        delete labelEl.dataset.editing;
        labelEl.classList.remove('curriculo-label--editing');
        labelEl.textContent = texto;
        labelEl.dataset.id = id;
        // Re-bind dblclick
        labelEl.addEventListener('dblclick', function () { startEditLabel(labelEl); }, { once: true });
    }

    async function saveLabel(labelEl, id, novo, anterior) {
        try {
            var resp = await fetch('/curriculos/' + id + '/label', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ label: novo }),
            });
            var data = await resp.json();
            if (!resp.ok) throw new Error(data.error || 'Erro ao salvar');
            resetLabel(labelEl, data.label, id);
            // Atualiza atributo nos botões correspondentes
            ['visualizar', 'baixar'].forEach(function (action) {
                var btn = container.querySelector('[data-action="' + action + '"][data-id="' + id + '"]');
                if (btn) btn.dataset.label = data.label;
            });
        } catch (err) {
            resetLabel(labelEl, anterior, id);
            window.alert('Não foi possível salvar a label: ' + err.message);
        }
    }

    // ── Modal PDF (Task 4) ──────────────────────────────────────────────
    function openPdfModal(id, label) {
        var overlay = document.createElement('div');
        overlay.className = 'pdf-modal-overlay';
        overlay.innerHTML =
            '<div class="pdf-modal">' +
                '<div class="pdf-modal__header">' +
                    '<h3 class="pdf-modal__title">' + esc(label) + '</h3>' +
                    '<div style="display:flex; gap:8px; align-items:center;">' +
                        '<button type="button" class="pdf-modal__download" title="Baixar PDF" style="background:none; border:none; cursor:pointer; color:#666; padding:4px; display:flex; align-items:center; justify-content:center; transition:color 0.2s;">' +
                            '<i data-lucide="download"></i>' +
                        '</button>' +
                        '<button type="button" class="pdf-modal__close" title="Fechar (Esc)">' +
                            '<i data-lucide="x"></i>' +
                        '</button>' +
                    '</div>' +
                '</div>' +
                '<div class="pdf-modal__body">' +
                    '<iframe class="pdf-modal__iframe" src="/curriculos/pdf/' + id + '"></iframe>' +
                '</div>' +
            '</div>';

        document.body.appendChild(overlay);
        if (window.lucide) lucide.createIcons({ nodes: [overlay] });

        function close() {
            document.removeEventListener('keydown', onKeyDown);
            overlay.remove();
        }

        function onKeyDown(e) {
            if (e.key === 'Escape') close();
        }

        overlay.querySelector('.pdf-modal__close').addEventListener('click', close);
        overlay.querySelector('.pdf-modal__download').addEventListener('click', function() {
            window.location.href = '/curriculos/download/' + id;
        });
        
        // Efeito hover no botão de download via JS
        var btnDownload = overlay.querySelector('.pdf-modal__download');
        btnDownload.onmouseover = function() { this.style.color = '#333'; };
        btnDownload.onmouseout = function() { this.style.color = '#666'; };

        overlay.addEventListener('click', function (e) {
            if (e.target === overlay) close();
        });
        document.addEventListener('keydown', onKeyDown);
    }

    // ── Ações ───────────────────────────────────────────────────────────
    container.addEventListener('click', async function (e) {
        var btn = e.target.closest('[data-action]');
        if (!btn) return;

        var action = btn.dataset.action;
        var id     = btn.dataset.id;
        var label  = btn.dataset.label || 'este currículo';

        if (action === 'visualizar') {
            openPdfModal(id, label);
            return;
        }

        if (action === 'baixar') {
            window.location.href = '/curriculos/download/' + id;
            return;
        }

        if (action === 'deletar') {
            var ok = await confirmModal({
                title:       'Apagar currículo',
                message:     'Apagar o currículo "' + label + '"? Essa ação não pode ser desfeita.',
                confirmText: 'Apagar',
                cancelText:  'Cancelar',
                danger:      true,
            });
            if (!ok) return;
            try {
                var resp = await fetch('/curriculos/' + id, { method: 'DELETE' });
                if (!resp.ok) throw new Error();
                var card = container.querySelector('[data-id="' + id + '"].curriculo-card');
                if (card) card.remove();
                if (!container.querySelector('.curriculo-card')) renderEmpty();
            } catch {
                window.alert('Não foi possível apagar o currículo.');
            }
        }
    });

    // ── Carga inicial ───────────────────────────────────────────────────
    async function load() {
        try {
            var resp = await fetch('/curriculos/lista');
            var data = await resp.json();
            if (!resp.ok) throw new Error(data.error || 'Erro');
            renderList(data.curriculos);
        } catch (err) {
            container.innerHTML =
                '<p style="color:var(--color-error,#e05252);padding:24px">Erro ao carregar: ' + esc(err.message) + '</p>';
        }
    }

    load();
})();
