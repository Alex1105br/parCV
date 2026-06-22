/**
 * CurriculoPicker — modal reutilizável para selecionar um currículo já
 * salvo (em /curriculos) em vez de enviar um novo arquivo. Usado em
 * /analisar, /entrevista e /chat.
 *
 * Uso:
 *   CurriculoPicker.open(function (curriculo) {
 *       // curriculo: { id, label, cor, arquivo_nome, criado_em, tem_arquivo_pdf }
 *   });
 *
 * Totalmente auto-contido (estilos inline injetados uma única vez), para
 * funcionar igual em qualquer página, independente do design system local.
 */
(function () {
    'use strict';

    var STYLE_ID = 'curriculo-picker-styles';
    var COR_PADRAO = '#6366f1';

    function injectStyles() {
        if (document.getElementById(STYLE_ID)) return;
        var style = document.createElement('style');
        style.id = STYLE_ID;
        style.textContent = [
            '.cp-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.6);display:flex;',
            'align-items:center;justify-content:center;z-index:9999;padding:20px;',
            'font-family:system-ui,-apple-system,sans-serif;}',
            '.cp-modal{background:#161722;border:1px solid rgba(255,255,255,0.08);border-radius:14px;',
            'width:100%;max-width:480px;max-height:80vh;display:flex;flex-direction:column;',
            'box-shadow:0 20px 50px -10px rgba(0,0,0,0.5);}',
            '.cp-header{display:flex;align-items:center;justify-content:space-between;',
            'padding:18px 20px;border-bottom:1px solid rgba(255,255,255,0.06);}',
            '.cp-title{color:#fff;font-size:16px;font-weight:600;margin:0;}',
            '.cp-close{background:none;border:none;color:#a0a5b5;cursor:pointer;padding:4px;',
            'display:flex;align-items:center;justify-content:center;border-radius:6px;}',
            '.cp-close:hover{background:rgba(255,255,255,0.06);color:#fff;}',
            '.cp-body{padding:10px;overflow-y:auto;flex:1;}',
            /* Row: item de seleção + botão olho lado a lado */
            '.cp-row{display:flex;align-items:center;gap:4px;border-radius:10px;',
            'border:1px solid transparent;transition:border-color .15s;}',
            '.cp-row:hover{border-color:rgba(255,255,255,0.1);}',
            '.cp-item{display:flex;align-items:center;gap:12px;flex:1;min-width:0;',
            'background:transparent;border:none;border-radius:10px;padding:12px 8px 12px 12px;',
            'cursor:pointer;text-align:left;transition:background .15s;color:#fff;}',
            '.cp-item:hover{background:rgba(255,255,255,0.04);}',
            /* Botão olho */
            '.cp-eye-btn{flex-shrink:0;background:none;border:none;cursor:pointer;',
            'color:#a0a5b5;padding:8px;display:flex;align-items:center;justify-content:center;',
            'border-radius:6px;transition:color .15s,background .15s;}',
            '.cp-eye-btn:hover{color:#fff;background:rgba(255,255,255,0.08);}',
            '.cp-item__icon{width:36px;height:36px;border-radius:8px;background:rgba(99,102,241,0.12);',
            'display:flex;align-items:center;justify-content:center;flex-shrink:0;color:#6366f1;}',
            '.cp-item__info{flex:1;min-width:0;}',
            '.cp-item__label{display:inline-flex;align-items:center;gap:6px;font-size:13px;',
            'font-weight:600;padding:2px 10px;border-radius:20px;margin-bottom:4px;}',
            '.cp-item__dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}',
            '.cp-item__file{font-size:13px;color:#a0a5b5;white-space:nowrap;overflow:hidden;',
            'text-overflow:ellipsis;}',
            '.cp-item__date{font-size:12px;color:#6b7280;flex-shrink:0;padding-right:4px;}',
            '.cp-empty{padding:40px 20px;text-align:center;color:#a0a5b5;font-size:14px;}',
            '.cp-loading{padding:40px 20px;text-align:center;color:#a0a5b5;font-size:14px;}',
            '.cp-error{padding:40px 20px;text-align:center;color:#f87171;font-size:14px;}',
            /* Modal de preview de PDF (inline no picker) */
            '.cp-pdf-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.82);display:flex;',
            'align-items:center;justify-content:center;z-index:10000;padding:20px;',
            'font-family:system-ui,-apple-system,sans-serif;}',
            '.cp-pdf-modal{background:#1e1f2e;border:1px solid rgba(255,255,255,0.1);border-radius:10px;',
            'width:100%;max-width:900px;height:90vh;display:flex;flex-direction:column;',
            'box-shadow:0 25px 60px -15px rgba(0,0,0,0.6);overflow:hidden;}',
            '.cp-pdf-header{display:flex;align-items:center;justify-content:space-between;',
            'padding:12px 16px;border-bottom:1px solid rgba(255,255,255,0.07);background:#161722;}',
            '.cp-pdf-title{color:#fff;font-size:14px;font-weight:600;margin:0;white-space:nowrap;',
            'overflow:hidden;text-overflow:ellipsis;padding-right:12px;}',
            '.cp-pdf-actions{display:flex;gap:6px;align-items:center;flex-shrink:0;}',
            '.cp-pdf-btn{background:none;border:none;cursor:pointer;color:#a0a5b5;padding:6px;',
            'display:flex;align-items:center;justify-content:center;border-radius:6px;',
            'transition:color .15s,background .15s;}',
            '.cp-pdf-btn:hover{color:#fff;background:rgba(255,255,255,0.08);}',
            '.cp-pdf-body{flex:1;position:relative;background:#525659;}',
            '.cp-pdf-iframe{width:100%;height:100%;border:none;}'
        ].join('');
        document.head.appendChild(style);
    }

    function hexToRgba(hex, alpha) {
        var h = (hex || COR_PADRAO).replace('#', '');
        var r = parseInt(h.substring(0, 2), 16);
        var g = parseInt(h.substring(2, 4), 16);
        var b = parseInt(h.substring(4, 6), 16);
        return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
    }

    function escapeHtml(s) {
        if (s == null) return '';
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function formatDate(iso) {
        try {
            var d = new Date(iso);
            return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
        } catch (e) {
            return '';
        }
    }

    // ── Modal de visualização de PDF ─────────────────────────────────────
    function openPdfPreview(id, label) {
        var overlay = document.createElement('div');
        overlay.className = 'cp-pdf-overlay';

        var iconX    = window.lucide ? '<i data-lucide="x"></i>'        : '&times;';
        var iconDl   = window.lucide ? '<i data-lucide="download"></i>' : '&#8595;';
        var iconBack = window.lucide ? '<i data-lucide="arrow-left"></i>' : '&larr;';

        overlay.innerHTML =
            '<div class="cp-pdf-modal" role="dialog" aria-label="Visualizar PDF">' +
                '<div class="cp-pdf-header">' +
                    '<h3 class="cp-pdf-title">' + escapeHtml(label) + '</h3>' +
                    '<div class="cp-pdf-actions">' +
                        '<button type="button" class="cp-pdf-btn cp-pdf-back" title="Voltar à lista">' + iconBack + '</button>' +
                        '<button type="button" class="cp-pdf-btn cp-pdf-download" title="Baixar PDF">' + iconDl + '</button>' +
                        '<button type="button" class="cp-pdf-btn cp-pdf-close" title="Fechar (Esc)">' + iconX + '</button>' +
                    '</div>' +
                '</div>' +
                '<div class="cp-pdf-body">' +
                    '<iframe class="cp-pdf-iframe" src="/curriculos/pdf/' + escapeHtml(String(id)) + '"></iframe>' +
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

        overlay.querySelector('.cp-pdf-close').addEventListener('click', close);
        overlay.querySelector('.cp-pdf-back').addEventListener('click', close);
        overlay.querySelector('.cp-pdf-download').addEventListener('click', function () {
            window.location.href = '/curriculos/download/' + id;
        });
        overlay.addEventListener('click', function (e) {
            if (e.target === overlay) close();
        });
        document.addEventListener('keydown', onKeyDown);
    }

    // ── Modal principal do picker ────────────────────────────────────────
    function open(onSelect) {
        injectStyles();

        var overlay = document.createElement('div');
        overlay.className = 'cp-overlay';
        overlay.innerHTML =
            '<div class="cp-modal" role="dialog" aria-label="Selecionar currículo salvo">' +
                '<div class="cp-header">' +
                    '<h3 class="cp-title">Selecionar currículo salvo</h3>' +
                    '<button type="button" class="cp-close" aria-label="Fechar">' +
                        (window.lucide ? '<i data-lucide="x"></i>' : '&times;') +
                    '</button>' +
                '</div>' +
                '<div class="cp-body" id="cp-body"><div class="cp-loading">Carregando currículos…</div></div>' +
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

        overlay.querySelector('.cp-close').addEventListener('click', close);
        overlay.addEventListener('click', function (e) {
            if (e.target === overlay) close();
        });
        document.addEventListener('keydown', onKeyDown);

        fetch('/curriculos/lista')
            .then(function (res) {
                if (!res.ok) throw new Error('Erro ao carregar currículos');
                return res.json();
            })
            .then(function (data) {
                var body = overlay.querySelector('#cp-body');
                var curriculos = data.curriculos || [];

                if (!curriculos.length) {
                    body.innerHTML = '<div class="cp-empty">Nenhum currículo salvo ainda. Envie um arquivo normalmente.</div>';
                    return;
                }

                var iconEye  = window.lucide ? '<i data-lucide="eye"></i>' : '&#128065;';
                var iconFile = window.lucide ? '<i data-lucide="file-text"></i>' : '';

                body.innerHTML = curriculos.map(function (c) {
                    var cor = c.cor || COR_PADRAO;
                    var labelStyle = 'color:' + cor + ';background:' + hexToRgba(cor, 0.12) + ';';
                    return (
                        '<div class="cp-row">' +
                            '<button type="button" class="cp-item" data-id="' + escapeHtml(c.id) + '">' +
                                '<span class="cp-item__icon">' + iconFile + '</span>' +
                                '<span class="cp-item__info">' +
                                    '<span class="cp-item__label" style="' + escapeHtml(labelStyle) + '">' +
                                        '<span class="cp-item__dot" style="background:' + escapeHtml(cor) + ';"></span>' +
                                        escapeHtml(c.label) +
                                    '</span>' +
                                    '<div class="cp-item__file">' + escapeHtml(c.arquivo_nome || '') + '</div>' +
                                '</span>' +
                                '<span class="cp-item__date">' + escapeHtml(formatDate(c.criado_em)) + '</span>' +
                            '</button>' +
                            '<button type="button" class="cp-eye-btn" ' +
                                'data-id="' + escapeHtml(c.id) + '" ' +
                                'data-label="' + escapeHtml(c.label) + '" ' +
                                'title="Visualizar PDF" aria-label="Visualizar PDF de ' + escapeHtml(c.label) + '">' +
                                iconEye +
                            '</button>' +
                        '</div>'
                    );
                }).join('');

                if (window.lucide) lucide.createIcons({ nodes: [body] });

                // Clique no item → selecionar currículo
                Array.prototype.forEach.call(body.querySelectorAll('.cp-item'), function (btn) {
                    btn.addEventListener('click', function () {
                        var id = btn.getAttribute('data-id');
                        var escolhido = curriculos.filter(function (c) { return c.id === id; })[0];
                        close();
                        if (escolhido && typeof onSelect === 'function') onSelect(escolhido);
                    });
                });

                // Clique no olho → abrir preview sem fechar o picker
                Array.prototype.forEach.call(body.querySelectorAll('.cp-eye-btn'), function (btn) {
                    btn.addEventListener('click', function (e) {
                        e.stopPropagation();
                        var id    = btn.getAttribute('data-id');
                        var label = btn.getAttribute('data-label') || 'Currículo';
                        openPdfPreview(id, label);
                    });
                });
            })
            .catch(function () {
                overlay.querySelector('#cp-body').innerHTML =
                    '<div class="cp-error">Não foi possível carregar seus currículos. Tente novamente.</div>';
            });
    }

    window.CurriculoPicker = { open: open };
})();