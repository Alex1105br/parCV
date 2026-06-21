(function () {
    'use strict';

    var currentPage = 1;
    var totalPages = 1;
    var totalCount = 0;

    // Mesma escala de cor do relatório de /entrevista (lá em 0-10, aqui em 0-100)
    function scoreClass(score) {
        if (score >= 90) return 'score-badge--excelente';
        if (score >= 70) return 'score-badge--bom';
        if (score >= 50) return 'score-badge--regular';
        if (score >= 30) return 'score-badge--ruim';
        return 'score-badge--pessimo';
    }

    function formatDate(iso) {
        var d = new Date(iso);
        return d.toLocaleDateString('pt-BR', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    }

    function escapeHtml(s) {
        if (s == null) return '';
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function renderList(data) {
        var container = document.getElementById('list-container');

        if (!data.analises || data.analises.length === 0) {
            container.innerHTML =
                '<div class="empty-state">' +
                    '<i data-lucide="inbox"></i>' +
                    '<p class="empty-state__title">Nenhuma análise encontrada</p>' +
                    '<p class="empty-state__text">Faça sua primeira análise de currículo.</p>' +
                    '<a href="/analisar" class="btn btn--primary"><i data-lucide="scan-search"></i> Analisar currículo</a>' +
                '</div>';
            if (window.lucide) lucide.createIcons({ nodes: [container] });
            return;
        }

        totalPages = data.pages;
        totalCount = data.total;

        var listHtml = '<div class="analise-list">';
        data.analises.forEach(function (a) {
            var cls = scoreClass(a.score_total);
            var titulo = a.titulo || 'Análise sem título';
            var vagaHtml = a.vaga
                ? '<span class="analise-card__vaga">' + escapeHtml(a.vaga.slice(0, 80)) + (a.vaga.length > 80 ? '…' : '') + '</span>'
                : '<span class="analise-card__vaga analise-card__vaga--empty">Sem descrição de vaga</span>';

            listHtml +=
                '<a class="analise-card" href="/historico/' + escapeHtml(a.id) + '" data-aid="' + escapeHtml(a.id) + '">' +
                    '<div class="score-badge ' + cls + '">' + a.score_total + '</div>' +
                    '<div class="analise-card__body">' +
                        '<div class="analise-card__title-row">' +
                            '<span class="analise-card__title">' + escapeHtml(titulo) + '</span>' +
                            '<button type="button" class="analise-card__edit-btn" aria-label="Renomear análise" title="Renomear">' +
                                '<i data-lucide="pencil"></i>' +
                            '</button>' +
                            '<button type="button" class="analise-card__delete-btn" aria-label="Apagar análise" title="Apagar">' +
                                '<i data-lucide="trash-2"></i>' +
                            '</button>' +
                        '</div>' +
                        vagaHtml +
                        '<span class="analise-card__date">' + formatDate(a.criado_em) + '</span>' +
                    '</div>' +
                    '<i data-lucide="chevron-right" class="analise-card__arrow"></i>' +
                '</a>';
        });
        listHtml += '</div>';

        if (data.pages > 1) {
            listHtml +=
                '<div class="pagination">' +
                    '<button class="pagination__btn" id="btn-prev" ' + (data.page <= 1 ? 'disabled' : '') + '>' +
                        '<i data-lucide="chevron-left"></i> Anterior' +
                    '</button>' +
                    '<span class="pagination__info">Página ' + data.page + ' de ' + data.pages + '</span>' +
                    '<button class="pagination__btn" id="btn-next" ' + (data.page >= data.pages ? 'disabled' : '') + '>' +
                        'Próxima <i data-lucide="chevron-right"></i>' +
                    '</button>' +
                '</div>';
        }

        container.innerHTML = listHtml;
        if (window.lucide) lucide.createIcons({ nodes: [container] });

        container.querySelectorAll('.analise-card__edit-btn').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                var card = btn.closest('.analise-card');
                var titleEl = card.querySelector('.analise-card__title');
                startInlineRename(card, card.dataset.aid, titleEl);
            });
        });

        container.querySelectorAll('.analise-card__delete-btn').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                var card = btn.closest('.analise-card');
                deletarAnalise(card, card.dataset.aid);
            });
        });

        var btnPrev = document.getElementById('btn-prev');
        var btnNext = document.getElementById('btn-next');
        if (btnPrev) btnPrev.addEventListener('click', function () { loadPage(currentPage - 1); });
        if (btnNext) btnNext.addEventListener('click', function () { loadPage(currentPage + 1); });
    }

    // ===== Renomear análise (mesmo padrão usado em /chat) =====
    function startInlineRename(card, aid, titleEl) {
        if (card.querySelector('.analise-card__rename-input')) return;
        var currentTitle = titleEl.textContent;
        var input = document.createElement('input');
        input.type = 'text';
        input.value = currentTitle;
        input.className = 'analise-card__rename-input';
        var titleRow = card.querySelector('.analise-card__title-row');
        titleRow.appendChild(input);
        card.classList.add('analise-card--editing');
        input.focus();
        input.select();

        var done = false;

        function commit() {
            if (done) return;
            done = true;
            var novoTitulo = input.value.trim();
            input.remove();
            card.classList.remove('analise-card--editing');
            if (novoTitulo && novoTitulo !== currentTitle) {
                titleEl.textContent = novoTitulo;
                fetch('/analises/' + encodeURIComponent(aid) + '/titulo', {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ titulo: novoTitulo })
                }).catch(function () {});
            }
        }

        function cancel() {
            if (done) return;
            done = true;
            input.remove();
            card.classList.remove('analise-card--editing');
        }

        input.addEventListener('click', function (e) { e.stopPropagation(); });
        input.addEventListener('mousedown', function (e) { e.stopPropagation(); });
        input.addEventListener('keydown', function (e) {
            e.stopPropagation();
            if (e.key === 'Enter') commit();
            else if (e.key === 'Escape') cancel();
        });
        input.addEventListener('blur', commit);
    }

    // ===== Apagar análise =====
    async function deletarAnalise(card, aid) {
        var titulo = card.querySelector('.analise-card__title').textContent;
        var confirmado = await confirmModal({
            title: 'Apagar análise',
            message: 'Apagar a análise "' + titulo + '"? Essa ação não pode ser desfeita.',
            confirmText: 'Apagar',
            cancelText: 'Cancelar',
            danger: true
        });
        if (!confirmado) return;

        card.classList.add('analise-card--deleting');

        fetch('/analises/' + encodeURIComponent(aid), { method: 'DELETE' })
            .then(function (resp) {
                if (!resp.ok) throw new Error('Erro ' + resp.status);
                return resp.json();
            })
            .then(function () {
                // Se a página atual ficar vazia após remover o item e não for a
                // primeira página, volta uma página; senão só recarrega a atual.
                var restantes = document.querySelectorAll('.analise-card').length - 1;
                var pagina = (restantes <= 0 && currentPage > 1) ? currentPage - 1 : currentPage;
                loadPage(pagina);
            })
            .catch(function () {
                card.classList.remove('analise-card--deleting');
                window.alert('Não foi possível apagar a análise. Tente novamente.');
            });
    }

    function renderError(msg) {
        var container = document.getElementById('list-container');
        container.innerHTML = '<p class="error" style="padding:24px">' + escapeHtml(msg) + '</p>';
    }

    async function loadPage(page) {
        currentPage = page;
        try {
            var resp = await fetch('/analises?page=' + page + '&per_page=20');
            if (!resp.ok) throw new Error('Erro ' + resp.status);
            var data = await resp.json();
            renderList(data);
        } catch (err) {
            renderError('Falha ao carregar histórico: ' + err.message);
        }
    }

    loadPage(1);
})();