(function () {
    'use strict';

    const sidebar = document.getElementById('sidebar');
    const toggle = document.getElementById('sidebar-toggle');

    if (toggle && sidebar) {
        toggle.addEventListener('click', function () {
            const collapsed = sidebar.classList.toggle('sidebar--collapsed');
            toggle.setAttribute('aria-expanded', String(!collapsed));
            toggle.setAttribute('aria-label', collapsed ? 'Expandir menu' : 'Contrair menu');
        });
    }
})();
