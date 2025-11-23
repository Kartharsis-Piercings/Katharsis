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

    // --- 2. FUNCIÓN DE SCROLL CENTRALIZADA ---
    /**
     * Calcula la posición correcta del ancla y se desplaza suavemente.
     * @param {string} anchorId - El ID del elemento al que saltar (ej: "#oreja").
     */
    function scrollToAnchor(anchorId) {
        const targetElement = document.querySelector(anchorId);
        if (!targetElement) return;

        // --- Cálculo del Offset Fijo ---
        // Usamos los valores fijos del CSS para máxima fiabilidad.
        
        let offsetPx = 115; // Offset de ESCRITORIO (top: 100px + 15px buffer)

        if (window.innerWidth <= 900) {
            // Offset para MÓVIL (usamos el valor de scroll-margin-top: 125px del CSS)
            offsetPx = 125; 
        }

        const elementPosition = targetElement.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.pageYOffset - offsetPx;

        // --- Corrección Crucial para iOS (iPhone) ---
        // Usamos setTimeout(..., 0) para asegurar que el scroll ocurra
        // DESPUÉS de que el navegador termine de procesar el clic (y cerrar el menú).
        // Esto evita que iOS "luche" contra el scroll.
        setTimeout(() => {
            window.scrollTo({
                top: offsetPosition,
                behavior: "smooth"
            });
        }, 0); // 0ms de retraso es suficiente para pasarlo al siguiente 'tick'
    }

    // --- 3. ASIGNAR EVENTO A LOS ENLACES DE NAVEGACIÓN (Problema 1) ---
    // Esto maneja los clics en el menú lateral morado.
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault(); // Detener el salto por defecto
            
            // Cerrar el menú si está activo (en móvil)
            if (guideNavList.classList.contains('active')) {
                guideNavList.classList.remove('active');
            }
            
            const targetId = this.getAttribute('href');
            scrollToAnchor(targetId); // Llama a nuestra función central
        });
    });

    // --- 4. NUEVO: MANEJAR SCROLL EN CARGA DE PÁGINA (Problema 2) ---
    // Esto se ejecuta cuando vienes desde index.html con un #ancla.
    // Usamos 'load' en lugar de 'DOMContentLoaded' para esperar a que
    // el CSS y las imágenes se carguen y el layout sea estable.
    window.addEventListener('load', () => {
        if (window.location.hash) {
            // Se usa setTimeout para dar tiempo al navegador a pintar
            // todo antes de que intentemos calcular la posición.
            setTimeout(() => {
                scrollToAnchor(window.location.hash);
            }, 100); // 100ms de retraso para asegurar renderizado completo.
        }
    });

}); // Fin de DOMContentLoaded