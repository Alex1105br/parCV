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
            '.cp-item{display:flex;align-items:center;gap:12px;width:100%;background:transparent;',
            'border:1px solid transparent;border-radius:10px;padding:12px;cursor:pointer;',
            'text-align:left;transition:background .15s,border-color .15s;color:#fff;}',
            '.cp-item:hover{background:rgba(255,255,255,0.05);border-color:rgba(255,255,255,0.1);}',
            '.cp-item__icon{width:36px;height:36px;border-radius:8px;background:rgba(99,102,241,0.12);',
            'display:flex;align-items:center;justify-content:center;flex-shrink:0;color:#6366f1;}',
            '.cp-item__info{flex:1;min-width:0;}',
            '.cp-item__label{display:inline-flex;align-items:center;gap:6px;font-size:13px;',
            'font-weight:600;padding:2px 10px;border-radius:20px;margin-bottom:4px;}',
            '.cp-item__dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}',
            '.cp-item__file{font-size:13px;color:#a0a5b5;white-space:nowrap;overflow:hidden;',
            'text-overflow:ellipsis;}',
            '.cp-item__date{font-size:12px;color:#6b7280;flex-shrink:0;}',
            '.cp-empty{padding:40px 20px;text-align:center;color:#a0a5b5;font-size:14px;}',
            '.cp-loading{padding:40px 20px;text-align:center;color:#a0a5b5;font-size:14px;}',
            '.cp-error{padding:40px 20px;text-align:center;color:#f87171;font-size:14px;}'
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

                body.innerHTML = curriculos.map(function (c) {
                    var cor = c.cor || COR_PADRAO;
                    var labelStyle = 'color:' + cor + ';background:' + hexToRgba(cor, 0.12) + ';';
                    return (
                        '<button type="button" class="cp-item" data-id="' + escapeHtml(c.id) + '">' +
                            '<span class="cp-item__icon">' + (window.lucide ? '<i data-lucide="file-text"></i>' : '') + '</span>' +
                            '<span class="cp-item__info">' +
                                '<span class="cp-item__label" style="' + escapeHtml(labelStyle) + '">' +
                                    '<span class="cp-item__dot" style="background:' + escapeHtml(cor) + ';"></span>' +
                                    escapeHtml(c.label) +
                                '</span>' +
                                '<div class="cp-item__file">' + escapeHtml(c.arquivo_nome || '') + '</div>' +
                            '</span>' +
                            '<span class="cp-item__date">' + escapeHtml(formatDate(c.criado_em)) + '</span>' +
                        '</button>'
                    );
                }).join('');

                if (window.lucide) lucide.createIcons({ nodes: [body] });

                Array.prototype.forEach.call(body.querySelectorAll('.cp-item'), function (btn) {
                    btn.addEventListener('click', function () {
                        var id = btn.getAttribute('data-id');
                        var escolhido = curriculos.filter(function (c) { return c.id === id; })[0];
                        close();
                        if (escolhido && typeof onSelect === 'function') onSelect(escolhido);
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
