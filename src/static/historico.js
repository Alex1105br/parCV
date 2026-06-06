(function () {
    'use strict';

    var currentPage = 1;
    var totalPages = 1;
    var totalCount = 0;

    function scoreClass(score) {
        if (score > 75) return 'score-badge--high';
        if (score > 50) return 'score-badge--mid';
        return 'score-badge--low';
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
            var vagaHtml = a.vaga
                ? '<span class="analise-card__vaga">' + escapeHtml(a.vaga.slice(0, 80)) + (a.vaga.length > 80 ? '…' : '') + '</span>'
                : '<span class="analise-card__vaga analise-card__vaga--empty">Sem descrição de vaga</span>';

            listHtml +=
                '<a class="analise-card" href="/historico/' + escapeHtml(a.id) + '">' +
                    '<div class="score-badge ' + cls + '">' + a.score_total + '</div>' +
                    '<div class="analise-card__body">' +
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

        var btnPrev = document.getElementById('btn-prev');
        var btnNext = document.getElementById('btn-next');
        if (btnPrev) btnPrev.addEventListener('click', function () { loadPage(currentPage - 1); });
        if (btnNext) btnNext.addEventListener('click', function () { loadPage(currentPage + 1); });
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
