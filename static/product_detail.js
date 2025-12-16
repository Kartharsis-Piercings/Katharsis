// static/product_detail.js

// --- LÓGICA DE LA GALERÍA DE IMÁGENES ---
const track = document.querySelector('.carousel-track-main');

if (track && track.children.length > 0) {
    const slides = Array.from(track.children);
    const thumbnails = document.querySelectorAll('.thumbnails img');
    let currentIndex = 0;

    // Función central para mover el carrusel
    const moveToSlide = (newIndex) => {
        track.style.transform = `translateX(-${100 * newIndex}%)`;

        // Actualizar miniaturas activas
        if(thumbnails.length > 0 && thumbnails[currentIndex]) {
            thumbnails[currentIndex].classList.remove('active');
        }
        if(thumbnails.length > 0 && thumbnails[newIndex]) {
            thumbnails[newIndex].classList.add('active');
        }

        currentIndex = newIndex;
    };

    // Botones (solo si hay más de 1 imagen)
    if (slides.length > 1) {
        const nextButton = document.querySelector('.carousel-button-main.next');
        const prevButton = document.querySelector('.carousel-button-main.prev');

        if(nextButton) {
            nextButton.addEventListener('click', () => {
                const nextIndex = (currentIndex + 1) % slides.length;
                moveToSlide(nextIndex);
            });
        }

        if(prevButton) {
            prevButton.addEventListener('click', () => {
                const prevIndex = (currentIndex - 1 + slides.length) % slides.length;
                moveToSlide(prevIndex);
            });
        }
    } else {
        // Ocultar botones si es imagen única
        const nextBtn = document.querySelector('.carousel-button-main.next');
        const prevBtn = document.querySelector('.carousel-button-main.prev');
        if(nextBtn) nextBtn.style.display = 'none';
        if(prevBtn) prevBtn.style.display = 'none';
    }

    // Clic en miniaturas
    thumbnails.forEach((thumb, index) => {
        thumb.addEventListener('click', () => {
            moveToSlide(index);
        });
    });
}

// Swipe en Móvil
const mainCarousel = document.querySelector('.main-image-carousel');
if (mainCarousel) {
    let touchStartX = 0;
    let touchEndX = 0;
    const swipeThreshold = 50;

    mainCarousel.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });

    mainCarousel.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    }, { passive: true });

    function handleSwipe() {
        const swipeDistance = touchEndX - touchStartX;
        const nextBtn = document.querySelector('.carousel-button-main.next');
        const prevBtn = document.querySelector('.carousel-button-main.prev');

        if (swipeDistance < -swipeThreshold && nextBtn) {
            nextBtn.click();
        } else if (swipeDistance > swipeThreshold && prevBtn) {
            prevBtn.click();
        }
        touchStartX = 0;
        touchEndX = 0;
    }
}

// --- CONTROLES DE CANTIDAD ---
const btnPlus = document.querySelector('.quantity-btn.plus');
const btnMinus = document.querySelector('.quantity-btn.minus');

if(btnPlus) {
    btnPlus.addEventListener('click', () => {
        const input = document.getElementById('quantity');
        if(input) input.value = parseInt(input.value) + 1;
    });
}

if(btnMinus) {
    btnMinus.addEventListener('click', () => {
        const input = document.getElementById('quantity');
        if (input && parseInt(input.value) > 1) {
            input.value = parseInt(input.value) - 1;
        }
    });
}

// --- AÑADIR AL CARRITO (CORREGIDO) ---
const addToCartForm = document.querySelector('.add-to-cart-form');

if (addToCartForm) {
    addToCartForm.addEventListener('submit', async function(e) {
        e.preventDefault(); 

        const form = this;
        const btn = form.querySelector('.btn-add-cart');
        const sizeSelect = form.querySelector('select[name="size"]');

        // 1. Validación
        if (sizeSelect && !sizeSelect.value) {
            alert('Por favor, selecciona un tamaño.');
            return;
        }

        // 2. Estado Visual de Carga
        const originalText = btn.textContent;
        const originalBg = btn.style.backgroundColor;
        
        btn.textContent = 'Añadiendo...';
        btn.disabled = true;

        try {
            const formData = new FormData(form);
            
            // CORRECCIÓN CRÍTICA: Usamos la variable global addToCartUrl definida en el HTML
            // en lugar de usar Jinja {{ url_for }} aquí.
            const response = await fetch(addToCartUrl, {
                method: 'POST',
                body: formData
            });

            // CORRECCIÓN LÓGICA: Parseamos JSON antes de usar 'data'
            const data = await response.json();

            if (response.ok && data.status === 'success') {
                // Éxito Visual
                btn.textContent = '✓ Añadido';
                btn.style.backgroundColor = '#4CAF50'; 

                // Actualizar contador del header
                const cartCountEl = document.querySelector('.cart-count');
                if (cartCountEl) {
                    cartCountEl.textContent = data.cart_count;
                    cartCountEl.classList.add('animate'); // Asegúrate de tener CSS para esta clase si quieres animación
                    setTimeout(() => cartCountEl.classList.remove('animate'), 500);
                }
            } else {
                // Error del servidor (ej. sin stock)
                alert(data.message || 'Hubo un error al añadir el producto.');
                // Revertir visualmente si falló la lógica de negocio
                btn.textContent = originalText;
                btn.style.backgroundColor = originalBg;
            }

        } catch (error) {
            console.error('Error al añadir al carrito:', error);
            alert('Error de conexión. Inténtalo de nuevo.');
            btn.textContent = originalText;
            btn.style.backgroundColor = originalBg;
        } finally {
            // Restaurar botón después de 2 segundos (solo si fue éxito)
            if (btn.textContent === '✓ Añadido') {
                setTimeout(() => {
                    btn.textContent = originalText;
                    btn.style.backgroundColor = originalBg;
                    btn.disabled = false;
                }, 2000);
            } else {
                btn.disabled = false;
            }
        }
    });
}

// --- LÓGICA DEL ACORDEÓN ---
const accordionHeaders = document.querySelectorAll('.accordion-header');
accordionHeaders.forEach(header => {
    header.addEventListener('click', () => {
        const accordionItem = header.parentElement;
        const accordionContent = header.nextElementSibling;
        
        // Cierra otros acordeones
        document.querySelectorAll('.accordion-item').forEach(item => {
            if (item !== accordionItem && item.classList.contains('active')) {
                item.classList.remove('active');
                item.querySelector('.accordion-content').style.maxHeight = null;
            }
        });

        // Alternar el actual
        accordionItem.classList.toggle('active');
        if (accordionItem.classList.contains('active')) {
            accordionContent.style.maxHeight = accordionContent.scrollHeight + "px";
        } else {
            accordionContent.style.maxHeight = null;
        }
    });
});