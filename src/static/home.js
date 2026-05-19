(function () {
    'use strict';

    const sidebar = document.getElementById('sidebar');
    const toggle = document.getElementById('sidebar-toggle');

    if (toggle && sidebar) {
        toggle.addEventListener('click', function () {
            const isHidden = sidebar.classList.toggle('sidebar--hidden');
            toggle.setAttribute('aria-expanded', String(!isHidden));
        });
    }
})();
