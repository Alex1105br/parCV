(function () {
    'use strict';

    // Aplica o tema salvo imediatamente (evita flash; chamado também pelo
    // script inline no <head> de base.html — esta função é idempotente).
    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);

        // Atualiza label e ícone do botão, se existir na página
        var btn   = document.getElementById('theme-toggle');
        if (!btn) return;

        var label = btn.querySelector('.sidebar__theme-label');
        if (label) {
            label.textContent = theme === 'light' ? 'Modo escuro' : 'Modo claro';
        }
        btn.setAttribute('aria-label',
            theme === 'light' ? 'Ativar modo escuro' : 'Ativar modo claro');
    }

    // Aplica na carga (complementa o script inline do <head>)
    var saved = localStorage.getItem('parcv-theme') || 'dark';
    applyTheme(saved);

    document.addEventListener('DOMContentLoaded', function () {
        var btn = document.getElementById('theme-toggle');
        if (!btn) return;

        btn.addEventListener('click', function () {
            var current = document.documentElement.getAttribute('data-theme') || 'dark';
            var next    = current === 'dark' ? 'light' : 'dark';
            localStorage.setItem('parcv-theme', next);
            applyTheme(next);
            // Reinicializa ícones Lucide para trocar sun ↔ moon
            if (window.lucide) lucide.createIcons();
        });
    });
})();