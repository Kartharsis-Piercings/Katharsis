
    // --- SCRIPT INCRUSTADO DE CARRITO (VERSIÓN FINAL) ---
    document.addEventListener('DOMContentLoaded', () => {
        console.log("CARGA FORZADA: Script de carrito activo");

        // 1. REFERENCIAS AL DOM
        const checkoutBtn = document.getElementById('checkout-btn');
        const yapeModal = document.getElementById('yape-payment-modal');
        const closeModalBtn = document.getElementById('close-yape-modal');
        const termsCheckbox = document.getElementById('terms-checkbox');
        const yapeForm = document.getElementById('yape-verification-form');
        const verificationStatus = document.getElementById('verification-status');

        // 2. LÓGICA DEL MODAL
        if (checkoutBtn && termsCheckbox && yapeModal) {
            
            // Estado inicial del botón
            checkoutBtn.disabled = !termsCheckbox.checked;

            // Escuchar cambios en el checkbox
            termsCheckbox.addEventListener('change', () => {
                checkoutBtn.disabled = !termsCheckbox.checked;
            });

            // Click en "Continuar al pago"
            checkoutBtn.addEventListener('click', (e) => {
                e.preventDefault();
                console.log("Botón presionado");

                // Validar Checkbox
                if (!termsCheckbox.checked) {
                    alert('Por favor, acepta los Términos y Condiciones.');
                    return;
                }

                // Validar Campos de Envío
                const requiredIds = ['shipping-name', 'shipping-dni', 'shipping-region', 'shipping-city', 'shipping-address', 'shipping-phone'];
                let missing = false;
                
                requiredIds.forEach(id => {
                    const el = document.getElementById(id);
                    if (!el || !el.value.trim()) {
                        missing = true;
                        if(el) el.style.border = "2px solid red";
                    } else {
                        if(el) el.style.border = "1px solid #333";
                    }
                });

                if (missing) {
                    alert('Por favor, completa todos los campos de envío resaltados.');
                    return;
                }

                // ABRIR MODAL
                console.log("Abriendo modal...");
                yapeModal.style.display = 'flex';
                // Forzar visualización por si el CSS falla
                yapeModal.style.visibility = 'visible';
                yapeModal.style.opacity = '1';
            });
        } else {
            console.error("Faltan elementos HTML: Botón, Modal o Checkbox no encontrados.");
        }

        // Cerrar Modal
        if (closeModalBtn) {
            closeModalBtn.addEventListener('click', () => {
                if(yapeModal) yapeModal.style.display = 'none';
            });
        }
        
        window.addEventListener('click', (e) => {
            if (yapeModal && e.target === yapeModal) {
                yapeModal.style.display = 'none';
            }
        });

        // 3. PROCESO DE PAGO (YAPE)
        if (yapeForm) {
            yapeForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const btn = yapeForm.querySelector('button[type="submit"]');
                const originalText = btn.textContent;
                
                btn.textContent = 'Verificando...';
                btn.disabled = true;
                if(verificationStatus) verificationStatus.textContent = '';

                const formData = {
                    customer_info: {
                        name: document.getElementById('shipping-name')?.value,
                        dni: document.getElementById('shipping-dni')?.value,
                        region: document.getElementById('shipping-region')?.value,
                        city: document.getElementById('shipping-city')?.value,
                        address: document.getElementById('shipping-address')?.value,
                        phone: document.getElementById('shipping-phone')?.value,
                        consent_purchase: document.getElementById('whatsapp-consent-purchase')?.checked || false,
                        consent_offers: document.getElementById('whatsapp-consent-offers')?.checked || false,
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
                        if(verificationStatus) {
                            verificationStatus.style.color = 'green';
                            verificationStatus.textContent = result.message;
                        }
                        setTimeout(() => window.location.href = result.redirect_url, 2000);
                    } else {
                        throw new Error(result.message || 'Error desconocido');
                    }
                } catch (error) {
                    if(verificationStatus) {
                        verificationStatus.style.color = 'red';
                        verificationStatus.textContent = error.message;
                    }
                    btn.textContent = originalText;
                    btn.disabled = false;
                }
            });
        }

        // 4. FUNCIONALIDAD DEL CARRITO (Botones +, -, Eliminar)
        
        // Actualizar Totales en Pantalla
        function updateSummary(subtotal, total, shipping, promo) {
            const fmt = n => `S/ ${parseFloat(n).toLocaleString('es-PE', {minimumFractionDigits: 2})}`;
            
            const els = {
                sub: document.querySelector('.summary-row .subtotal'),
                tot: document.querySelector('.summary-row.total .total'),
                shp: document.getElementById('shipping-cost-display'),
                mod: document.getElementById('modal-total-amount')
            };
            
            if(els.sub) els.sub.textContent = fmt(subtotal);
            if(els.tot) els.tot.textContent = fmt(total);
            if(els.shp) els.shp.textContent = fmt(shipping);
            if(els.mod) els.mod.textContent = fmt(total);
            
            const promoBox = document.querySelector('.promo-message');
            if(promoBox) {
                promoBox.style.display = promo ? 'flex' : 'none';
                if(promo) promoBox.querySelector('.promo-text').textContent = promo;
            }
        }

        // Eventos de botones
        document.body.addEventListener('click', async (e) => {
            // Botones de cantidad
            if (e.target.closest('.quantity-btn')) {
                const btn = e.target.closest('.quantity-btn');
                const isPlus = btn.classList.contains('plus');
                const itemId = btn.dataset.id;
                const qtySpan = btn.parentElement.querySelector('.quantity');
                let newQty = parseInt(qtySpan.textContent) + (isPlus ? 1 : -1);
                
                if (newQty > 0) {
                    const [pid, size] = itemId.split('-');
                    const res = await fetch('/update_cart_item', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ product_id: pid, size: size, quantity: newQty })
                    });
                    const data = await res.json();
                    if(data.status === 'success') {
                        qtySpan.textContent = newQty;
                        const row = document.querySelector(`.cart-item[data-id="${itemId}"]`);
                        if(row) row.querySelector('.item-price').textContent = `S/ ${parseFloat(data.item_total).toFixed(2)}`;
                        updateSummary(data.subtotal, data.total, data.shipping_cost, data.promo_message);
                    }
                }
            }

            // Botón Eliminar
            if (e.target.closest('.item-remove')) {
                const btn = e.target.closest('.item-remove');
                if(!confirm('¿Eliminar producto?')) return;
                
                const itemId = btn.dataset.id;
                const [pid, size] = itemId.split('-');
                const res = await fetch('/remove_from_cart', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ product_id: pid, size: size })
                });
                if((await res.json()).status === 'success') location.reload();
            }
        });

        // Cambio de Región
        const regionSelect = document.getElementById('shipping-region');
        if(regionSelect) {
            regionSelect.addEventListener('change', async function() {
                if(!this.value) return;
                const res = await fetch('/update_shipping', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({region: this.value})
                });
                const data = await res.json();
                if(data.status === 'success') {
                    updateSummary(data.subtotal, data.total, data.shipping_cost, data.promo_message);
                }
            });
        }
    });
