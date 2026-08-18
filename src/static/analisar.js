(function () {
    'use strict';

    const fileInput = document.getElementById('ats-file');
    const vagaInput = document.getElementById('ats-vaga');
    const btnAnalisar = document.getElementById('btn-analisar');
    const loader = document.getElementById('loader');
    const resultado = document.getElementById('resultado');
    const fileDrop = document.getElementById('file-drop');
    const photoDrop = document.getElementById('photo-drop');
    const photoInput = document.getElementById('photo-file');

    var textoOriginal = '';
    var photoDataUrl = null;
    var _sliderCleanup = null;
    var selectedCurriculo = null; // currículo salvo escolhido via CurriculoPicker, se houver

    var MAX_FILE_BYTES = 5 * 1024 * 1024; // 5 MB — deve coincidir com MAX_UPLOAD_BYTES no back-end

    function showFileSizeError(show) {
        var el = document.getElementById('file-size-error');
        if (el) el.classList.toggle('hidden', !show);
    }

    function validateFileSize(file) {
        if (file && file.size > MAX_FILE_BYTES) {
            showFileSizeError(true);
            return false;
        }
        showFileSizeError(false);
        return true;
    }

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
                if (!validateFileSize(e.dataTransfer.files[0])) return;
                fileInput.files = e.dataTransfer.files;
                selectedCurriculo = null;
                updateDropLabel();
            }
        });

        fileInput.addEventListener('change', function () {
            if (fileInput.files.length && !validateFileSize(fileInput.files[0])) {
                fileInput.value = '';
                updateDropLabel();
                return;
            }
            if (fileInput.files.length) selectedCurriculo = null;
            updateDropLabel();
        });
    }

    // ===== Photo Drop Zone =====
    if (photoDrop && photoInput) {
        photoDrop.addEventListener('click', function () { photoInput.click(); });

        photoDrop.addEventListener('dragover', function (e) {
            e.preventDefault();
            photoDrop.classList.add('file-drop--active');
        });

        photoDrop.addEventListener('dragleave', function () {
            photoDrop.classList.remove('file-drop--active');
        });

        photoDrop.addEventListener('drop', function (e) {
            e.preventDefault();
            photoDrop.classList.remove('file-drop--active');
            if (e.dataTransfer.files.length) {
                photoInput.files = e.dataTransfer.files;
                updatePhotoLabel();
            }
        });

        photoInput.addEventListener('change', updatePhotoLabel);
    }

    function updateDropLabel() {
        const textEl = fileDrop.querySelector('.file-drop__text');
        if (fileInput.files.length) {
            textEl.textContent = fileInput.files[0].name;
            fileDrop.classList.add('file-drop--active');
        } else if (selectedCurriculo) {
            textEl.textContent = 'Usando: ' + selectedCurriculo.label;
            fileDrop.classList.add('file-drop--active');
        } else {
            textEl.textContent = 'Arraste ou clique para selecionar';
            fileDrop.classList.remove('file-drop--active');
        }
    }

    // ===== Usar currículo salvo =====
    var btnUsarSalvo = document.getElementById('btn-usar-salvo');
    if (btnUsarSalvo) {
        btnUsarSalvo.addEventListener('click', function () {
            if (window.CurriculoPicker) {
                window.CurriculoPicker.open(function (curriculo) {
                    selectedCurriculo = curriculo;
                    fileInput.value = '';
                    showFileSizeError(false);
                    updateDropLabel();
                });
            }
        });
    }

    function updatePhotoLabel() {
        if (!photoDrop || !photoInput) return;
        const textEl = photoDrop.querySelector('.file-drop__text');
        if (photoInput.files.length) {
            textEl.textContent = photoInput.files[0].name;
            photoDrop.classList.add('file-drop--active');
            var reader = new FileReader();
            reader.onload = function (e) {
                photoDataUrl = e.target.result;
                _refreshCVPreviews();
            };
            reader.readAsDataURL(photoInput.files[0]);
        } else {
            textEl.textContent = 'Adicionar foto (aparece no cabeçalho do PDF)';
            photoDrop.classList.remove('file-drop--active');
            photoDataUrl = null;
            _refreshCVPreviews();
        }
    }

    function _refreshCVPreviews() {
        var taEl = document.getElementById('textarea-curriculo');
        var texto = taEl ? taEl.value : '';
        if (!texto) return;
        var previewEl = document.getElementById('curriculo-text');
        if (previewEl) previewEl.innerHTML = renderStructuredCV(texto, photoDataUrl);
        var tplPane = document.getElementById('tpl-preview-pane');
        if (tplPane) {
            delete tplPane.dataset.rendered;
            if (!document.getElementById('template-modal').classList.contains('hidden')) {
                tplPane.innerHTML = renderStructuredCV(texto, photoDataUrl);
                tplPane.dataset.rendered = '1';
            }
        }
    }

    btnAnalisar.addEventListener('click', enviarAnalise);

    // ===== Analysis =====
    async function enviarAnalise() {
        if (!fileInput.files.length && !selectedCurriculo) {
            alert('Selecione um arquivo ou um currículo salvo');
            return;
        }

        const formData = new FormData();
        if (selectedCurriculo) {
            formData.append('curriculo_id', selectedCurriculo.id);
        } else {
            formData.append('arquivo', fileInput.files[0]);
        }
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

    // ===== Criterio helpers (compat: criterios antigos eram número puro,
    // novos vêm como {nota, motivo} — ver build_prompt_ats) =====
    function criterioNota(c) {
        return (c && typeof c === 'object') ? c.nota : c;
    }
    function criterioMotivo(c, fallback) {
        return (c && typeof c === 'object' && c.motivo) ? c.motivo : fallback;
    }
    function criterioLista(c, campo) {
        return (c && typeof c === 'object' && Array.isArray(c[campo])) ? c[campo] : [];
    }
    // Mesma escala de cor do relatório de /entrevista (lá em 0-10, aqui em 0-100)
    function scoreCor(score) {
        if (score >= 90) return 'var(--color-score-excelente)';
        if (score >= 70) return 'var(--color-score-bom)';
        if (score >= 50) return 'var(--color-score-regular)';
        if (score >= 30) return 'var(--color-score-ruim)';
        return 'var(--color-score-pessimo)';
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

    // ===== Show analysis result =====
    function mostrarResultado(data) {
        if (data.error) {
            resultado.innerHTML = '<p class="error">' + escapeHtml(data.error) + '</p>';
            return;
        }

        // Garante que criterios e listas existam mesmo com resposta parcial do LLM
        data.criterios = data.criterios || {};
        var CRITERIOS_CHAVE = ['estrutura', 'clareza', 'experiencia', 'palavras_chave', 'skills', 'compatibilidade'];
        CRITERIOS_CHAVE.forEach(function(k) { data.criterios[k] = data.criterios[k] || {}; });
        data.pontos_fortes = data.pontos_fortes || [];
        data.pontos_fracos = data.pontos_fracos || [];
        data.sugestoes = data.sugestoes || [];
        data.palavras_chave_faltando = data.palavras_chave_faltando || [];
        data.certificados_sugeridos = data.certificados_sugeridos || [];

        const score = data.score_total || 0;
        var cor = scoreCor(score);

        var analiseHtml =
            '<div class="score-box" style="border-color:' + cor + '">' +
                '<h2 style="color:' + cor + '">Score ATS: ' + score + '/100</h2>' +
            '</div>' +
            renderVeredito(data.veredito) +
            '<button class="btn btn--optimize" id="btn-otimizar" style="margin-top: 16px;"><i data-lucide="wand-2"></i> Otimizar Currículo</button>' +
            '<div id="loader-otimizar" class="loader hidden" style="margin-top: 12px;">' +
                '<span class="loader__bar"></span>' +
                '<span>Otimizando currículo... (pode levar alguns minutos)</span>' +
            '</div>' +
            '<h3>Critérios</h3>' +
            '<div class="criterios-list">' +
                renderCriterioAccordion('estrutura', 'Estrutura', data.criterios.estrutura, 15, 'Formatação e organização do documento') +
                renderCriterioAccordion('clareza', 'Clareza', data.criterios.clareza, 15, 'Qualidade da escrita e objetividade') +
                renderCriterioAccordion('experiencia', 'Experiência', data.criterios.experiencia, 20, 'Relevância e descrição de cargos') +
                renderCriterioAccordion('palavras_chave', 'Palavras-chave', data.criterios.palavras_chave, 20, 'Termos que sistemas ATS buscam') +
                renderCriterioAccordion('skills', 'Skills', data.criterios.skills, 15, 'Competências técnicas listadas') +
                renderCriterioAccordion('compatibilidade', 'Compatibilidade', data.criterios.compatibilidade, 15, 'Aderência à vaga descrita') +
            '</div>' +
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
        setupCriterioAccordions(resultado);
        document.getElementById('btn-otimizar').addEventListener('click', otimizarCurriculo);
    }

    // ===== Optimization =====
    async function otimizarCurriculo() {
        if (!fileInput.files.length && !selectedCurriculo) {
            alert('Selecione um arquivo ou um currículo salvo primeiro e clique em Analisar.');
            return;
        }

        const loaderOtimizar = document.getElementById('loader-otimizar');
        const btnOtimizar = document.getElementById('btn-otimizar');

        loaderOtimizar.classList.remove('hidden');
        btnOtimizar.disabled = true;

        const formData = new FormData();
        if (selectedCurriculo) {
            formData.append('curriculo_id', selectedCurriculo.id);
        } else {
            formData.append('arquivo', fileInput.files[0]);
        }
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
                            '<div class="cv-structured cv-structured--preview" id="curriculo-text">' + renderStructuredCV(curriculo, photoDataUrl) + '</div>' +
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
            '<div class="cv-edit-section" id="cv-edit-section">' +
                '<button type="button" class="btn btn--secondary cv-edit-toggle" id="btn-toggle-edit">' +
                    '<i data-lucide="pencil"></i> Editar texto antes do PDF' +
                '</button>' +
                '<div id="cv-edit-wrapper" class="cv-edit-wrapper hidden">' +
                    '<p class="cv-edit-hint">Edite livremente. Use <code>---SECAO: nome---</code>, <code>---EMPRESA: nome---</code>, <code>---CARGO: nome---</code> para estruturar seções.</p>' +
                    '<textarea id="textarea-curriculo" class="cv-edit-textarea" spellcheck="false"></textarea>' +
                    '<div class="cv-edit-actions">' +
                        '<button type="button" class="btn btn--primary" id="btn-salvar-edit"><i data-lucide="save"></i> Salvar e atualizar prévia</button>' +
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

        // Populate editable textarea
        var textareaEl = document.getElementById('textarea-curriculo');
        if (textareaEl) textareaEl.value = curriculo;

        // Toggle edit section
        document.getElementById('btn-toggle-edit').addEventListener('click', function () {
            var wrapper = document.getElementById('cv-edit-wrapper');
            var isHidden = wrapper.classList.toggle('hidden');
            this.innerHTML = isHidden
                ? '<i data-lucide="pencil"></i> Editar texto antes do PDF'
                : '<i data-lucide="x"></i> Fechar editor';
            if (window.lucide) lucide.createIcons({ nodes: [this] });
        });

        // Save + update preview
        document.getElementById('btn-salvar-edit').addEventListener('click', function () {
            var novoTexto = document.getElementById('textarea-curriculo').value;
            // Re-render optimized pane in slider
            var previewEl = document.getElementById('curriculo-text');
            if (previewEl) previewEl.innerHTML = renderStructuredCV(novoTexto, photoDataUrl);
            // Invalidate template modal preview so it regenerates on next open
            var tplPane = document.getElementById('tpl-preview-pane');
            if (tplPane) {
                tplPane.innerHTML = renderStructuredCV(novoTexto, photoDataUrl);
                tplPane.dataset.rendered = '1';
            }
            var btn = this;
            btn.innerHTML = '<i data-lucide="check"></i> Salvo!';
            if (window.lucide) lucide.createIcons({ nodes: [btn] });
            setTimeout(function () {
                btn.innerHTML = '<i data-lucide="save"></i> Salvar e atualizar prévia';
                if (window.lucide) lucide.createIcons({ nodes: [btn] });
            }, 2000);
        });

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
                pane.innerHTML = renderStructuredCV(curriculo, photoDataUrl);
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

            var taEl = document.getElementById('textarea-curriculo');
            var textoFinal = taEl ? taEl.value : curriculo;
            var fd = new FormData();
            fd.append('template', tpl);
            fd.append('texto', textoFinal);
            if (photoInput && photoInput.files.length) {
                fd.append('foto', photoInput.files[0]);
            }

            fetch('/otimizar/pdf', { method: 'POST', body: fd })
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

    function _wrapHeader(headerHtml, photoUrl) {
        if (!photoUrl) return headerHtml;
        return '<div class="cv-header-row">' +
            '<div class="cv-header-text">' + headerHtml + '</div>' +
            '<img class="cv-header-photo" src="' + photoUrl + '" alt="">' +
            '</div>';
    }

    function renderStructuredCV(texto, photoUrl) {
        var lines = texto.normalize('NFC').split('\n');
        var html = '';
        var headerIdx = 0;
        var headerHtml = '';
        var inList = false;

        for (var i = 0; i < lines.length; i++) {
            var line = lines[i].trim();
            if (!line) continue;

            var secMatch = line.match(/^---SECAO:\s*(.+?)\s*---$/);
            if (secMatch) {
                if (inList) { html += '</ul>'; inList = false; }
                if (headerHtml) { html += _wrapHeader(headerHtml, photoUrl); headerHtml = ''; headerIdx = 99; }
                html += '<h3 class="cv-section">' + linkifyText(secMatch[1]) + '</h3>';
                headerIdx = 99;
                continue;
            }

            var empMatch = line.match(/^---EMPRESA:\s*(.+?)\s*---$/);
            if (empMatch) {
                if (inList) { html += '</ul>'; inList = false; }
                if (headerHtml) { html += _wrapHeader(headerHtml, photoUrl); headerHtml = ''; headerIdx = 99; }
                html += '<div class="cv-company">' + linkifyText(empMatch[1]) + '</div>';
                continue;
            }

            var cargoMatch = line.match(/^---CARGO:\s*(.+?)\s*---$/);
            if (cargoMatch) {
                if (inList) { html += '</ul>'; inList = false; }
                if (headerHtml) { html += _wrapHeader(headerHtml, photoUrl); headerHtml = ''; headerIdx = 99; }
                html += '<div class="cv-role">' + linkifyText(cargoMatch[1]) + '</div>';
                continue;
            }

            if (line.charAt(0) === '•' || line.charAt(0) === '-') {
                if (headerHtml) { html += _wrapHeader(headerHtml, photoUrl); headerHtml = ''; headerIdx = 99; }
                if (!inList) { html += '<ul class="cv-bullets">'; inList = true; }
                html += '<li>' + linkifyText(line.replace(/^[•\-]\s*/, '')) + '</li>';
                continue;
            }

            if (inList) { html += '</ul>'; inList = false; }

            if (headerIdx === 0) {
                headerHtml += '<h2 class="cv-name">' + linkifyText(line) + '</h2>';
                headerIdx = 1;
                continue;
            }
            if (headerIdx === 1) {
                if (line.indexOf('@') !== -1 || line.toLowerCase().indexOf('linkedin') !== -1) {
                    headerHtml += '<p class="cv-contact">' + linkifyText(line) + '</p>';
                    html += _wrapHeader(headerHtml, photoUrl) + '<hr class="cv-divider">';
                    headerHtml = '';
                    headerIdx = 99;
                } else {
                    headerHtml += '<p class="cv-title">' + linkifyText(line) + '</p>';
                    headerIdx = 2;
                }
                continue;
            }
            if (headerIdx === 2) {
                headerHtml += '<p class="cv-contact">' + linkifyText(line) + '</p>';
                html += _wrapHeader(headerHtml, photoUrl) + '<hr class="cv-divider">';
                headerHtml = '';
                headerIdx = 99;
                continue;
            }

            html += '<p class="cv-text">' + linkifyText(line) + '</p>';
        }

        if (inList) html += '</ul>';
        if (headerHtml) html += _wrapHeader(headerHtml, photoUrl);
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

    function linkifyText(text) {
        // First escape the HTML
        var escaped = escapeHtml(text);
        
        // Pattern to match URLs
        var urlPattern = /(https?:\/\/[^\s<>"{}|\\^`\[\]]*[a-zA-Z0-9]|www\.[^\s<>"{}|\\^`\[\]]*[a-zA-Z0-9])/g;
        
        // Replace URLs with clickable links
        var linkedText = escaped.replace(urlPattern, function(url) {
            var href = url.startsWith('http') ? url : 'https://' + url;
            return '<a href="' + href + '" target="_blank" rel="noopener noreferrer" class="cv-link">' + url + '</a>';
        });
        
        return linkedText;
    }
})();