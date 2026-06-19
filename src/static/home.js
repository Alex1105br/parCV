(function () {
    'use strict';

    // ===== Sidebar toggle =====
    const sidebar = document.getElementById('sidebar');
    const toggle  = document.getElementById('sidebar-toggle');

    if (toggle && sidebar) {
        toggle.addEventListener('click', function () {
            const collapsed = sidebar.classList.toggle('sidebar--collapsed');
            toggle.setAttribute('aria-expanded', String(!collapsed));
            toggle.setAttribute('aria-label', collapsed ? 'Expandir menu' : 'Contrair menu');
        });
    }

    // ===== Estatísticas do usuário =====
    async function loadStats() {
        try {
            // Carrega total de análises e melhor score
            const resp = await fetch('/analises?page=1&per_page=50');
            if (!resp.ok) return;
            const data = await resp.json();

            const totalAnalises = data.total || 0;
            document.getElementById('stat-analises').textContent = totalAnalises;

            if (data.analises && data.analises.length > 0) {
                const bestScore = Math.max(...data.analises.map(function(a) { return a.score_total || 0; }));
                document.getElementById('stat-score').textContent = bestScore + '/100';
            } else {
                document.getElementById('stat-score').textContent = '—';
            }
        } catch (_) {
            // Silencia erros de rede — stats são informativos, não críticos
        }
    }

    loadStats();
})();
