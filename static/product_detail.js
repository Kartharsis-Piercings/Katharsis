// --- LÓGICA MEJORADA DE LA GALERÍA DE IMÁGENES ---
const track = document.querySelector('.carousel-track-main');
// Solo activar si hay imágenes y más de una
if (track && track.children.length > 0) {
    const slides = Array.from(track.children);
    const thumbnails = document.querySelectorAll('.thumbnails img');
    let currentIndex = 0;

    // Función central para mover el carrusel y actualizar las miniaturas
    const moveToSlide = (newIndex) => {
        // Mueve el track del carrusel
        track.style.transform = `translateX(-${100 * newIndex}%)`;

        // Actualiza la clase 'active' en la miniatura correspondiente
        thumbnails[currentIndex].classList.remove('active');
        thumbnails[newIndex].classList.add('active');

        currentIndex = newIndex;
    };

    // Event listeners para los botones del carrusel (solo si hay más de una imagen)
    if (slides.length > 1) {
        const nextButton = document.querySelector('.carousel-button-main.next');
        const prevButton = document.querySelector('.carousel-button-main.prev');

        nextButton.addEventListener('click', () => {
            const nextIndex = (currentIndex + 1) % slides.length; // Bucle hacia adelante
            moveToSlide(nextIndex);
        });

        prevButton.addEventListener('click', () => {
            const prevIndex = (currentIndex - 1 + slides.length) % slides.length; // Bucle hacia atrás
            moveToSlide(prevIndex);
        });
    } else {
        // Oculta los botones si solo hay una imagen
        document.querySelector('.carousel-button-main.next').style.display = 'none';
        document.querySelector('.carousel-button-main.prev').style.display = 'none';
    }


    // Event listeners para las miniaturas
    thumbnails.forEach((thumb, index) => {
        thumb.addEventListener('click', () => {
            moveToSlide(index);
        });
    });
}

// Controles de cantidad
document.querySelector('.quantity-btn.plus').addEventListener('click', () => {
    const input = document.getElementById('quantity');
    input.value = parseInt(input.value) + 1;
});

document.querySelector('.quantity-btn.minus').addEventListener('click', () => {
    const input = document.getElementById('quantity');
    if (parseInt(input.value) > 1) {
        input.value = parseInt(input.value) - 1;
    }
});

// --- AÑADIR AL CARRITO CON AJAX ---
document.querySelector('.add-to-cart-form').addEventListener('submit', async function(e) {
    e.preventDefault(); // Prevenimos la recarga de la página

    const form = this;
    const btn = form.querySelector('.btn-add-cart');
    const sizeSelect = form.querySelector('select[name="size"]');

    // Validación simple
    if (!sizeSelect.value) {
        alert('Por favor, selecciona un tamaño.');
        return;
    }

    // Guardamos el estado original del botón
    const originalText = btn.textContent;
    const originalBg = btn.style.backgroundColor;

    // Mostramos feedback visual en el botón
    btn.textContent = '✓ Añadido';
    btn.style.backgroundColor = '#4CAF50'; // Verde éxito
    btn.disabled = true;

    try {
        const formData = new FormData(form);
        const response = await fetch("{{ url_for('add_to_cart') }}", {
            method: 'POST',
            body: formData
        });

        if (response.ok && data.status === 'success') {
            // Actualizamos el contador del carrito en el header
            const data = await response.json();
            const cartCountEl = document.querySelector('.cart-count');
            if (cartCountEl) {
                cartCountEl.textContent = data.cart_count; // Actualiza el número
                // La animación que ya tienes funcionará perfecto aquí
                cartCountEl.classList.add('animate');
                setTimeout(() => cartCountEl.classList.remove('animate'), 500);
            }
        } else {
            alert(data.message || 'Hubo un error al añadir el producto.');
        }

    } catch (error) {
        console.error('Error al añadir al carrito:', error);
        alert('Error de conexión. Inténtalo de nuevo.');
    } finally {
        // Restauramos el botón después de un par de segundos
        setTimeout(() => {
            btn.textContent = originalText;
            btn.style.backgroundColor = originalBg;
            btn.disabled = false;
        }, 2000);
    }
});

// --- LÓGICA DEL ACORDEÓN ---
const accordionHeaders = document.querySelectorAll('.accordion-header');
accordionHeaders.forEach(header => {
    header.addEventListener('click', () => {
        const accordionItem = header.parentElement;
        const accordionContent = header.nextElementSibling;
        
        // Cierra otros acordeones abiertos para que solo uno esté abierto a la vez
        document.querySelectorAll('.accordion-item').forEach(item => {
            if (item !== accordionItem && item.classList.contains('active')) {
                item.classList.remove('active');
                item.querySelector('.accordion-content').style.maxHeight = null;
            }
        });

        // Abre o cierra el acordeón clickeado
        accordionItem.classList.toggle('active');
        if (accordionItem.classList.contains('active')) {
            accordionContent.style.maxHeight = accordionContent.scrollHeight + "px";
        } else {
            accordionContent.style.maxHeight = null;
        }
    });
});
