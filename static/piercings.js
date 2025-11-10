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

    // --- 2. LÓGICA DE SCROLL MANUAL (VERSIÓN CORREGIDA) ---
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Prevenimos el salto de ancla por defecto
            e.preventDefault(); 
            
            // Cerramos el menú si está abierto (en móvil)
            if (guideNavList.classList.contains('active')) {
                guideNavList.classList.remove('active');
            }

            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);

            if (targetElement) {
                // --- Cálculo del Offset Fijo ---
                
                // Altura del header principal (sabemos que es 60px)
                const headerOffset = 60; 
                
                // Altura de la barra de navegación "sticky"
                let navBarOffset = 0;
                
                // Detectamos si estamos en vista móvil o escritorio
                if (window.innerWidth <= 900) {
                    // En móvil, el offset es la altura del botón morado
                    // (que tiene 1rem de padding (16px*2=32) + font-size ~16px = ~48px)
                    // Usamos la altura sticky del CSS: 68px
                    navBarOffset = 68;
                } else {
                    // En escritorio, el offset es la altura sticky del nav: 100px
                    navBarOffset = 100;
                }
                
                // Búfer adicional para que no quede pegado
                const buffer = 15;
                
                // En móvil, queremos que el offset sea menor que en escritorio
                // Si estamos en móvil (window.innerWidth <= 900), usamos el offset de 68px del CSS
                // Si estamos en escritorio, usamos el de 100px.
                
                let totalOffset;
                
                if (window.innerWidth <= 900) {
                    // Offset para MÓVIL (Header + Botón Navegación + Buffer)
                    totalOffset = 60 + 68 + buffer; // Aprox 143px
                } else {
                    // Offset para ESCRITORIO (Header (que desaparece) + Nav Sticky + Buffer)
                    totalOffset = 100 + buffer; // Aprox 115px (como lo tenías en el CSS)
                }

                // --- Cálculo de la Posición ---
                const elementPosition = targetElement.getBoundingClientRect().top;
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