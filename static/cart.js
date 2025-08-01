document.addEventListener('DOMContentLoaded', () => {
    
    // --- MANEJO DEL MODAL DE PAGO ---
    const checkoutBtn = document.getElementById('checkout-btn');
    const yapeModal = document.getElementById('yape-payment-modal');
    const closeModalBtn = document.getElementById('close-yape-modal');
    const yapeForm = document.getElementById('yape-verification-form');
    const verificationStatus = document.getElementById('verification-status');
    const termsCheckbox = document.getElementById('terms-checkbox');

    // Nos aseguramos de que todos los elementos existan antes de añadir listeners
    if (checkoutBtn && termsCheckbox && yapeModal) {

        // Función para actualizar el estado del botón (visual)
        const updateButtonState = () => {
            checkoutBtn.disabled = !termsCheckbox.checked;
        };

        // Estado inicial del botón al cargar la página
        updateButtonState();

        // Escuchar cambios en el checkbox para habilitar/deshabilitar el botón
        termsCheckbox.addEventListener('input', updateButtonState);

        // Listener principal para el clic en el botón de pago
        checkoutBtn.addEventListener('click', (e) => {
            e.preventDefault(); // Prevenimos cualquier acción por defecto

            // --- VALIDACIÓN FINAL ANTES DE MOSTRAR EL MODAL ---

            // 1. Validar que los términos y condiciones estén aceptados
            if (!termsCheckbox.checked) {
                alert('Por favor, acepta los Términos y Condiciones para continuar.');
                return; // Detiene la ejecución aquí mismo
            }

            // 2. Validar que los demás campos de envío estén llenos
            const name = document.getElementById('shipping-name').value;
            const dni = document.getElementById('shipping-dni').value;
            const region = document.getElementById('shipping-region').value;
            const city = document.getElementById('shipping-city').value;
            const address = document.getElementById('shipping-address').value;
            const phone = document.getElementById('shipping-phone').value;

            if (!name || !dni || !region || !city || !address || !phone) {
                alert('Por favor, completa todos los campos de Detalles de Envío antes de continuar.');
                return; // Detiene la ejecución si falta algún dato
            }

            // 3. Si todas las validaciones pasan, mostramos el modal de pago
            yapeModal.style.display = 'flex';
        });
    }

    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', () => {
            if (yapeModal) {
                yapeModal.style.display = 'none';
            }
        });
    }

    if (yapeForm) {
        yapeForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitButton = yapeForm.querySelector('.btn-confirm-payment');
            submitButton.textContent = 'Verificando...';
            submitButton.disabled = true;
            verificationStatus.textContent = '';

            const formData = {
                customer_info: {
                    name: document.getElementById('shipping-name').value,
                    dni: document.getElementById('shipping-dni').value,
                    region: document.getElementById('shipping-region').value,
                    city: document.getElementById('shipping-city').value,
                    address: document.getElementById('shipping-address').value,
                    phone: document.getElementById('shipping-phone').value,
                    consent_purchase: document.getElementById('whatsapp-consent-purchase').checked,
                    consent_offers: document.getElementById('whatsapp-consent-offers').checked,
                },
                yape_code: document.getElementById('yape-code').value,
            };

            try {
                const response = await fetch('/process_order', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });

                const result = await response.json();

                if (response.ok) {
                    verificationStatus.style.color = 'green';
                    verificationStatus.textContent = result.message;
                    // Redirigir a una página de éxito después de unos segundos
                    setTimeout(() => {
                        window.location.href = result.redirect_url;
                    }, 3000);
                } else {
                    throw new Error(result.message || 'Error desconocido');
                }

            } catch (error) {
                verificationStatus.style.color = 'red';
                verificationStatus.textContent = `Error: ${error.message}. Por favor, verifica el código e intenta de nuevo.`;
                submitButton.textContent = 'Verificar y Finalizar Compra';
                submitButton.disabled = false;
            }
        });
    }
    
    // Función para actualizar ítem (CORREGIDA)
    async function updateCartItem(itemId, quantity) {
        const [productId, size] = itemId.split('-');

        try {
            const response = await fetch('/update_cart_item', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    product_id: productId, 
                    size: size,
                    quantity: quantity
                })
            });

            if (!response.ok) {
                throw new Error('Error en la respuesta del servidor.');
            }

            const data = await response.json();

            if (data.status === 'success') {
                const itemElement = document.querySelector(`.cart-item[data-id="${itemId}"]`);

                if (itemElement) {
                    const itemPriceElement = itemElement.querySelector('.item-price');
                    if (itemPriceElement) {
                        // BUG 1 CORREGIDO: Usamos "S/" en lugar de "$"
                        itemPriceElement.textContent = `S/ ${data.item_total.toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                    }
                }

                // BUG 2 CORREGIDO: Pasamos todos los datos a la función que actualiza los totales
                updateSummaryTotals(data.subtotal, data.total, data.shipping_cost, data.promo_message);
            } else {
                alert(data.message || 'No se pudo actualizar el producto.');
            }

        } catch (error) {
            console.error('Error al actualizar el carrito:', error);
            alert('Hubo un problema de conexión. Inténtalo de nuevo.');
        }
    }

// Coloca esta única versión de la función en tu cart.js
function updateSummaryTotals(subtotal, total, shippingCost, promoMessage) {
    const formatCurrency = (value) => `S/ ${parseFloat(value).toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    // Actualiza el resumen del carrito
    document.querySelector('.summary-row .subtotal').textContent = formatCurrency(subtotal);
    document.querySelector('.summary-row.total .total').textContent = formatCurrency(total);
    document.getElementById('shipping-cost-display').textContent = formatCurrency(shippingCost);

    // Actualiza el total en el modal
    document.getElementById('modal-total-amount').textContent = formatCurrency(total);
    
    // Muestra u oculta el mensaje de promoción de envío
    const promoContainer = document.querySelector('.promo-message');
    if (promoContainer) {
        const promoTextEl = promoContainer.querySelector('.promo-text');
        if (promoMessage) {
            promoTextEl.textContent = promoMessage;
            promoContainer.style.display = 'flex';
        } else {
            promoContainer.style.display = 'none';
        }
    }
}

    // Función para eliminar ítem
    async function removeCartItem(itemId) {
        const [productId, size] = itemId.split('-');
        const response = await fetch('/remove_from_cart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ 
                product_id: productId, 
                size: size
            })
            
        });
        
        const data = await response.json();
        if(data.status === 'success') {
            document.querySelector(`.cart-item[data-id="${itemId}"]`)?.remove();
            
            // Re-calcula los totales desde el objeto 'cart' devuelto
            const newSubtotal = data.cart.cart_items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
            const newTotal = getCartTotal(data.cart); // Usa tu función auxiliar que ya tienes
            
            updateSummaryTotals(newSubtotal, newTotal);
            updateCartCount(data.cart_count); // actualiza el contador global
        }
    }

    // Función auxiliar para calcular total
    function getCartTotal(cart) {
        let total = cart.cart_items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        total += cart.shipping_cost || 0;
        return total;
    }

    // Actualizar contador del carrito
    function updateCartCount(change) {
        const cartCount = document.querySelector('.cart-count');
        if (cartCount) {
            let count = parseInt(cartCount.textContent) || 0;
            count = Math.max(0, count + change);
            cartCount.textContent = count;
            
            cartCount.classList.add('animate');
            setTimeout(() => cartCount.classList.remove('animate'), 500);
        }
    }

    // Conectar eventos
    function setupEventListeners() {
        document.querySelectorAll('.quantity-btn.plus').forEach(btn => {
            btn.addEventListener('click', function() {
                const itemId = this.dataset.id;
                const input = this.parentElement.querySelector('.quantity');
                const newQuantity = parseInt(input.textContent) + 1;
                input.textContent = newQuantity;
                updateCartItem(itemId, newQuantity);
            });
        });
        
        document.querySelectorAll('.quantity-btn.minus').forEach(btn => {
            btn.addEventListener('click', function() {
                const itemId = this.dataset.id;
                const input = this.parentElement.querySelector('.quantity');
                if (parseInt(input.textContent) > 1) {
                    const newQuantity = parseInt(input.textContent) - 1;
                    input.textContent = newQuantity;
                    updateCartItem(itemId, newQuantity);
                }
            });
        });
        
        document.querySelectorAll('.item-remove').forEach(btn => {
            btn.addEventListener('click', function() {
                const itemId = this.dataset.id;
                if (confirm('¿Eliminar este producto del carrito?')) {
                    removeCartItem(itemId);
                }
            });
        });
    }
    
    // SOLUCIÓN: Verificar existencia de elementos antes de agregar listeners
    const applyCouponBtn = document.getElementById('apply-coupon');
    if (applyCouponBtn) {
        applyCouponBtn.addEventListener('click', async () => {
            const couponCode = document.getElementById('coupon-input')?.value?.trim();
            if (!couponCode) return;
            
            const response = await fetch('/apply_coupon', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({ coupon_code: couponCode })
            });
            
            if (response.ok) {
                location.reload();
            } else {
                const error = await response.json();
                alert(error.error || 'Error al aplicar el cupón');
            }
        });
    }
    
    const shippingRegion = document.getElementById('shipping-region');
    if (shippingRegion) {
        shippingRegion.addEventListener('change', async function() {
            const region = this.value;
            if (!region) return;

            try {
                const response = await fetch('/update_shipping', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ region })
                });

                if (!response.ok) {
                    throw new Error('Error al actualizar el envío.');
                }

                const data = await response.json();

                if (data.status === 'success') {
                    // ¡Aquí está la magia!
                    // Llamamos a la función que actualiza los precios en la página
                    // en lugar de recargarla.
                    updateSummaryTotals(data.subtotal, data.total, data.shipping_cost, data.promo_message);
                }

            } catch (error) {
                console.error('Error:', error);
                alert('Hubo un problema al calcular el costo de envío.');
            }
        });
    }
    

    
    const saveCartBtn = document.querySelector('.save-cart');
    if (saveCartBtn) {
        saveCartBtn.addEventListener('click', async () => {
            const response = await fetch('/save_cart', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                }
            });
            
            if (response.ok) {
                alert('Carrito guardado. Puedes acceder a él desde tu perfil.');
            }
        });
    }
    
    // Funciones auxiliares
    function getCSRFToken() {
        return document.querySelector('input[name="csrf_token"]')?.value || '';
    }
    
    // Inicializar solo si estamos en la página del carrito
    if (document.querySelector('.cart-container')) {
        setupEventListeners();
    }
});

 const saveCartBtn = document.getElementById('save-cart-btn');
    if (saveCartBtn) {
        saveCartBtn.addEventListener('click', async () => {
            const response = await fetch('/save_cart', { method: 'POST' });
            const data = await response.json();
            alert(data.message);
            if (response.ok) {
                location.reload(); // Recarga la página para mostrar el carrito vacío
            }
        });
    }

    const restoreCartBtn = document.getElementById('restore-cart-btn');
    if (restoreCartBtn) {
        restoreCartBtn.addEventListener('click', async () => {
            const response = await fetch('/restore_cart', { method: 'POST' });
            const data = await response.json();
            alert(data.message);
            if (response.ok) {
                location.reload(); // Recarga la página para mostrar el carrito restaurado
            }
        });
    }
;