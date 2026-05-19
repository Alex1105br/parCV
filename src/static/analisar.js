(function () {
    'use strict';

    const fileInput = document.getElementById('ats-file');
    const vagaInput = document.getElementById('ats-vaga');
    const btnAnalisar = document.getElementById('btn-analisar');
    const loader = document.getElementById('loader');
    const resultado = document.getElementById('resultado');
    const fileDrop = document.getElementById('file-drop');

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
        } else {
            textEl.textContent = 'Arraste ou clique para selecionar';
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
        else if (score > 50) cor = 'var(--color-warning)';

        resultado.innerHTML =
            '<div class="score-box" style="border-color:' + cor + '">' +
                '<h2 style="color:' + cor + '">Score ATS: ' + score + '/100</h2>' +
            '</div>' +
            '<h3>Critérios</h3>' +
            '<ul class="criterios-list">' +
                '<li><strong>Estrutura:</strong> ' + escapeHtml(data.criterios.estrutura) + '/15 <span class="criterio-info">Formata\u00e7\u00e3o e organiza\u00e7\u00e3o do documento</span></li>' +
                '<li><strong>Clareza:</strong> ' + escapeHtml(data.criterios.clareza) + '/15 <span class="criterio-info">Qualidade da escrita e objetividade</span></li>' +
                '<li><strong>Experi\u00eancia:</strong> ' + escapeHtml(data.criterios.experiencia) + '/20 <span class="criterio-info">Relev\u00e2ncia e descri\u00e7\u00e3o de cargos</span></li>' +
                '<li><strong>Palavras-chave:</strong> ' + escapeHtml(data.criterios.palavras_chave) + '/20 <span class="criterio-info">Termos que sistemas ATS buscam</span></li>' +
                '<li><strong>Skills:</strong> ' + escapeHtml(data.criterios.skills) + '/15 <span class="criterio-info">Compet\u00eancias t\u00e9cnicas listadas</span></li>' +
                '<li><strong>Compatibilidade:</strong> ' + escapeHtml(data.criterios.compatibilidade) + '/15 <span class="criterio-info">Ader\u00eancia \u00e0 vaga descrita</span></li>' +
            '</ul>' +
            '<h3>Pontos fortes</h3>' +
            '<ul>' + data.pontos_fortes.map(function (p) { return '<li>' + escapeHtml(p) + '</li>'; }).join('') + '</ul>' +
            '<h3>Pontos fracos</h3>' +
            '<ul>' + data.pontos_fracos.map(function (p) { return '<li>' + escapeHtml(p) + '</li>'; }).join('') + '</ul>' +
            '<h3>Sugestões</h3>' +
            '<ul>' + data.sugestoes.map(function (s) { return '<li>' + escapeHtml(s) + '</li>'; }).join('') + '</ul>' +
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

        let melhorasHtml = '';
        if (melhorias && melhorias.length) {
            melhorasHtml =
                '<div class="cv-improvements">' +
                    '<strong>Melhorias aplicadas:</strong>' +
                    '<ul>' + melhorias.map(function (m) { return '<li>' + escapeHtml(m) + '</li>'; }).join('') + '</ul>' +
                '</div>';
        }

        div.innerHTML =
            '<hr style="margin: 24px 0; border-color: var(--color-border);">' +
            '<h2 style="color: var(--color-success);">Currículo Otimizado</h2>' +
            melhorasHtml +
            '<div class="cv-structured" id="curriculo-text">' + renderStructuredCV(curriculo) + '</div>' +
            '<div style="display: flex; gap: 12px; flex-wrap: wrap;">' +
                '<button type="button" class="btn btn--primary" id="btn-pdf"><i data-lucide="file-down"></i> Baixar PDF</button>' +
                '<button type="button" class="btn btn--secondary" id="btn-copiar"><i data-lucide="clipboard"></i> Copiar texto</button>' +
            '</div>';

        if (window.lucide) lucide.createIcons({ nodes: [div] });

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
            var texto = document.getElementById('curriculo-text').innerText;
            navigator.clipboard.writeText(texto).then(function () {
                alert('Currículo copiado para a área de transferência!');
            });
        });
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

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }
})();
