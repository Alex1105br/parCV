(function () {
    'use strict';

    const fileInput = document.getElementById('ats-file');
    const vagaInput = document.getElementById('ats-vaga');
    const btnAnalisar = document.getElementById('btn-analisar');
    const loader = document.getElementById('loader');
    const resultado = document.getElementById('resultado');
    const fileDrop = document.getElementById('file-drop');

    var textoOriginal = '';
    var _sliderCleanup = null;

    // ===== File Drop Zone =====
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

    // ===== Analysis =====
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
        if (_sliderCleanup) { _sliderCleanup(); _sliderCleanup = null; }

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

    // ===== Tab setup =====
    function setupTabs(container) {
        container.querySelectorAll('.cv-tab').forEach(function (tab) {
            tab.addEventListener('click', function () {
                if (this.disabled) return;
                container.querySelectorAll('.cv-tab').forEach(function (t) { t.classList.remove('cv-tab--active'); });
                this.classList.add('cv-tab--active');
                container.querySelectorAll('.cv-tab-panel').forEach(function (p) { p.classList.add('hidden'); });
                var panel = document.getElementById('cv-panel-' + this.dataset.tab);
                if (panel) panel.classList.remove('hidden');
            });
        });
    }

    // ===== Show analysis result =====
    function mostrarResultado(data) {
        if (data.error) {
            resultado.innerHTML = '<p class="error">' + escapeHtml(data.error) + '</p>';
            return;
        }

        const score = data.score_total;
        let cor = 'var(--color-danger)';
        if (score > 75) cor = 'var(--color-success)';
        else if (score > 50) cor = 'var(--color-peach)';

        var analiseHtml =
            '<div class="score-box" style="border-color:' + cor + '">' +
                '<h2 style="color:' + cor + '">Score ATS: ' + score + '/100</h2>' +
            '</div>' +
            '<button class="btn btn--optimize" id="btn-otimizar" style="margin-top: 16px;"><i data-lucide="wand-2"></i> Otimizar Currículo</button>' +
            '<div id="loader-otimizar" class="loader hidden" style="margin-top: 12px;">' +
                '<span class="loader__bar"></span>' +
                '<span>Otimizando currículo... (pode levar alguns minutos)</span>' +
            '</div>' +
            '<h3>Critérios</h3>' +
            '<ul class="criterios-list">' +
                '<li><span class="criterio-icon" data-tooltip="Formatação e organização do documento"><i data-lucide="info"></i></span><strong>Estrutura:</strong> ' + escapeHtml(data.criterios.estrutura) + '/15</li>' +
                '<li><span class="criterio-icon" data-tooltip="Qualidade da escrita e objetividade"><i data-lucide="info"></i></span><strong>Clareza:</strong> ' + escapeHtml(data.criterios.clareza) + '/15</li>' +
                '<li><span class="criterio-icon" data-tooltip="Relevância e descrição de cargos"><i data-lucide="info"></i></span><strong>Experiência:</strong> ' + escapeHtml(data.criterios.experiencia) + '/20</li>' +
                '<li><span class="criterio-icon" data-tooltip="Termos que sistemas ATS buscam"><i data-lucide="info"></i></span><strong>Palavras-chave:</strong> ' + escapeHtml(data.criterios.palavras_chave) + '/20</li>' +
                '<li><span class="criterio-icon" data-tooltip="Competências técnicas listadas"><i data-lucide="info"></i></span><strong>Skills:</strong> ' + escapeHtml(data.criterios.skills) + '/15</li>' +
                '<li><span class="criterio-icon" data-tooltip="Aderência à vaga descrita"><i data-lucide="info"></i></span><strong>Compatibilidade:</strong> ' + escapeHtml(data.criterios.compatibilidade) + '/15</li>' +
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
            : '');

        resultado.innerHTML =
            '<div class="cv-tabs" id="tabs-main">' +
                '<button class="cv-tab cv-tab--active" data-tab="analise"><i data-lucide="scan-search"></i> Análise</button>' +
                '<button class="cv-tab" data-tab="otimizacao" id="tab-otimizacao" disabled><i data-lucide="wand-2"></i> Otimização</button>' +
            '</div>' +
            '<div id="cv-panel-analise" class="cv-tab-panel">' + analiseHtml + '</div>' +
            '<div id="cv-panel-otimizacao" class="cv-tab-panel hidden"></div>';

        if (window.lucide) lucide.createIcons({ nodes: [resultado] });
        setupTabs(resultado);
        document.getElementById('btn-otimizar').addEventListener('click', otimizarCurriculo);
    }

    // ===== Optimization =====
    async function otimizarCurriculo() {
        if (!fileInput.files.length) {
            alert('Selecione um arquivo de currículo primeiro e clique em Analisar.');
            return;
        }

        const loaderOtimizar = document.getElementById('loader-otimizar');
        const btnOtimizar = document.getElementById('btn-otimizar');

        loaderOtimizar.classList.remove('hidden');
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
                var analisePanel = document.getElementById('cv-panel-analise');
                analisePanel.insertAdjacentHTML('beforeend',
                    '<p class="error">' + escapeHtml(data.error) + '</p>');
                return;
            }

            mostrarComparacao(data.curriculo_otimizado, data.melhorias);
        } catch (err) {
            loaderOtimizar.classList.add('hidden');
            btnOtimizar.disabled = false;
            alert('Erro ao otimizar: ' + err.message);
        }
    }

    // ===== Show comparison with slider =====
    function mostrarComparacao(curriculo, melhorias) {
        var panel = document.getElementById('cv-panel-otimizacao');

        // Cleanup old slider if re-optimizing
        if (_sliderCleanup) { _sliderCleanup(); _sliderCleanup = null; }

        var melhorasHtml = '';
        if (melhorias && melhorias.length) {
            melhorasHtml =
                '<div class="cv-improvements">' +
                    '<strong>Melhorias aplicadas:</strong>' +
                    '<ul>' + melhorias.map(function (m) { return '<li>' + escapeHtml(m) + '</li>'; }).join('') + '</ul>' +
                '</div>';
        }

        var originalHtml = textoOriginal && textoOriginal.trim()
            ? renderOriginalCV(textoOriginal)
            : '<p class="error">Texto original não disponível.</p>';

        panel.innerHTML =
            melhorasHtml +
            '<div class="cv-slide-wrapper">' +
                '<div class="cv-slide-toggle-wrap">' +
                    '<button class="cv-slide-toggle" id="slide-toggle">' +
                        '<span class="cv-slide-toggle__label" id="slide-toggle-left">Otimizado</span>' +
                        '<span class="cv-slide-toggle__divider" id="slide-toggle-divider"><i data-lucide="arrow-left-right"></i></span>' +
                        '<span class="cv-slide-toggle__label" id="slide-toggle-right">Original</span>' +
                    '</button>' +
                '</div>' +
                '<div class="cv-slide-compare" id="cv-slide-compare">' +
                    // Original pane (background, scrollable)
                    '<div class="cv-slide-pane cv-slide-pane--original" id="slide-pane-original">' +
                        originalHtml +
                    '</div>' +
                    // Optimized pane (clipped via wrapper)
                    '<div class="cv-slide-clipper" id="slide-clipper">' +
                        '<div class="cv-slide-pane cv-slide-pane--optimized" id="slide-pane-optimized">' +
                            '<div class="cv-structured cv-structured--preview" id="curriculo-text">' + renderStructuredCV(curriculo) + '</div>' +
                        '</div>' +
                    '</div>' +
                    // Drag handle
                    '<div class="cv-slide-handle" id="slide-handle">' +
                        '<div class="cv-slide-handle__bar"></div>' +
                        '<div class="cv-slide-handle__btn"><i data-lucide="move-horizontal"></i></div>' +
                        '<div class="cv-slide-handle__bar"></div>' +
                    '</div>' +
                '</div>' +
            '</div>' +
            '<div style="display: flex; gap: 12px; flex-wrap: wrap; margin-top: 16px;">' +
                '<button type="button" class="btn btn--primary" id="btn-pdf"><i data-lucide="file-down"></i> Baixar PDF</button>' +
                '<button type="button" class="btn btn--secondary" id="btn-copiar"><i data-lucide="clipboard"></i> Copiar texto</button>' +
            '</div>' +
            '<div id="template-modal" class="tpl-modal hidden" role="dialog" aria-modal="true" aria-label="Escolher template de PDF">' +
                '<div class="tpl-modal__backdrop"></div>' +
                '<div class="tpl-modal__box">' +
                    '<h3 class="tpl-modal__title"><i data-lucide="layout-template"></i> Escolha o template</h3>' +
                    '<div class="tpl-layout">' +
                        '<div class="tpl-cards">' +
                            '<label class="tpl-card">' +
                                '<input type="radio" name="tpl" value="classico" checked>' +
                                '<div class="tpl-swatch tpl-swatch--classico"></div>' +
                                '<div class="tpl-card__info">' +
                                    '<span class="tpl-card__label">Clássico</span>' +
                                    '<span class="tpl-card__desc">Azul e preto</span>' +
                                '</div>' +
                                '<span class="tpl-card__check"><i data-lucide="check"></i></span>' +
                            '</label>' +
                            '<label class="tpl-card">' +
                                '<input type="radio" name="tpl" value="moderno">' +
                                '<div class="tpl-swatch tpl-swatch--moderno"></div>' +
                                '<div class="tpl-card__info">' +
                                    '<span class="tpl-card__label">Moderno</span>' +
                                    '<span class="tpl-card__desc">Teal, cabeçalhos</span>' +
                                '</div>' +
                                '<span class="tpl-card__check"><i data-lucide="check"></i></span>' +
                            '</label>' +
                            '<label class="tpl-card">' +
                                '<input type="radio" name="tpl" value="executivo">' +
                                '<div class="tpl-swatch tpl-swatch--executivo"></div>' +
                                '<div class="tpl-card__info">' +
                                    '<span class="tpl-card__label">Executivo</span>' +
                                    '<span class="tpl-card__desc">Borgonha, barra lateral</span>' +
                                '</div>' +
                                '<span class="tpl-card__check"><i data-lucide="check"></i></span>' +
                            '</label>' +
                        '</div>' +
                        '<div class="tpl-preview-wrap">' +
                            '<div class="cv-preview cv-preview--classico" id="tpl-preview-pane"></div>' +
                        '</div>' +
                    '</div>' +
                    '<div class="tpl-modal__actions">' +
                        '<button type="button" class="btn btn--secondary" id="tpl-cancel">Cancelar</button>' +
                        '<button type="button" class="btn btn--primary" id="tpl-confirm"><i data-lucide="download"></i> Baixar PDF</button>' +
                    '</div>' +
                '</div>' +
            '</div>';

        if (window.lucide) lucide.createIcons({ nodes: [panel] });

        // Enable + switch to Otimização tab
        var tabComp = document.getElementById('tab-otimizacao');
        tabComp.disabled = false;
        tabComp.click();

        // Init slider
        var slideContainer = document.getElementById('cv-slide-compare');
        _sliderCleanup = initSlider(
            slideContainer,
            document.getElementById('slide-pane-original'),
            document.getElementById('slide-pane-optimized'),
            function (pct) { currentSlidePos = pct; }
        );

        // Toggle button
        var slideToggle = document.getElementById('slide-toggle');
        var toggleLeftEl = document.getElementById('slide-toggle-left');
        var toggleRightEl = document.getElementById('slide-toggle-right');
        var toggleDividerEl = document.getElementById('slide-toggle-divider');
        var slideToggleState = 'split'; // 'split' | 'optimized' | 'original'
        var currentSlidePos = 50;

        function animateSlider(to, duration) {
            var from = currentSlidePos;
            var start = null;
            function step(ts) {
                if (!start) start = ts;
                var t = Math.min((ts - start) / duration, 1);
                var eased = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
                currentSlidePos = from + (to - from) * eased;
                slideContainer.style.setProperty('--slide-pos', currentSlidePos + '%');
                if (t < 1) requestAnimationFrame(step);
            }
            requestAnimationFrame(step);
        }

        function updateToggleUI() {
            toggleLeftEl.classList.toggle('cv-slide-toggle__label--active', slideToggleState === 'optimized');
            toggleRightEl.classList.toggle('cv-slide-toggle__label--active', slideToggleState === 'original');
        }

        slideToggle.addEventListener('click', function () {
            if (slideToggleState !== 'original') {
                slideToggleState = 'original';
                animateSlider(0, 380);
            } else {
                slideToggleState = 'optimized';
                animateSlider(100, 380);
            }
            updateToggleUI();
        });

        // PDF download — open template picker with live preview
        document.getElementById('btn-pdf').addEventListener('click', function () {
            var modal = document.getElementById('template-modal');
            var pane = document.getElementById('tpl-preview-pane');
            if (!pane.dataset.rendered) {
                pane.innerHTML = renderStructuredCV(curriculo);
                pane.dataset.rendered = '1';
            }
            modal.classList.remove('hidden');
            if (window.lucide) lucide.createIcons({ nodes: [modal] });
        });

        // Live preview on card switch
        document.getElementById('template-modal').querySelectorAll('input[name="tpl"]')
            .forEach(function (radio) {
                radio.addEventListener('change', function () {
                    var pane = document.getElementById('tpl-preview-pane');
                    pane.className = 'cv-preview cv-preview--' + this.value;
                });
            });

        document.getElementById('tpl-cancel').addEventListener('click', function () {
            document.getElementById('template-modal').classList.add('hidden');
        });

        document.getElementById('template-modal').querySelector('.tpl-modal__backdrop')
            .addEventListener('click', function () {
                document.getElementById('template-modal').classList.add('hidden');
            });

        document.getElementById('tpl-confirm').addEventListener('click', function () {
            var selected = document.querySelector('input[name="tpl"]:checked');
            var tpl = selected ? selected.value : 'classico';
            var btn = document.getElementById('tpl-confirm');
            btn.disabled = true;
            btn.textContent = 'Gerando...';

            fetch('/otimizar/pdf?template=' + encodeURIComponent(tpl))
                .then(function (res) {
                    if (!res.ok) throw new Error('Erro ao gerar PDF');
                    return res.blob();
                })
                .then(function (blob) {
                    var url = URL.createObjectURL(blob);
                    var a = document.createElement('a');
                    a.href = url;
                    a.download = 'curriculo_' + tpl + '.pdf';
                    a.click();
                    URL.revokeObjectURL(url);
                    document.getElementById('template-modal').classList.add('hidden');
                })
                .catch(function (err) { alert(err.message); })
                .finally(function () {
                    btn.disabled = false;
                    btn.innerHTML = '<i data-lucide="download"></i> Baixar';
                    if (window.lucide) lucide.createIcons({ nodes: [btn] });
                });
        });

        // Copy text
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

    // ===== Slider =====
    function initSlider(container, origPane, optPane, onPosChange) {
        var isDragging = false;

        function setPos(clientX) {
            var rect = container.getBoundingClientRect();
            var pct = Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100));
            container.style.setProperty('--slide-pos', pct + '%');
            if (onPosChange) onPosChange(pct);
        }

        var handle = container.querySelector('.cv-slide-handle');

        function onMouseDown(e) { isDragging = true; e.preventDefault(); }
        function onMouseMove(e) { if (isDragging) setPos(e.clientX); }
        function onMouseUp() { isDragging = false; }
        function onTouchStart(e) { isDragging = true; e.preventDefault(); }
        function onTouchMove(e) { if (isDragging) setPos(e.touches[0].clientX); }
        function onTouchEnd() { isDragging = false; }

        // Proportional scroll sync: original drives optimized
        function onOrigScroll() {
            var maxOrig = origPane.scrollHeight - origPane.clientHeight;
            var maxOpt = optPane.scrollHeight - optPane.clientHeight;
            if (maxOrig > 0 && maxOpt > 0) {
                optPane.scrollTop = (origPane.scrollTop / maxOrig) * maxOpt;
            }
        }

        handle.addEventListener('mousedown', onMouseDown);
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
        handle.addEventListener('touchstart', onTouchStart, { passive: false });
        document.addEventListener('touchmove', onTouchMove);
        document.addEventListener('touchend', onTouchEnd);
        origPane.addEventListener('scroll', onOrigScroll);

        return function () {
            handle.removeEventListener('mousedown', onMouseDown);
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            handle.removeEventListener('touchstart', onTouchStart);
            document.removeEventListener('touchmove', onTouchMove);
            document.removeEventListener('touchend', onTouchEnd);
            origPane.removeEventListener('scroll', onOrigScroll);
        };
    }

    // ===== CV Renderers =====
    function renderOriginalCV(texto) {
        return '<pre class="cv-original-pre">' + escapeHtml(texto) + '</pre>';
    }

    function renderStructuredCV(texto) {
        var lines = texto.normalize('NFC').split('\n');
        var html = '';
        var headerIdx = 0;
        var inList = false;

        for (var i = 0; i < lines.length; i++) {
            var line = lines[i].trim();
            if (!line) continue;

            var secMatch = line.match(/^---SECAO:\s*(.+?)\s*---$/);
            if (secMatch) {
                if (inList) { html += '</ul>'; inList = false; }
                html += '<h3 class="cv-section">' + escapeHtml(secMatch[1]) + '</h3>';
                headerIdx = 99;
                continue;
            }

            var empMatch = line.match(/^---EMPRESA:\s*(.+?)\s*---$/);
            if (empMatch) {
                if (inList) { html += '</ul>'; inList = false; }
                html += '<div class="cv-company">' + escapeHtml(empMatch[1]) + '</div>';
                continue;
            }

            var cargoMatch = line.match(/^---CARGO:\s*(.+?)\s*---$/);
            if (cargoMatch) {
                if (inList) { html += '</ul>'; inList = false; }
                html += '<div class="cv-role">' + escapeHtml(cargoMatch[1]) + '</div>';
                continue;
            }

            if (line.charAt(0) === '•' || line.charAt(0) === '-') {
                if (!inList) { html += '<ul class="cv-bullets">'; inList = true; }
                html += '<li>' + escapeHtml(line.replace(/^[•\-]\s*/, '')) + '</li>';
                continue;
            }

            if (inList) { html += '</ul>'; inList = false; }

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
