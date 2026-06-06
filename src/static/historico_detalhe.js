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

    function scoreNumClass(score) {
        if (score > 75) return 'detalhe__score-num--high';
        if (score > 50) return 'detalhe__score-num--mid';
        return 'detalhe__score-num--low';
    }

    function renderDetalhe(data) {
        var container = document.getElementById('page-content');

        var criterios = data.criterios || {};
        var scoreClass = scoreNumClass(data.score_total);

        var sidebar =
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

        var criteriosHtml =
            '<h3>Critérios</h3>' +
            '<ul class="criterios-list">' +
                '<li><span class="criterio-icon" data-tooltip="Formatação e organização do documento"><i data-lucide="info"></i></span><strong>Estrutura:</strong> ' + escapeHtml(criterios.estrutura) + '/15</li>' +
                '<li><span class="criterio-icon" data-tooltip="Qualidade da escrita e objetividade"><i data-lucide="info"></i></span><strong>Clareza:</strong> ' + escapeHtml(criterios.clareza) + '/15</li>' +
                '<li><span class="criterio-icon" data-tooltip="Relevância e descrição de cargos"><i data-lucide="info"></i></span><strong>Experiência:</strong> ' + escapeHtml(criterios.experiencia) + '/20</li>' +
                '<li><span class="criterio-icon" data-tooltip="Termos que sistemas ATS buscam"><i data-lucide="info"></i></span><strong>Palavras-chave:</strong> ' + escapeHtml(criterios.palavras_chave) + '/20</li>' +
                '<li><span class="criterio-icon" data-tooltip="Competências técnicas listadas"><i data-lucide="info"></i></span><strong>Skills:</strong> ' + escapeHtml(criterios.skills) + '/15</li>' +
                '<li><span class="criterio-icon" data-tooltip="Aderência à vaga descrita"><i data-lucide="info"></i></span><strong>Compatibilidade:</strong> ' + escapeHtml(criterios.compatibilidade) + '/15</li>' +
            '</ul>';

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
                    criteriosHtml + pontosHtml + palavrasHtml + certsHtml +
                '</section>' +
            '</div>';

        if (window.lucide) lucide.createIcons({ nodes: [container] });
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

    load();
})();
