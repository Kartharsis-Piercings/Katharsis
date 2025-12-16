/**
 * Esta función asigna todos los eventos necesarios a las tarjetas de producto
 * (Vista Rápida, Wishlist, Añadir al Carrito) para que sean interactivas.
 */
function setupProductCardListeners() {
    const quickViewModal = document.querySelector('.quick-view-modal');
    const modalProduct = document.querySelector('.modal-product');

    // 1. Lógica para VISTA RÁPIDA
    document.querySelectorAll('.quick-view').forEach(btn => {
        // Evita reasignar el mismo evento
        if (btn.dataset.listenerAttached) return;

        btn.addEventListener('click', async function() {
            const productId = this.getAttribute('data-product-id');
            if (!productId || !quickViewModal || !modalProduct) return;

            modalProduct.innerHTML = '<p>Cargando...</p>';
            quickViewModal.classList.add('active');
            document.body.style.overflow = 'hidden';

            try {
                const response = await fetch(`/api/product/${productId}`);
                const product = await response.json();
                // Aquí va tu lógica para construir el HTML del modal
                modalProduct.innerHTML = `
                    <div class="modal-product-info">
                        <h2>${product.name}</h2>
                        <p>${product.description}</p>
                        </div>`;
            } catch (error) {
                console.error('Error al cargar producto para vista rápida:', error);
                modalProduct.innerHTML = '<p>Error al cargar el producto.</p>';
            }
        });
        btn.dataset.listenerAttached = 'true';
    });

    // 2. WISHLIST (Lógica Completada)
    document.querySelectorAll('.btn-wishlist').forEach(btn => {
        if (btn.dataset.listenerAttached) return;
        
        btn.addEventListener('click', async function(e) {
            e.preventDefault();
            const productId = this.dataset.productId;
            const icon = this.querySelector('i');
            
            try {
                const response = await fetch('/toggle_wishlist', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ product_id: productId })
                });
                const data = await response.json();
                
                if (data.status === 'success') {
                    if (data.action === 'added') {
                        this.classList.add('active');
                        icon.classList.remove('far'); // Corazón vacío
                        icon.classList.add('fas');    // Corazón lleno
                        icon.style.color = '#ff5252';
                    } else {
                        this.classList.remove('active');
                        icon.classList.remove('fas');
                        icon.classList.add('far');
                        icon.style.color = ''; // Volver al color original
                    }
                }
            } catch (error) {
                console.error('Error wishlist:', error);
            }
        });
        btn.dataset.listenerAttached = 'true';
    });

    // 3. AÑADIR AL CARRITO (Cards Normales)
    // Usamos la clase .add-to-cart-form que definimos en el HTML
    document.querySelectorAll('.add-to-cart-form').forEach(form => {
        if (form.dataset.listenerAttached) return;
        form.addEventListener('submit', handleAddToCartSubmit);
        form.dataset.listenerAttached = 'true';
    });
}

// Ejecutar la función cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    setupProductCardListeners();

    // Lógica para cerrar el modal (debe estar aquí también)
    const quickViewModal = document.querySelector('.quick-view-modal');
    const closeModalBtn = document.querySelector('.close-modal');

    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', () => {
            quickViewModal.classList.remove('active');
            document.body.style.overflow = 'auto';
        });
    }
    if (quickViewModal) {
        quickViewModal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.remove('active');
                document.body.style.overflow = 'auto';
            }
        });
    }
});