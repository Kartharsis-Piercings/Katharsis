document.addEventListener('DOMContentLoaded', () => {
    const navToggleBtn = document.getElementById('nav-toggle-btn');
    const guideNavList = document.getElementById('guide-nav-list');
    const navLinks = guideNavList.querySelectorAll('a');

    if (navToggleBtn && guideNavList) {
        // 1. Lógica para desplegar/colapsar el menú
        navToggleBtn.addEventListener('click', () => {
            guideNavList.classList.toggle('active');
        });

        // 2. Lógica para cerrar el menú al hacer clic en un enlace
        navLinks.forEach(link => {
            link.addEventListener('click', () => {
                if (guideNavList.classList.contains('active')) {
                    guideNavList.classList.remove('active');
                }
            });
        });
    }
});