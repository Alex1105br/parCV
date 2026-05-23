(function () {
    'use strict';

    const fileInput = document.getElementById('ats-file');
    const vagaInput = document.getElementById('ats-vaga');
    const btnAnalisar = document.getElementById('btn-analisar');
    const loader = document.getElementById('loader');
    const resultado = document.getElementById('resultado');
    const fileDrop = document.getElementById('file-drop');

    var textoOriginal = '';

    // File drop zone interactions
    if (fileDrop) {
        fileDrop.addEventListener('click', function () { fileInput.click(); });

        fileDrop.addEventListener('dragover', function (e) {
            e.preventDefault();
            fileDrop.classList.add('file-drop--active');
        });

        fileDrop.addEventListener('dragleave', function () {
            fileDrop.classList.remove('file-drop--active');
        });

        fileDrop.addEventListener('drop', function (e) {
            e.preventDefault();
            fileDrop.classList.remove('file-drop--active');
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                updateDropLabel();
            }
        });

        fileInput.addEventListener('change', updateDropLabel);
    }

    function updateDropLabel() {
        const textEl = fileDrop.querySelector('.file-drop__text');
        if (fileInput.files.length) {
            textEl.textContent = fileInput.files[0].name;
            fileDrop.classList.add('file-drop--active');
        } else {
            textEl.textContent = 'Arraste ou clique para selecionar';
            fileDrop.classList.remove('file-drop--active');
        }
    }

    btnAnalisar.addEventListener('click', enviarAnalise);

    async function enviarAnalise() {
        if (!fileInput.files.length) {
            alert('Selecione um arquivo');
            return;
        }

        const formData = new FormData();
        formData.append('arquivo', fileInput.files[0]);
        const vaga = vagaInput.value.trim();
        if (vaga) formData.append('vaga', vaga);

        loader.classList.remove('hidden');
        resultado.innerHTML = '';

        try {
            const response = await fetch('/analisar', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            loader.classList.add('hidden');
            textoOriginal = data.texto_original || '';
            mostrarResultado(data);
        } catch (err) {
            loader.classList.add('hidden');
            alert('Erro: ' + err.message);
        }
    }

    function mostrarResultado(data) {
        if (data.error) {
            resultado.innerHTML = '<p class="error">' + escapeHtml(data.error) + '</p>';
            return;
        }

        const score = data.score_total;
        let cor = 'var(--color-danger)';
        if (score > 75) cor = 'var(--color-success)';
        else if (score > 50) cor = 'var(--color-peach)';

        resultado.innerHTML =
            '<div class="score-box" style="border-color:' + cor + '">' +
                '<h2 style="color:' + cor + '">Score ATS: ' + score + '/100</h2>' +
            '</div>' +
            '<h3>Critérios</h3>' +
            '<ul class="criterios-list">' +
                '<li><span class="criterio-icon" data-tooltip="Formata\u00e7\u00e3o e organiza\u00e7\u00e3o do documento"><i data-lucide="info"></i></span><strong>Estrutura:</strong> ' + escapeHtml(data.criterios.estrutura) + '/15</li>' +
                '<li><span class="criterio-icon" data-tooltip="Qualidade da escrita e objetividade"><i data-lucide="info"></i></span><strong>Clareza:</strong> ' + escapeHtml(data.criterios.clareza) + '/15</li>' +
                '<li><span class="criterio-icon" data-tooltip="Relev\u00e2ncia e descri\u00e7\u00e3o de cargos"><i data-lucide="info"></i></span><strong>Experi\u00eancia:</strong> ' + escapeHtml(data.criterios.experiencia) + '/20</li>' +
                '<li><span class="criterio-icon" data-tooltip="Termos que sistemas ATS buscam"><i data-lucide="info"></i></span><strong>Palavras-chave:</strong> ' + escapeHtml(data.criterios.palavras_chave) + '/20</li>' +
                '<li><span class="criterio-icon" data-tooltip="Compet\u00eancias t\u00e9cnicas listadas"><i data-lucide="info"></i></span><strong>Skills:</strong> ' + escapeHtml(data.criterios.skills) + '/15</li>' +
                '<li><span class="criterio-icon" data-tooltip="Ader\u00eancia \u00e0 vaga descrita"><i data-lucide="info"></i></span><strong>Compatibilidade:</strong> ' + escapeHtml(data.criterios.compatibilidade) + '/15</li>' +
            '</ul>' +
            '<h3>Pontos fortes</h3>' +
            '<ul>' + data.pontos_fortes.map(function (p) { return '<li>' + escapeHtml(p) + '</li>'; }).join('') + '</ul>' +
            '<h3>Pontos fracos</h3>' +
            '<ul>' + data.pontos_fracos.map(function (p) { return '<li>' + escapeHtml(p) + '</li>'; }).join('') + '</ul>' +
            '<h3>Sugestões</h3>' +
            '<ul>' + data.sugestoes.map(function (s) { return '<li>' + escapeHtml(s) + '</li>'; }).join('') + '</ul>' +
            (data.palavras_chave_faltando && data.palavras_chave_faltando.length ?
                '<h3>Palavras-chave ausentes</h3>' +
                '<div class="tags-list">' + data.palavras_chave_faltando.map(function (k) { return '<span class="tag">' + escapeHtml(k) + '</span>'; }).join('') + '</div>'
            : '') +
            (data.certificados_sugeridos && data.certificados_sugeridos.length ?
                '<h3>Certificados recomendados</h3>' +
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
            : '') +
            '<div style="margin-top: 20px;">' +
                '<button class="btn btn--optimize" id="btn-otimizar"><i data-lucide="sparkles"></i> Otimizar Currículo</button>' +
            '</div>' +
            '<div id="loader-otimizar" class="loader hidden">' +
                '<span class="loader__spinner"></span>' +
                '<span>Otimizando currículo... (pode levar alguns minutos)</span>' +
            '</div>' +
            '<div id="resultado-otimizado"></div>';

        if (window.lucide) lucide.createIcons({ nodes: [resultado] });
        document.getElementById('btn-otimizar').addEventListener('click', otimizarCurriculo);
    }

    async function otimizarCurriculo() {
        if (!fileInput.files.length) {
            alert('Selecione um arquivo de currículo primeiro e clique em Analisar.');
            return;
        }

        const loaderOtimizar = document.getElementById('loader-otimizar');
        const resultadoOtimizado = document.getElementById('resultado-otimizado');
        const btnOtimizar = document.getElementById('btn-otimizar');

        loaderOtimizar.classList.remove('hidden');
        resultadoOtimizado.innerHTML = '';
        btnOtimizar.disabled = true;

        const formData = new FormData();
        formData.append('arquivo', fileInput.files[0]);
        const vaga = vagaInput.value.trim();
        if (vaga) formData.append('vaga', vaga);

        try {
            const response = await fetch('/otimizar', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            loaderOtimizar.classList.add('hidden');
            btnOtimizar.disabled = false;

            if (data.error) {
                resultadoOtimizado.innerHTML = '<p class="error">' + escapeHtml(data.error) + '</p>';
                return;
            }

            mostrarCurriculoOtimizado(data.curriculo_otimizado, data.melhorias);
        } catch (err) {
            loaderOtimizar.classList.add('hidden');
            btnOtimizar.disabled = false;
            alert('Erro ao otimizar: ' + err.message);
        }
    }

    function mostrarCurriculoOtimizado(curriculo, melhorias) {
        const div = document.getElementById('resultado-otimizado');

        var melhorasHtml = '';
        if (melhorias && melhorias.length) {
            melhorasHtml =
                '<div class="cv-improvements">' +
                    '<strong>Melhorias aplicadas:</strong>' +
                    '<ul>' + melhorias.map(function (m) { return '<li>' + escapeHtml(m) + '</li>'; }).join('') + '</ul>' +
                '</div>';
        }

        div.innerHTML =
            '<hr style="margin: 24px 0; border-color: var(--color-border);">' +
            '<div class="cv-tabs">' +
                '<button class="cv-tab cv-tab--active" data-tab="otimizado"><i data-lucide="sparkles"></i> Otimizado</button>' +
                '<button class="cv-tab" data-tab="comparacao"><i data-lucide="columns-2"></i> Comparação</button>' +
            '</div>' +
            '<div id="cv-panel-otimizado" class="cv-tab-panel">' +
                melhorasHtml +
                '<div class="cv-structured" id="curriculo-text">' + renderStructuredCV(curriculo) + '</div>' +
                '<div style="display: flex; gap: 12px; flex-wrap: wrap;">' +
                    '<button type="button" class="btn btn--primary" id="btn-pdf"><i data-lucide="file-down"></i> Baixar PDF</button>' +
                    '<button type="button" class="btn btn--secondary" id="btn-copiar"><i data-lucide="clipboard"></i> Copiar texto</button>' +
                '</div>' +
            '</div>' +
            '<div id="cv-panel-comparacao" class="cv-tab-panel hidden">' +
                renderComparisonView(textoOriginal, curriculo) +
            '</div>';

        if (window.lucide) lucide.createIcons({ nodes: [div] });

        div.querySelectorAll('.cv-tab').forEach(function (tab) {
            tab.addEventListener('click', function () {
                div.querySelectorAll('.cv-tab').forEach(function (t) { t.classList.remove('cv-tab--active'); });
                tab.classList.add('cv-tab--active');
                div.querySelectorAll('.cv-tab-panel').forEach(function (p) { p.classList.add('hidden'); });
                document.getElementById('cv-panel-' + tab.dataset.tab).classList.remove('hidden');
            });
        });

        document.getElementById('btn-pdf').addEventListener('click', function () {
            fetch('/otimizar/pdf')
                .then(function (res) {
                    if (!res.ok) throw new Error('Erro ao gerar PDF');
                    return res.blob();
                })
                .then(function (blob) {
                    var url = URL.createObjectURL(blob);
                    var a = document.createElement('a');
                    a.href = url;
                    a.download = 'curriculo_otimizado.pdf';
                    a.click();
                    URL.revokeObjectURL(url);
                })
                .catch(function (err) { alert(err.message); });
        });

        document.getElementById('btn-copiar').addEventListener('click', function () {
            var el = document.getElementById('curriculo-text');
            var texto = formatPlainText(el);
            var btn = document.getElementById('btn-copiar');
            navigator.clipboard.writeText(texto).then(function () {
                btn.innerHTML = '<i data-lucide="check"></i> Texto copiado';
                if (window.lucide) lucide.createIcons({ nodes: [btn] });
                setTimeout(function () {
                    btn.innerHTML = '<i data-lucide="clipboard"></i> Copiar texto';
                    if (window.lucide) lucide.createIcons({ nodes: [btn] });
                }, 2000);
            });
        });
    }

    function renderComparisonView(original, optimized) {
        var linesA = original.split('\n').map(function (l) { return l.trim(); }).filter(Boolean);
        var linesB = cvToPlainLines(optimized);
        var diff = computeDiff(linesA, linesB);

        var leftHtml = '';
        var rightHtml = '';

        diff.forEach(function (item) {
            if (item.type === 'same') {
                leftHtml  += '<div class="diff-line diff-line--same">'   + escapeHtml(item.text) + '</div>';
                rightHtml += '<div class="diff-line diff-line--same">'   + escapeHtml(item.text) + '</div>';
            } else if (item.type === 'remove') {
                leftHtml  += '<div class="diff-line diff-line--remove">' + escapeHtml(item.text) + '</div>';
                rightHtml += '<div class="diff-line diff-line--empty"></div>';
            } else {
                leftHtml  += '<div class="diff-line diff-line--empty"></div>';
                rightHtml += '<div class="diff-line diff-line--add">'    + escapeHtml(item.text) + '</div>';
            }
        });

        return '<div class="cv-diff">' +
            '<div class="cv-diff__panel">' +
                '<div class="cv-diff__header"><i data-lucide="file-text"></i> Original</div>' +
                '<div class="cv-diff__content">' + leftHtml + '</div>' +
            '</div>' +
            '<div class="cv-diff__divider"></div>' +
            '<div class="cv-diff__panel">' +
                '<div class="cv-diff__header"><i data-lucide="sparkles"></i> Otimizado</div>' +
                '<div class="cv-diff__content">' + rightHtml + '</div>' +
            '</div>' +
        '</div>' +
        '<div class="diff-legend">' +
            '<span class="diff-legend__item diff-legend__item--remove">Removido</span>' +
            '<span class="diff-legend__item diff-legend__item--add">Adicionado</span>' +
        '</div>';
    }

    function cvToPlainLines(texto) {
        return texto.split('\n').map(function (line) {
            line = line.trim();
            if (!line) return null;
            var m;
            if ((m = line.match(/^---SECAO:\s*(.+?)\s*---$/)))  return m[1].toUpperCase();
            if ((m = line.match(/^---EMPRESA:\s*(.+?)\s*---$/))) return m[1];
            if ((m = line.match(/^---CARGO:\s*(.+?)\s*---$/)))   return m[1];
            return line;
        }).filter(Boolean);
    }

    function computeDiff(a, b) {
        var m = a.length, n = b.length;
        var dp = [];
        for (var i = 0; i <= m; i++) {
            dp[i] = new Int32Array(n + 1);
        }
        for (var i = 1; i <= m; i++) {
            for (var j = 1; j <= n; j++) {
                dp[i][j] = a[i-1] === b[j-1]
                    ? dp[i-1][j-1] + 1
                    : Math.max(dp[i-1][j], dp[i][j-1]);
            }
        }
        var result = [];
        var i = m, j = n;
        while (i > 0 || j > 0) {
            if (i > 0 && j > 0 && a[i-1] === b[j-1]) {
                result.push({ type: 'same', text: a[i-1] });
                i--; j--;
            } else if (j > 0 && (i === 0 || dp[i][j-1] >= dp[i-1][j])) {
                result.push({ type: 'add', text: b[j-1] });
                j--;
            } else {
                result.push({ type: 'remove', text: a[i-1] });
                i--;
            }
        }
        return result.reverse();
    }

    function renderStructuredCV(texto) {
        var lines = texto.split('\n');
        var html = '';
        var headerIdx = 0;
        var inList = false;

        for (var i = 0; i < lines.length; i++) {
            var line = lines[i].trim();
            if (!line) continue;

            // Section marker
            var secMatch = line.match(/^---SECAO:\s*(.+?)\s*---$/);
            if (secMatch) {
                if (inList) { html += '</ul>'; inList = false; }
                html += '<h3 class="cv-section">' + escapeHtml(secMatch[1]) + '</h3>';
                headerIdx = 99;
                continue;
            }

            // Company marker
            var empMatch = line.match(/^---EMPRESA:\s*(.+?)\s*---$/);
            if (empMatch) {
                if (inList) { html += '</ul>'; inList = false; }
                html += '<div class="cv-company">' + escapeHtml(empMatch[1]) + '</div>';
                continue;
            }

            // Role marker
            var cargoMatch = line.match(/^---CARGO:\s*(.+?)\s*---$/);
            if (cargoMatch) {
                if (inList) { html += '</ul>'; inList = false; }
                html += '<div class="cv-role">' + escapeHtml(cargoMatch[1]) + '</div>';
                continue;
            }

            // Bullet
            if (line.charAt(0) === '\u2022' || line.charAt(0) === '-') {
                if (!inList) { html += '<ul class="cv-bullets">'; inList = true; }
                html += '<li>' + escapeHtml(line.replace(/^[\u2022\-]\s*/, '')) + '</li>';
                continue;
            }

            if (inList) { html += '</ul>'; inList = false; }

            // Header lines
            if (headerIdx === 0) {
                html += '<h2 class="cv-name">' + escapeHtml(line) + '</h2>';
                headerIdx = 1;
                continue;
            }
            if (headerIdx === 1) {
                if (line.indexOf('@') !== -1 || line.toLowerCase().indexOf('linkedin') !== -1) {
                    html += '<p class="cv-contact">' + escapeHtml(line) + '</p><hr class="cv-divider">';
                    headerIdx = 99;
                } else {
                    html += '<p class="cv-title">' + escapeHtml(line) + '</p>';
                    headerIdx = 2;
                }
                continue;
            }
            if (headerIdx === 2) {
                html += '<p class="cv-contact">' + escapeHtml(line) + '</p><hr class="cv-divider">';
                headerIdx = 99;
                continue;
            }

            html += '<p class="cv-text">' + escapeHtml(line) + '</p>';
        }

        if (inList) html += '</ul>';
        return html;
    }

    function formatPlainText(el) {
        var parts = [];
        var children = el.children;
        for (var i = 0; i < children.length; i++) {
            var node = children[i];
            var tag = node.tagName.toLowerCase();
            var text = node.innerText.trim();
            if (!text) continue;
            if (tag === 'h2' || tag === 'h3') {
                if (parts.length) parts.push('');
                parts.push(text.toUpperCase());
                parts.push('');
            } else if (tag === 'hr') {
                parts.push('---');
            } else if (tag === 'ul') {
                var items = node.querySelectorAll('li');
                for (var j = 0; j < items.length; j++) {
                    parts.push('• ' + items[j].innerText.trim());
                }
            } else {
                parts.push(text);
            }
        }
        return parts.join('\n').replace(/\n{3,}/g, '\n\n').trim();
    }

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }
})();
