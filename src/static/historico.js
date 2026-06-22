(function () {
    'use strict';

    // ===== Helpers compartilhados entre as colunas Análises/Entrevistas =====

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

    var COR_PADRAO_CURRICULO = '#6366f1';

    function hexToRgba(hex, alpha) {
        var h = (hex || COR_PADRAO_CURRICULO).replace('#', '');
        var r = parseInt(h.substring(0, 2), 16);
        var g = parseInt(h.substring(2, 4), 16);
        var b = parseInt(h.substring(4, 6), 16);
        return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
    }

    // Monta a badge de currículo (label + cor escolhida pelo usuário em
    // /curriculos) usada nos cards de Análises e Entrevistas. Mantém o
    // roxo padrão da marca quando nenhuma cor foi definida.
    function curriculoBadgeHtml(label, cor) {
        if (!label) return '';
        var corFinal = cor || COR_PADRAO_CURRICULO;
        var style = '--cor-label:' + corFinal +
            ';--cor-label-bg:' + hexToRgba(corFinal, 0.1) +
            ';--cor-label-border:' + hexToRgba(corFinal, 0.25);
        return '<span class="historico-curriculo-badge" style="' + escapeHtml(style) + '">' +
            '<i data-lucide="file-text"></i>' + escapeHtml(label) +
            '</span>';
    }

    var STATUS_LABELS = {
        em_planejamento: 'Em planejamento',
        em_andamento: 'Em andamento',
        concluida: 'Concluída'
    };

    var STATUS_CLASSES = {
        em_planejamento: 'status-pill--neutro',
        em_andamento: 'status-pill--andamento',
        concluida: 'status-pill--concluida'
    };

    // ===========================================================================
    // Coluna "Análises" (GET /analises, PATCH /analises/<id>/titulo, DELETE /analises/<id>)
    // ===========================================================================
    (function () {
        var currentPage = 1;

        function renderList(data) {
            var container = document.getElementById('list-container-analises');

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

            var listHtml = '<div class="analise-list">';
            data.analises.forEach(function (a) {
                var cls = scoreClass(a.score_total);
                var titulo = a.titulo || 'Análise sem título';
                var vagaHtml = a.vaga
                    ? '<span class="analise-card__vaga">' + escapeHtml(a.vaga.slice(0, 80)) + (a.vaga.length > 80 ? '…' : '') + '</span>'
                    : '<span class="analise-card__vaga analise-card__vaga--empty">Sem descrição de vaga</span>';
                var curriculoHtml = curriculoBadgeHtml(a.curriculo_label, a.curriculo_cor);

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
                            '<div class="analise-card__meta-row">' +
                                curriculoHtml +
                                '<span class="analise-card__date">' + formatDate(a.criado_em) + '</span>' +
                            '</div>' +
                        '</div>' +
                        '<i data-lucide="chevron-right" class="analise-card__arrow"></i>' +
                    '</a>';
            });
            listHtml += '</div>';

            if (data.pages > 1) {
                listHtml +=
                    '<div class="pagination">' +
                        '<button class="pagination__btn" id="btn-prev-analises" ' + (data.page <= 1 ? 'disabled' : '') + '>' +
                            '<i data-lucide="chevron-left"></i> Anterior' +
                        '</button>' +
                        '<span class="pagination__info">Página ' + data.page + ' de ' + data.pages + '</span>' +
                        '<button class="pagination__btn" id="btn-next-analises" ' + (data.page >= data.pages ? 'disabled' : '') + '>' +
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

            var btnPrev = document.getElementById('btn-prev-analises');
            var btnNext = document.getElementById('btn-next-analises');
            if (btnPrev) btnPrev.addEventListener('click', function () { loadPage(currentPage - 1); });
            if (btnNext) btnNext.addEventListener('click', function () { loadPage(currentPage + 1); });
        }

        // ===== Renomear análise =====
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
                    var restantes = document.querySelectorAll('#list-container-analises .analise-card').length - 1;
                    var pagina = (restantes <= 0 && currentPage > 1) ? currentPage - 1 : currentPage;
                    loadPage(pagina);
                })
                .catch(function () {
                    card.classList.remove('analise-card--deleting');
                    window.alert('Não foi possível apagar a análise. Tente novamente.');
                });
        }

        function renderError(msg) {
            var container = document.getElementById('list-container-analises');
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
                renderError('Falha ao carregar análises: ' + err.message);
            }
        }

        loadPage(1);
    })();

    // ===========================================================================
    // Coluna "Entrevistas" (GET /entrevista/lista, PATCH /entrevista/<id>/titulo,
    // DELETE /entrevista/<id>) — mesmo padrão usado acima para "Análises".
    // ===========================================================================
    (function () {
        var currentPage = 1;

        function destinoEntrevista(e) {
            return e.status === 'concluida'
                ? '/entrevista/' + encodeURIComponent(e.id) + '/relatorio'
                : '/entrevista/' + encodeURIComponent(e.id) + '/executar';
        }

        function renderList(data) {
            var container = document.getElementById('list-container-entrevistas');

            if (!data.entrevistas || data.entrevistas.length === 0) {
                container.innerHTML =
                    '<div class="empty-state">' +
                        '<i data-lucide="inbox"></i>' +
                        '<p class="empty-state__title">Nenhuma entrevista encontrada</p>' +
                        '<p class="empty-state__text">Faça sua primeira simulação de entrevista.</p>' +
                        '<a href="/entrevista" class="btn btn--primary"><i data-lucide="user-check"></i> Simular entrevista</a>' +
                    '</div>';
                if (window.lucide) lucide.createIcons({ nodes: [container] });
                return;
            }

            var listHtml = '<div class="analise-list">';
            data.entrevistas.forEach(function (e) {
                var titulo = e.titulo || 'Entrevista sem título';
                var vagaHtml = e.vaga_descricao
                    ? '<span class="analise-card__vaga">' + escapeHtml(e.vaga_descricao.slice(0, 80)) + (e.vaga_descricao.length > 80 ? '…' : '') + '</span>'
                    : '<span class="analise-card__vaga analise-card__vaga--empty">Sem descrição de vaga</span>';
                var curriculoHtml = curriculoBadgeHtml(e.curriculo_label, e.curriculo_cor);

                var indicadorHtml;
                if (e.status === 'concluida' && e.score_geral != null) {
                    var cls = scoreClass(e.score_geral * 10);
                    indicadorHtml = '<div class="score-badge ' + cls + ' score-badge--decimal">' + e.score_geral.toFixed(1) + '</div>';
                } else {
                    indicadorHtml =
                        '<div class="status-pill ' + (STATUS_CLASSES[e.status] || 'status-pill--neutro') + '">' +
                            (STATUS_LABELS[e.status] || e.status) +
                        '</div>';
                }

                listHtml +=
                    '<a class="analise-card" href="' + destinoEntrevista(e) + '" data-eid="' + escapeHtml(e.id) + '">' +
                        indicadorHtml +
                        '<div class="analise-card__body">' +
                            '<div class="analise-card__title-row">' +
                                '<span class="analise-card__title">' + escapeHtml(titulo) + '</span>' +
                                '<button type="button" class="analise-card__edit-btn" aria-label="Renomear entrevista" title="Renomear">' +
                                    '<i data-lucide="pencil"></i>' +
                                '</button>' +
                                '<button type="button" class="analise-card__delete-btn" aria-label="Apagar entrevista" title="Apagar">' +
                                    '<i data-lucide="trash-2"></i>' +
                                '</button>' +
                            '</div>' +
                            vagaHtml +
                            '<div class="analise-card__meta-row">' +
                                curriculoHtml +
                                '<span class="analise-card__date">' + formatDate(e.criado_em) + '</span>' +
                            '</div>' +
                        '</div>' +
                        '<i data-lucide="chevron-right" class="analise-card__arrow"></i>' +
                    '</a>';
            });
            listHtml += '</div>';

            if (data.pages > 1) {
                listHtml +=
                    '<div class="pagination">' +
                        '<button class="pagination__btn" id="btn-prev-entrevistas" ' + (data.page <= 1 ? 'disabled' : '') + '>' +
                            '<i data-lucide="chevron-left"></i> Anterior' +
                        '</button>' +
                        '<span class="pagination__info">Página ' + data.page + ' de ' + data.pages + '</span>' +
                        '<button class="pagination__btn" id="btn-next-entrevistas" ' + (data.page >= data.pages ? 'disabled' : '') + '>' +
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
                    startInlineRename(card, card.dataset.eid, titleEl);
                });
            });

            container.querySelectorAll('.analise-card__delete-btn').forEach(function (btn) {
                btn.addEventListener('click', function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    var card = btn.closest('.analise-card');
                    deletarEntrevista(card, card.dataset.eid);
                });
            });

            var btnPrev = document.getElementById('btn-prev-entrevistas');
            var btnNext = document.getElementById('btn-next-entrevistas');
            if (btnPrev) btnPrev.addEventListener('click', function () { loadPage(currentPage - 1); });
            if (btnNext) btnNext.addEventListener('click', function () { loadPage(currentPage + 1); });
        }

        // ===== Renomear entrevista (mesmo padrão usado em "Análises") =====
        function startInlineRename(card, eid, titleEl) {
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
                    fetch('/entrevista/' + encodeURIComponent(eid) + '/titulo', {
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

        // ===== Apagar entrevista =====
        async function deletarEntrevista(card, eid) {
            var titulo = card.querySelector('.analise-card__title').textContent;
            var confirmado = await confirmModal({
                title: 'Apagar entrevista',
                message: 'Apagar a entrevista "' + titulo + '"? Essa ação não pode ser desfeita.',
                confirmText: 'Apagar',
                cancelText: 'Cancelar',
                danger: true
            });
            if (!confirmado) return;

            card.classList.add('analise-card--deleting');

            fetch('/entrevista/' + encodeURIComponent(eid), { method: 'DELETE' })
                .then(function (resp) {
                    if (!resp.ok) throw new Error('Erro ' + resp.status);
                    return resp.json();
                })
                .then(function () {
                    var restantes = document.querySelectorAll('#list-container-entrevistas .analise-card').length - 1;
                    var pagina = (restantes <= 0 && currentPage > 1) ? currentPage - 1 : currentPage;
                    loadPage(pagina);
                })
                .catch(function () {
                    card.classList.remove('analise-card--deleting');
                    window.alert('Não foi possível apagar a entrevista. Tente novamente.');
                });
        }

        function renderError(msg) {
            var container = document.getElementById('list-container-entrevistas');
            container.innerHTML = '<p class="error" style="padding:24px">' + escapeHtml(msg) + '</p>';
        }

        async function loadPage(page) {
            currentPage = page;
            try {
                var resp = await fetch('/entrevista/lista?page=' + page + '&per_page=20');
                if (!resp.ok) throw new Error('Erro ' + resp.status);
                var data = await resp.json();
                renderList(data);
            } catch (err) {
                renderError('Falha ao carregar entrevistas: ' + err.message);
            }
        }

        loadPage(1);
    })();
})();