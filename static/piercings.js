// static/piercings.js

document.addEventListener('DOMContentLoaded', () => {
    const navToggleBtn = document.getElementById('nav-toggle-btn');
    const guideNavList = document.getElementById('guide-nav-list');
    
    // Salir si no estamos en la vista de guía (no hay botón)
    if (!navToggleBtn || !guideNavList) return;

    const navLinks = guideNavList.querySelectorAll('a');

    // 1. Lógica para desplegar/colapsar el menú (sin cambios)
    navToggleBtn.addEventListener('click', () => {
        guideNavList.classList.toggle('active');
    });

    // --- 2. LÓGICA DE SCROLL MANUAL (MEJORADA) ---
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Prevenimos el salto de ancla por defecto del navegador
            e.preventDefault(); 
            
            // Cerramos el menú si está abierto
            if (guideNavList.classList.contains('active')) {
                guideNavList.classList.remove('active');
            }

            // Obtenemos el ID del ancla (ej: "#oreja")
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);

            if (targetElement) {
                // --- Cálculo del Offset ---
                
                // Obtenemos la altura del header principal (asumimos 60px)
                const headerOffset = 60; 
                
                // Obtenemos la altura real del botón morado "Navegación"
                const navBarOffset = navToggleBtn.offsetHeight;
                
                // Sumamos ambas alturas y un pequeño búfer de 15px
                const totalOffset = headerOffset + navBarOffset + 15;

                // --- Cálculo de la Posición ---
                // Obtenemos la posición del elemento relativa a la ventana
                const elementPosition = targetElement.getBoundingClientRect().top;
                // Sumamos el scroll actual de la página y restamos nuestro offset
                const offsetPosition = elementPosition + window.pageYOffset - totalOffset;

                // Hacemos scroll suave a esa posición calculada
                window.scrollTo({
                    top: offsetPosition,
                    behavior: "smooth"
                });
            }
        });
    });
});