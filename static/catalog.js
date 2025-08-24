document.addEventListener('DOMContentLoaded', function() {
    // --- REFERENCIAS A ELEMENTOS PRINCIPALES ---
    const productsGrid = document.querySelector('.products-grid');
    const quickViewModal = document.querySelector('.quick-view-modal');
    const modalProduct = document.querySelector('.modal-product');
    const closeModalBtn = document.querySelector('.close-modal');
    const gridViewBtn = document.querySelector('.grid-view');
    const listViewBtn = document.querySelector('.list-view');
    const sortSelect = document.getElementById('sort-select');
    const priceFilterForm = document.getElementById('price-filter-form');
    const priceSlider = document.getElementById('price-slider');
    const maxPriceDisplay = document.getElementById('max-price-display');

    // =========================================================================
    // FUNCIÓN CENTRALIZADA PARA ASIGNAR TODOS LOS EVENTOS A LAS TARJETAS
    // =========================================================================
    function setupProductCardListeners() {

        // 1. Lógica para VISTA RÁPIDA
        document.querySelectorAll('.quick-view').forEach(btn => {
            btn.addEventListener('click', async function() {
                const productId = this.getAttribute('data-product-id');
        
        try {
            const response = await fetch(`/api/product/${productId}`);
            const product = await response.json();
            
            // --- Lógica de Badges para el Modal ---
            const saleBadgeHTML = product.on_sale 
                        ? `<span class="badge-sale">-${Math.round(((product.price - product.sale_price) / product.price) * 100)}%</span>` 
                        : '';
                    const newBadgeHTML = product.is_new ? `<span class="badge-new">Nuevo</span>` : '';

            
            // --- Lógica de Precio para el Modal ---
            const priceHTML = product.on_sale
                ? `<span class="current-price">S/ ${product.sale_price.toFixed(2)}</span><span class="old-price">S/ ${product.price.toFixed(2)}</span>`
                : `<span class="current-price">S/ ${product.price.toFixed(2)}</span>`;

            // Construir el contenido del modal
            modalProduct.innerHTML = `
                <div class="modal-product-gallery">
                    <div class="main-image">
                        <img src="${product.images[0]}" alt="${product.name}">
                    </div>
                    <div class="thumbnails">
                        ${product.images.map((image, index) => `
                            <img src="${image}" 
                                 alt="Miniatura ${index+1}" 
                                 class="${index === 0 ? 'active' : ''}" 
                                 data-index="${index}">
                        `).join('')}
                    </div>
                </div>
                <div class="modal-product-info">
                    <h2>${product.name}</h2>

                    <div class="product-badges" style="margin-bottom: 1rem;">
                                ${newBadgeHTML}
                                ${saleBadgeHTML}
                        </div>

                    <p class="product-category">${product.category.charAt(0).toUpperCase() + product.category.slice(1)}</p>
                    <div class="modal-product-price">
                        ${product.on_sale ? `
                            <span class="current-price">S/ ${product.sale_price.toLocaleString('es-PE')}</span>
                            <span class="old-price">S/ ${product.price.toLocaleString('es-PE')}</span>
                        ` : `
                            <span class="current-price">S/ ${product.price.toLocaleString('es-PE')}</span>
                        `}
                    </div>
                    <p class="modal-product-description">
                        ${product.description}
                    </p>
                    <div class="modal-product-actions">
                            <form method="POST" action="/add_to_cart">
                                <input type="hidden" name="product_id" value="${product.id}">
                                <select name="size" class="size-select" required>
                                    <option value="" disabled selected>Selecciona tamaño</option>
                                    ${product.sizes.map(size => `
                                        <option value="${size}">${size}</option>
                                    `).join('')}
                                </select>
                                <input type="number" name="quantity" min="1" max="10" value="1" class="quantity-input">
                                <button type="submit" class="btn-add-cart">Añadir al carrito</button>
                            </form>
                        <script>
                        function validateSize(form) {
                            const sizeSelect = form.querySelector('select[name="size"]');
                            if (!sizeSelect.value) {
                                alert("Por favor selecciona un tamaño");
                                return false;
                            }
                            return true;
                        }
                        </script>
                        <a href="/producto/${product.id}" class="btn-view-details">Ver detalles completos</a>
                    </div>
                    <div class="modal-product-details">
                        <h3>Detalles del Producto</h3>
                        <table class="details-table">
                            <tr>
                                <td>Material</td>
                                <td>${product.material.charAt(0).toUpperCase() + product.material.slice(1)}</td>
                            </tr>
                            <tr>
                                <td>Rosca</td>
                                <td>${product.rosca.charAt(0).toUpperCase() + product.rosca.slice(1)}</td>
                            </tr>
                            <tr>
                                <td>Garantía</td>
                                <td>1 año contra defectos de fabricación</td>
                            </tr>
                        </table>
                    </div>
                </div>
            `;

            
                // Agregar event listener al nuevo formulario del modal
                    const quickViewForm = modalProduct.querySelector('form[action="/add_to_cart"]');
                    if (quickViewForm) {
                        quickViewForm.addEventListener('submit', async function(e) {
                            e.preventDefault(); // ¡CLAVE! Previene la redirección

                            const sizeSelect = this.querySelector('select[name="size"]');
                            if (!sizeSelect.value) {
                                alert("Por favor selecciona un tamaño");
                                return; // Detiene la ejecución si no hay tamaño
                            }

                            const btn = this.querySelector('.btn-add-cart');
                            const originalText = btn.textContent;
                            
                            // Mostrar animación en el botón
                            btn.textContent = '✓ Añadido';
                            btn.style.backgroundColor = '#4CAF50';
                            btn.disabled = true;

                            try {
                                const formData = new FormData(this);
                                const response = await fetch('/add_to_cart', {
                                    method: 'POST',
                                    body: formData
                                });

                                if (response.ok) {
                                    // Actualizar contador del header
                                    const data = await response.json();
                                    const cartCount = document.querySelector('.cart-count');
                                    if (cartCount) {
                                        const count = parseInt(cartCount.textContent) || 0;
                                        const quantity = parseInt(formData.get('quantity')) || 1;
                                        cartCount.textContent = data.cart_count; // Aumentar por la cantidad añadida
                                        cartCount.classList.add('animate');
                                        setTimeout(() => cartCount.classList.remove('animate'), 500);
                                    }
                                } else {
                                    alert('Error al agregar al carrito');
                                }

                                // Restaurar botón y cerrar modal
                                setTimeout(() => {
                                    btn.textContent = originalText;
                                    btn.style.backgroundColor = ''; // O el color original
                                    btn.disabled = false;
                                    
                                    // Cierra el modal después de añadir
                                    const quickViewModal = document.querySelector('.quick-view-modal');
                                    if(quickViewModal) quickViewModal.classList.remove('active');
                                    document.body.style.overflow = 'auto';

                                }, 1500);

                            } catch (error) {
                                console.error('Error:', error);
                                alert('Error de conexión');
                                // Restaurar botón en caso de error
                                btn.textContent = originalText;
                                btn.style.backgroundColor = '';
                                btn.disabled = false;
                            }
                        });
                    }


                // Event listeners para las miniaturas
                const thumbnails = modalProduct.querySelectorAll('.thumbnails img');
                thumbnails.forEach(thumb => {
                    thumb.addEventListener('click', function() {
                        const index = this.getAttribute('data-index');
                        const mainImg = modalProduct.querySelector('.main-image img');
                        mainImg.src = this.src;
                        
                        // Actualizar clase activa
                        thumbnails.forEach(img => img.classList.remove('active'));
                        this.classList.add('active');

                        // Agregar event listener al formulario del modal
                        const quickViewForm = modalProduct.querySelector('form');
                        quickViewForm.addEventListener('submit', async function(e) {
                            e.preventDefault(); // Prevenir envío tradicional
                            
                            // Mismo manejo que formularios principales
                            const btn = this.querySelector('.btn-add-cart');
                            // ... usar misma lógica de botones que arriba ...
                            
                            // Enviar con fetch
                            const formData = new FormData(this);
                            const response = await fetch('/add_to_cart', {
                                method: 'POST',
                                body: formData
                            });
                            
                            // Cerrar modal después de agregar
                            if (response.ok) {
                                setTimeout(() => {
                                    quickViewModal.classList.remove('active');
                                }, 1500);
                            }
                        });

                    });
                });
                
                quickViewModal.classList.add('active');
                document.body.style.overflow = 'hidden';
                
            } catch (error) {
                console.error('Error al cargar el producto:', error);
                modalProduct.innerHTML = '<p>Error al cargar el producto. Por favor, inténtalo de nuevo.</p>';
                quickViewModal.classList.add('active');
                document.body.style.overflow = 'hidden';
            }
        });
    }
    );
    
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

     // Logica para el filtro en vista móvil
    const filterToggleBtn = document.getElementById('filter-toggle-btn');
    const catalogFilters = document.querySelector('.catalog-filters');

    if (filterToggleBtn && catalogFilters) {
        filterToggleBtn.addEventListener('click', () => {
            catalogFilters.classList.toggle('filters-active');
            
            // Cambia el texto del botón
            const isVisible = catalogFilters.classList.contains('filters-active');
            filterToggleBtn.innerHTML = isVisible 
                ? '<i class="fas fa-times"></i> Ocultar Filtros' 
                : '<i class="fas fa-filter"></i> Mostrar Filtros';
        });
    }

     // 2. Lógica para WISHLIST
        document.querySelectorAll('.btn-wishlist').forEach(btn => {
            btn.addEventListener('click', async function() {
                const productId = this.dataset.productId;
                const icon = this.querySelector('i');
                try {
                    const response = await fetch('/toggle_wishlist', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ product_id: parseInt(productId) })
                    });
                    const data = await response.json();
                    if (data.status === 'success') {
                        if (data.action === 'added') {
                            icon.classList.replace('far', 'fas');
                            icon.style.color = '#ff5252';
                        } else {
                            icon.classList.replace('fas', 'far');
                            icon.style.color = '';
                        }
                    }
                } catch (error) {
                    console.error('Error al actualizar la wishlist:', error);
                }
            });
        });

      // 3. Lógica para AÑADIR AL CARRITO
        document.querySelectorAll('form[action="/add_to_cart"]').forEach(form => {
            if (form.dataset.listenerAttached) return; // Previene duplicados

            form.addEventListener('submit', async function(e) {
                e.preventDefault();
                form.dataset.listenerAttached = 'true';

                const sizeSelect = this.querySelector('select[name="size"]');
                if (!sizeSelect.value) {
                    alert('Por favor selecciona un tamaño');
                    delete form.dataset.listenerAttached;
                    return;
                }

                const btn = this.querySelector('.btn-add-cart');
                const originalText = btn.textContent;
                btn.textContent = '✓ Añadido';
                btn.style.backgroundColor = '#4CAF50';
                btn.disabled = true;

                try {
                    const formData = new FormData(this);
                    const response = await fetch('/add_to_cart', { method: 'POST', body: formData });
                    if (response.ok) {
                        const data = await response.json();
                        const cartCount = document.querySelector('.cart-count');
                        if (cartCount) {
                            cartCount.textContent = data.cart_count;
                            cartCount.classList.add('animate');
                            setTimeout(() => cartCount.classList.remove('animate'), 500);
                        }
                    } else {
                        alert('Error al agregar al carrito');
                    }
                } catch (error) {
                    console.error('Error:', error);
                } finally {
                    setTimeout(() => {
                        btn.textContent = originalText;
                        btn.style.backgroundColor = '';
                        btn.disabled = false;
                        delete form.dataset.listenerAttached;
                    }, 2000);
                }
            });
        });
    }

    /**
     * Renderiza los productos en el DOM y luego reactiva los listeners.
     */
    function renderProducts(products) {
        if (!productsGrid) return;
        productsGrid.innerHTML = ''; // Limpia el grid

        if (products.length === 0) {
            productsGrid.innerHTML = `
                <div class="no-products">
                    <p>No se encontraron productos con los filtros seleccionados.</p>
                    <a href="/joyas" class="btn-clear">Ver todos los productos</a>
                </div>`;
            return;
        }

    // --- MANEJO DEL ORDENAMIENTO SIN RECARGAR LA PÁGINA ---
    const sortSelect = document.getElementById('sort-select');
    if (sortSelect) {
        sortSelect.addEventListener('change', function() {
            // Cuando el usuario cambia la opción, llamamos a la función para actualizar productos
            fetchAndUpdateProducts();
        });
    }

    // Dejamos los listeners de los filtros de precio para que también actualicen dinámicamente
    const priceFilterForm = document.getElementById('price-filter-form');
    if (priceFilterForm) {
        priceFilterForm.addEventListener('submit', function(e) {
            e.preventDefault(); // Prevenimos el envío tradicional del formulario
            fetchAndUpdateProducts();
        });
    }
    // ¡LA CLAVE! Se reactivan todos los listeners para los nuevos productos.
        setupProductCardListeners();
    }
    /**
     * Función principal para obtener y mostrar los productos dinámicamente.
     */
    async function fetchAndUpdateProducts() {
        const productsGrid = document.querySelector('.products-grid');
        if (!productsGrid) return;

        // Mostramos un indicador de carga
        productsGrid.innerHTML = '<p style="text-align: center; font-size: 1.2rem;">Cargando productos...</p>';

        // 1. Recolectar todos los filtros activos de la página
        const filters = getActiveFilters();
        
        // 2. Construir la URL para nuestra API con todos los filtros
        const url = new URL('/api/filter_products', window.location.origin);
        Object.keys(filters).forEach(key => url.searchParams.append(key, filters[key]));
        
        try {
            // 3. Realizar la petición fetch
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Error del servidor: ${response.statusText}`);
            }
            const products = await response.json();
            
            // 4. Renderizar los productos en la página
            renderProducts(products);

        } catch (error) {
            console.error('Error al cargar los productos:', error);
            productsGrid.innerHTML = '<p style="text-align: center; color: red;">No se pudieron cargar los productos. Inténtalo de nuevo.</p>';
        }
    }

    /**
     * Recolecta los valores de todos los filtros en la página.
     * @returns {object} Un objeto con todos los filtros activos.
     */
    function getActiveFilters() {
        // Obtenemos los filtros de la URL actual para mantener el estado
        const params = new URLSearchParams(window.location.search);
        
        const priceSlider = document.getElementById('price-slider');
        const sortSelect = document.getElementById('sort-select');

        return {
            category: params.get('category') || 'all',
            body_part: params.get('body_part') || 'all',
            material: params.get('material') || 'all',
            max_price: priceSlider ? priceSlider.value : '300',
            sort_by: sortSelect ? sortSelect.value : 'popular'
        };
    }

    /**
     * Limpia el grid y renderiza la lista de productos.
     * @param {Array} products - El array de objetos de producto.
     */
    function renderProducts(products) {
        const productsGrid = document.querySelector('.products-grid');
        productsGrid.innerHTML = ''; // Limpiar el contenido actual

        if (products.length === 0) {
            productsGrid.innerHTML = `
                <div class="no-products">
                    <p>No se encontraron productos con los filtros seleccionados.</p>
                    <a href="/joyas" class="btn-clear">Ver todos los productos</a>
                </div>`;
            return;
        }

        products.forEach(product => {
            const productCard = document.createElement('div');
            productCard.className = 'product-card';
            
            // Lógica para formatear precios
            const formatPrice = (price) => `S/ ${parseFloat(price).toFixed(2)}`;
            const priceHTML = product.on_sale 
                ? `<span class="current-price">${formatPrice(product.sale_price)}</span>
                   <span class="old-price">${formatPrice(product.price)}</span>`
                : `<span class="current-price">${formatPrice(product.price)}</span>`;

            // Lógica para las opciones de tamaño
            const sizesOptions = product.sizes.map(size => `<option value="${size}">${size}</option>`).join('');

             const saleBadgeHTML = product.on_sale 
                ? `<span class="badge-sale">-${Math.round(((product.price - product.sale_price) / product.price) * 100)}%</span>` 
                : '';

            productCard.innerHTML = `
                <div class="product-image">
                    <a href="/producto/${product.id}">
                        <img src="${product.images[0]}" alt="${product.name}">
                    </a>
                    <div class="product-badges">
                        ${product.is_new ? '<span class="badge-new">Nuevo</span>' : ''}
                        ${saleBadgeHTML} 
                    </div>
                    <button class="quick-view" data-product-id="${product.id}">Vista rápida</button>
                </div>
                <div class="product-info">
                    <h3><a href="/producto/${product.id}">${product.name}</a></h3>
                    <p class="product-category">${product.category}</p>
                    <div class="product-price">
                        ${priceHTML}
                    </div>
                    <div class="product-actions">
                        <form method="POST" action="/add_to_cart" class="add-to-cart-form">
                            <input type="hidden" name="product_id" value="${product.id}">
                            <select name="size" class="size-select" required>
                                <option value="" disabled selected>Selecciona tamaño</option>
                                ${sizesOptions}
                            </select>
                            <input type="hidden" name="quantity" value="1">
                            <button type="submit" class="btn-add-cart">Añadir al carrito</button>
                        </form>
                        <button class="btn-wishlist" data-product-id="${product.id}">
                             <i class="far fa-heart"></i>
                        </button>
                    </div>
                </div>`;
            
            productsGrid.appendChild(productCard);
        });
         setupProductCardListeners();
    }
    
    
    /**
     * Recolecta los valores de todos los filtros en la página.
     */
    function getActiveFilters() {
        const params = new URLSearchParams(window.location.search);
        return {
            category: params.get('category') || 'all',
            body_part: params.get('body_part') || 'all',
            material: params.get('material') || 'all',
            max_price: priceSlider ? priceSlider.value : '300',
            sort_by: sortSelect ? sortSelect.value : 'popular'
        };
    }

    /**
     * Función principal para obtener y mostrar los productos dinámicamente.
     */
    async function fetchAndUpdateProducts() {
        if (!productsGrid) return;
        productsGrid.innerHTML = '<p style="text-align: center; font-size: 1.2rem;">Cargando productos...</p>';

        const filters = getActiveFilters();
        const url = new URL('/api/filter_products', window.location.origin);
        Object.keys(filters).forEach(key => url.searchParams.append(key, filters[key]));

        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`Error del servidor: ${response.statusText}`);
            const products = await response.json();
            renderProducts(products);
        } catch (error) {
            console.error('Error al cargar los productos:', error);
            productsGrid.innerHTML = '<p style="text-align: center; color: red;">No se pudieron cargar los productos. Inténtalo de nuevo.</p>';
        }
    }

    // =========================================================================
    // ASIGNACIÓN DE EVENTOS INICIALES (SOLO PARA ELEMENTOS QUE NO CAMBIAN)
    // =========================================================================

    if (gridViewBtn && listViewBtn) {
        gridViewBtn.addEventListener('click', () => {
            productsGrid.classList.remove('list-view-active');
            gridViewBtn.classList.add('active');
            listViewBtn.classList.remove('active');
        });
        listViewBtn.addEventListener('click', () => {
            productsGrid.classList.add('list-view-active');
            listViewBtn.classList.add('active');
            gridViewBtn.classList.remove('active');
        });
    }

    if (sortSelect) {
        sortSelect.addEventListener('change', fetchAndUpdateProducts);
    }

    if (priceFilterForm) {
        priceFilterForm.addEventListener('submit', (e) => {
            e.preventDefault();
            fetchAndUpdateProducts();
        });
    }

    if (priceSlider && maxPriceDisplay) {
        priceSlider.addEventListener('input', () => maxPriceDisplay.textContent = priceSlider.value);
    }

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

    // Llamada inicial para los productos que cargan con la página
    setupProductCardListeners();
});