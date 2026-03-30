function irParaChat() {
    window.location.href = "/chat";
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggle = document.querySelector('.menu-toggle');
    if (sidebar && toggle) {
        const isHidden = sidebar.classList.toggle('hide');
        toggle.classList.toggle('active', !isHidden);
        document.body.classList.toggle('sidebar-open', !isHidden);
    }
}
