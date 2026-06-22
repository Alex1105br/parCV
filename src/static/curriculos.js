(function () {
    'use strict';

    var container = document.getElementById('curriculos-container');

    // ── Paleta de cores ──────────────────────────────────────────────────
    // Carregada do backend (fonte única de verdade) para garantir que o
    // front-end nunca ofereça uma cor que o servidor não aceitaria.
    var CORES = [];
    var COR_PADRAO = '#6366f1';

    async function carregarCores() {
        try {
            var resp = await fetch('/curriculos/cores');
            var data = await resp.json();
            if (resp.ok && Array.isArray(data.cores) && data.cores.length) {
                CORES = data.cores;
                COR_PADRAO = data.cor_padrao || CORES[0];
            }
        } catch (err) {
            // Mantém fallback vazio — o popover simplesmente não abrirá
            // até a próxima tentativa de carregamento da lista.
        }
    }

    function hexToRgba(hex, alpha) {
        var h = hex.replace('#', '');
        var r = parseInt(h.substring(0, 2), 16);
        var g = parseInt(h.substring(2, 4), 16);
        var b = parseInt(h.substring(4, 6), 16);
        return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
    }

    // Aplica a cor escolhida nas variáveis CSS do badge da label de um card
    function aplicarCorLabel(labelEl, cor) {
        cor = cor || COR_PADRAO;
        labelEl.style.setProperty('--cor-label', cor);
        labelEl.style.setProperty('--cor-label-bg', hexToRgba(cor, 0.15));
        labelEl.style.setProperty('--cor-label-border', hexToRgba(cor, 0.3));
    }

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
            var cor = c.cor || COR_PADRAO;
            html +=
                '<li class="curriculo-card" data-id="' + esc(c.id) + '">' +
                    '<div class="curriculo-card__icon"><i data-lucide="file-text"></i></div>' +
                    '<div class="curriculo-card__body">' +
                        '<div class="curriculo-card__top">' +
                            '<button type="button" class="curriculo-color-btn" data-action="cor" data-id="' + esc(c.id) + '" data-cor="' + esc(cor) + '" style="--cor-label:' + esc(cor) + '" title="Alterar cor da label" aria-label="Alterar cor da label"></button>' +
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

        // Aplica a cor salva de cada label (badge)
        container.querySelectorAll('.curriculo-label').forEach(function (labelEl) {
            var card = labelEl.closest('.curriculo-card');
            var colorBtn = card ? card.querySelector('.curriculo-color-btn') : null;
            aplicarCorLabel(labelEl, colorBtn ? colorBtn.dataset.cor : COR_PADRAO);
        });

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

    // ── Popover de seleção de cor ────────────────────────────────────────
    var popoverAtual = null;

    function closeColorPopover() {
        if (popoverAtual) {
            popoverAtual.remove();
            popoverAtual = null;
            document.removeEventListener('click', onDocClickClosePopover, true);
            document.removeEventListener('keydown', onEscClosePopover);
        }
    }

    function onDocClickClosePopover(e) {
        if (popoverAtual && !popoverAtual.contains(e.target) && e.target.dataset.action !== 'cor') {
            closeColorPopover();
        }
    }

    function onEscClosePopover(e) {
        if (e.key === 'Escape') closeColorPopover();
    }

    function openColorPopover(btn) {
        closeColorPopover();
        if (!CORES.length) return;

        var id = btn.dataset.id;
        var corAtual = btn.dataset.cor || COR_PADRAO;

        var pop = document.createElement('div');
        pop.className = 'curriculo-color-popover';
        pop.innerHTML = CORES.map(function (cor) {
            var ativa = cor.toLowerCase() === corAtual.toLowerCase();
            return '<button type="button" class="curriculo-color-swatch' +
                (ativa ? ' curriculo-color-swatch--active' : '') +
                '" style="background:' + esc(cor) + '" data-cor="' + esc(cor) + '" ' +
                'title="' + esc(cor) + '" aria-label="Usar cor ' + esc(cor) + '"></button>';
        }).join('');

        document.body.appendChild(pop);
        popoverAtual = pop;

        // Posiciona o popover abaixo do botão (ajustado para a viewport)
        var rect = btn.getBoundingClientRect();
        var popRect = pop.getBoundingClientRect();
        var top = window.scrollY + rect.bottom + 6;
        var left = window.scrollX + rect.left;
        if (left + popRect.width > window.innerWidth - 8) {
            left = window.innerWidth - popRect.width - 8;
        }
        pop.style.position = 'absolute';
        pop.style.top = top + 'px';
        pop.style.left = left + 'px';

        pop.querySelectorAll('.curriculo-color-swatch').forEach(function (sw) {
            sw.addEventListener('click', function () {
                var novaCor = sw.dataset.cor;
                closeColorPopover();
                if (novaCor.toLowerCase() === corAtual.toLowerCase()) return;
                saveCor(id, novaCor, corAtual);
            });
        });

        setTimeout(function () {
            document.addEventListener('click', onDocClickClosePopover, true);
            document.addEventListener('keydown', onEscClosePopover);
        }, 0);
    }

    async function saveCor(id, novaCor, corAnterior) {
        var card = container.querySelector('.curriculo-card[data-id="' + id + '"]');
        var colorBtn = card ? card.querySelector('.curriculo-color-btn') : null;
        var labelEl = card ? card.querySelector('.curriculo-label') : null;

        // Atualização otimista — aplica antes de confirmar com o servidor
        if (colorBtn) {
            colorBtn.dataset.cor = novaCor;
            colorBtn.style.setProperty('--cor-label', novaCor);
        }
        if (labelEl) aplicarCorLabel(labelEl, novaCor);

        try {
            var resp = await fetch('/curriculos/' + id + '/cor', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cor: novaCor }),
            });
            var data = await resp.json();
            if (!resp.ok) throw new Error(data.error || 'Erro ao salvar cor');
        } catch (err) {
            // Reverte em caso de falha
            if (colorBtn) {
                colorBtn.dataset.cor = corAnterior;
                colorBtn.style.setProperty('--cor-label', corAnterior);
            }
            if (labelEl) aplicarCorLabel(labelEl, corAnterior);
            window.alert('Não foi possível salvar a cor: ' + err.message);
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

        if (action === 'cor') {
            openColorPopover(btn);
            return;
        }

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
            var coresPromise = carregarCores();
            var resp = await fetch('/curriculos/lista');
            var data = await resp.json();
            await coresPromise;
            if (!resp.ok) throw new Error(data.error || 'Erro');
            renderList(data.curriculos);
        } catch (err) {
            container.innerHTML =
                '<p style="color:var(--color-error,#e05252);padding:24px">Erro ao carregar: ' + esc(err.message) + '</p>';
        }
    }

    load();
})();