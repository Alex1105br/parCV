(function () {
    'use strict';

    var analiseId = window.ANALISE_ID;

    function escapeHtml(s) {
        if (s == null) return '';
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function formatDate(iso) {
        var d = new Date(iso);
        return d.toLocaleDateString('pt-BR', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    }

    // Mesma escala de cor do relatório de /entrevista (lá em 0-10, aqui em 0-100)
    function scoreNumClass(score) {
        if (score >= 90) return 'detalhe__score-num--excelente';
        if (score >= 70) return 'detalhe__score-num--bom';
        if (score >= 50) return 'detalhe__score-num--regular';
        if (score >= 30) return 'detalhe__score-num--ruim';
        return 'detalhe__score-num--pessimo';
    }

    // Compat: criterios antigos eram número puro, novos vêm como
    // {nota, motivo} — ver build_prompt_ats em services/prompts.py
    function criterioNota(c) {
        return (c && typeof c === 'object') ? c.nota : c;
    }
    function criterioMotivo(c, fallback) {
        return (c && typeof c === 'object' && c.motivo) ? c.motivo : fallback;
    }
    function criterioLista(c, campo) {
        return (c && typeof c === 'object' && Array.isArray(c[campo])) ? c[campo] : [];
    }
    function nivelLabel(nivel) {
        var map = { baixa: 'Baixa', media: 'Média', alta: 'Alta' };
        return map[nivel] || 'Média';
    }
    function renderVeredito(veredito) {
        if (!veredito) return '';
        var nivel = veredito.nivel_aderencia || 'media';
        return '<h3>Compatibilidade com a vaga</h3>' +
            '<div class="veredito-box veredito-box--' + escapeHtml(nivel) + '">' +
                '<span class="veredito-box__nivel">Aderência ' + escapeHtml(nivelLabel(nivel)) + '</span>' +
                '<p class="veredito-box__resumo">' + escapeHtml(veredito.resumo || '') + '</p>' +
                (veredito.vagas_recomendadas && veredito.vagas_recomendadas.length ?
                    '<p class="veredito-box__label">Vagas com mais chance pra você:</p>' +
                    '<div class="tags-list">' + veredito.vagas_recomendadas.map(function (v) {
                        return '<span class="tag tag--positive">' + escapeHtml(v) + '</span>';
                    }).join('') + '</div>'
                : '') +
                (veredito.motivo_recomendacao ?
                    '<p class="veredito-box__motivo">' + escapeHtml(veredito.motivo_recomendacao) + '</p>'
                : '') +
            '</div>';
    }

    function renderCriterioAccordion(id, titulo, criterio, maxNota, fallbackMotivo) {
        var nota = criterioNota(criterio);
        var motivo = criterioMotivo(criterio, fallbackMotivo);
        var fortes = criterioLista(criterio, 'pontos_fortes');
        var fracos = criterioLista(criterio, 'pontos_fracos');

        var fortesHtml = fortes.length
            ? '<ul class="criterio-acc__list criterio-acc__list--fortes">' +
                fortes.map(function (p) { return '<li>' + escapeHtml(p) + '</li>'; }).join('') +
              '</ul>'
            : '<p class="criterio-acc__empty">Nenhum ponto forte específico identificado.</p>';

        var fracosHtml = fracos.length
            ? '<ul class="criterio-acc__list criterio-acc__list--fracos">' +
                fracos.map(function (p) { return '<li>' + escapeHtml(p) + '</li>'; }).join('') +
              '</ul>'
            : '<p class="criterio-acc__empty">Nenhum ponto fraco específico identificado.</p>';

        return (
            '<div class="criterio-acc" id="criterio-acc-' + id + '">' +
                '<button type="button" class="criterio-acc__header" aria-expanded="false" aria-controls="criterio-acc-body-' + id + '">' +
                    '<span class="criterio-acc__title">' + escapeHtml(titulo) + '</span>' +
                    '<span class="criterio-acc__right">' +
                        '<span class="criterio-acc__nota">' + escapeHtml(nota) + '/' + maxNota + '</span>' +
                        '<i data-lucide="chevron-down" class="criterio-acc__chevron"></i>' +
                    '</span>' +
                '</button>' +
                '<div class="criterio-acc__body hidden" id="criterio-acc-body-' + id + '">' +
                    (motivo ? '<p class="criterio-acc__motivo">' + escapeHtml(motivo) + '</p>' : '') +
                    '<div class="criterio-acc__section">' +
                        '<h4 class="criterio-acc__heading criterio-acc__heading--fortes"><i data-lucide="thumbs-up"></i> Pontos fortes</h4>' +
                        fortesHtml +
                    '</div>' +
                    '<div class="criterio-acc__section">' +
                        '<h4 class="criterio-acc__heading criterio-acc__heading--fracos"><i data-lucide="thumbs-down"></i> Pontos fracos</h4>' +
                        fracosHtml +
                    '</div>' +
                '</div>' +
            '</div>'
        );
    }

    function setupCriterioAccordions(container) {
        container.querySelectorAll('.criterio-acc__header').forEach(function (header) {
            header.addEventListener('click', function () {
                var body = document.getElementById(this.getAttribute('aria-controls'));
                var expanded = this.getAttribute('aria-expanded') === 'true';
                this.setAttribute('aria-expanded', String(!expanded));
                if (body) body.classList.toggle('hidden', expanded);
                this.closest('.criterio-acc').classList.toggle('criterio-acc--open', !expanded);
            });
        });
    }

    function renderDetalhe(data) {
        var container = document.getElementById('page-content');

        var criterios = data.criterios || {};
        var scoreClass = scoreNumClass(data.score_total);

        var sidebar =
            '<div class="detalhe__titulo-wrap">' +
                '<span class="detalhe__titulo" id="detalhe-titulo">' + escapeHtml(data.titulo || 'Análise sem título') + '</span>' +
                '<button type="button" class="detalhe__titulo-edit-btn" id="detalhe-titulo-edit" aria-label="Renomear análise" title="Renomear">' +
                    '<i data-lucide="pencil"></i>' +
                '</button>' +
            '</div>' +
            '<div class="detalhe__score-wrap">' +
                '<span class="detalhe__score-label">Score ATS</span>' +
                '<span class="detalhe__score-num ' + scoreClass + '">' + data.score_total + '</span>' +
                '<span class="detalhe__score-sub">de 100 pontos</span>' +
            '</div>' +
            '<div class="detalhe__meta">' +
                '<p class="detalhe__meta-label">Data</p>' +
                '<p class="detalhe__meta-value">' + formatDate(data.criado_em) + '</p>' +
            '</div>' +
            (data.vaga
                ? '<div class="detalhe__meta">' +
                    '<p class="detalhe__meta-label">Vaga</p>' +
                    '<p class="detalhe__meta-value">' + escapeHtml(data.vaga) + '</p>' +
                  '</div>'
                : '');

        var vereditoHtml = renderVeredito(data.veredito);

        var criteriosHtml =
            '<h3>Critérios</h3>' +
            '<div class="criterios-list">' +
                renderCriterioAccordion('estrutura', 'Estrutura', criterios.estrutura, 15, 'Formatação e organização do documento') +
                renderCriterioAccordion('clareza', 'Clareza', criterios.clareza, 15, 'Qualidade da escrita e objetividade') +
                renderCriterioAccordion('experiencia', 'Experiência', criterios.experiencia, 20, 'Relevância e descrição de cargos') +
                renderCriterioAccordion('palavras_chave', 'Palavras-chave', criterios.palavras_chave, 20, 'Termos que sistemas ATS buscam') +
                renderCriterioAccordion('skills', 'Skills', criterios.skills, 15, 'Competências técnicas listadas') +
                renderCriterioAccordion('compatibilidade', 'Compatibilidade', criterios.compatibilidade, 15, 'Aderência à vaga descrita') +
            '</div>';

        var pontosHtml =
            '<h3>Pontos fortes</h3>' +
            '<ul>' + (data.pontos_fortes || []).map(function (p) { return '<li>' + escapeHtml(p) + '</li>'; }).join('') + '</ul>' +
            '<h3>Pontos fracos</h3>' +
            '<ul>' + (data.pontos_fracos || []).map(function (p) { return '<li>' + escapeHtml(p) + '</li>'; }).join('') + '</ul>' +
            '<h3>Sugestões</h3>' +
            '<ul>' + (data.sugestoes || []).map(function (s) { return '<li>' + escapeHtml(s) + '</li>'; }).join('') + '</ul>';

        var palavrasHtml = (data.palavras_chave_faltando && data.palavras_chave_faltando.length)
            ? '<h3>Palavras-chave ausentes</h3>' +
              '<div class="tags-list">' +
              data.palavras_chave_faltando.map(function (k) { return '<span class="tag">' + escapeHtml(k) + '</span>'; }).join('') +
              '</div>'
            : '';

        var certsHtml = (data.certificados_sugeridos && data.certificados_sugeridos.length)
            ? '<h3>Certificados recomendados</h3>' +
              '<div class="cert-list">' +
              data.certificados_sugeridos.map(function (c) {
                  return '<div class="cert-card">' +
                      '<div class="cert-card__info">' +
                          '<span class="cert-card__name">' + escapeHtml(c.nome) + '</span>' +
                          '<span class="cert-card__platform">' + escapeHtml(c.plataforma) + '</span>' +
                      '</div>' +
                      (c.url ? '<a class="cert-card__link" href="' + escapeHtml(c.url) + '" target="_blank" rel="noopener noreferrer"><i data-lucide="external-link"></i> Ver</a>' : '') +
                  '</div>';
              }).join('') +
              '</div>'
            : '';

        container.innerHTML =
            '<div class="detalhe">' +
                '<aside class="detalhe__sidebar">' + sidebar + '</aside>' +
                '<section class="detalhe__content analisar__resultado">' +
                    vereditoHtml + criteriosHtml + pontosHtml + palavrasHtml + certsHtml +
                '</section>' +
            '</div>';

        if (window.lucide) lucide.createIcons({ nodes: [container] });
        setupCriterioAccordions(container);
        setupTituloRename(data.id || analiseId, data.titulo || 'Análise sem título');
    }

    // ===== Renomear análise (mesmo padrão usado em /chat e /historico) =====
    function setupTituloRename(aid, currentTitleInicial) {
        var titleEl = document.getElementById('detalhe-titulo');
        var editBtn = document.getElementById('detalhe-titulo-edit');
        if (!titleEl || !editBtn) return;

        editBtn.addEventListener('click', function () {
            var wrap = titleEl.closest('.detalhe__titulo-wrap');
            if (wrap.querySelector('.detalhe__titulo-rename-input')) return;
            var currentTitle = titleEl.textContent;
            var input = document.createElement('input');
            input.type = 'text';
            input.value = currentTitle;
            input.className = 'detalhe__titulo-rename-input';
            wrap.appendChild(input);
            wrap.classList.add('detalhe__titulo-wrap--editing');
            input.focus();
            input.select();

            var done = false;

            function commit() {
                if (done) return;
                done = true;
                var novoTitulo = input.value.trim();
                input.remove();
                wrap.classList.remove('detalhe__titulo-wrap--editing');
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
                wrap.classList.remove('detalhe__titulo-wrap--editing');
            }

            input.addEventListener('keydown', function (e) {
                if (e.key === 'Enter') commit();
                else if (e.key === 'Escape') cancel();
            });
            input.addEventListener('blur', commit);
        });
    }

    // ===== Apagar análise =====
    function setupDeleteButton() {
        var btn = document.getElementById('btn-apagar-analise');
        if (!btn) return;

        btn.addEventListener('click', async function () {
            var titleEl = document.getElementById('detalhe-titulo');
            var titulo = titleEl ? titleEl.textContent : 'esta análise';
            var confirmado = await confirmModal({
                title: 'Apagar análise',
                message: 'Apagar a análise "' + titulo + '"? Essa ação não pode ser desfeita.',
                confirmText: 'Apagar',
                cancelText: 'Cancelar',
                danger: true
            });
            if (!confirmado) return;

            btn.disabled = true;
            btn.innerHTML = '<i data-lucide="loader"></i> Apagando...';
            if (window.lucide) lucide.createIcons({ nodes: [btn] });

            fetch('/analises/' + encodeURIComponent(analiseId), { method: 'DELETE' })
                .then(function (resp) {
                    if (!resp.ok) throw new Error('Erro ' + resp.status);
                    window.location.href = '/historico';
                })
                .catch(function () {
                    btn.disabled = false;
                    btn.innerHTML = '<i data-lucide="trash-2"></i> Apagar análise';
                    if (window.lucide) lucide.createIcons({ nodes: [btn] });
                    window.alert('Não foi possível apagar a análise. Tente novamente.');
                });
        });
    }

    function renderError(msg) {
        var container = document.getElementById('page-content');
        container.innerHTML = '<p class="error" style="padding:40px 24px">' + escapeHtml(msg) + '</p>';
    }

    async function load() {
        try {
            var resp = await fetch('/analises/' + encodeURIComponent(analiseId));
            if (resp.status === 404) { renderError('Análise não encontrada.'); return; }
            if (!resp.ok) throw new Error('Erro ' + resp.status);
            var data = await resp.json();
            renderDetalhe(data);
        } catch (err) {
            renderError('Falha ao carregar análise: ' + err.message);
        }
    }

    setupDeleteButton();
    load();
})();