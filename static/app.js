// static/app.js
/**
 * Añade navegación por swipe (deslizar) a un contenedor de carrusel.
 * @param {HTMLElement} container El elemento que escuchará el gesto (ej. el carrusel).
 * @param {HTMLElement} nextButton El botón "siguiente" al que se le hará clic.
 * @param {HTMLElement} prevButton El botón "anterior" al que se le hará clic.
 */

function addSwipeNavigation(container, nextButton, prevButton) {
    let touchStartX = 0;
    let touchEndX = 0;
    const swipeThreshold = 50; // Mínimo de píxeles para considerar un swipe

    container.addEventListener('touchstart', (e) => {
        // Solo nos interesa el primer dedo
        touchStartX = e.changedTouches[0].screenX;
    }, { passive: true }); // passive: true para mejor performance de scroll

    container.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    }, { passive: true });

    function handleSwipe() {
        const swipeDistance = touchEndX - touchStartX;

        if (swipeDistance < -swipeThreshold) {
            // Swipe hacia la izquierda (queremos ir al siguiente)
            if (nextButton) nextButton.click();
        } else if (swipeDistance > swipeThreshold) {
            // Swipe hacia la derecha (queremos ir al anterior)
            if (prevButton) prevButton.click();
        }
        
        // Resetea los valores
        touchStartX = 0;
        touchEndX = 0;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    
    // --- LÓGICA DEL CARRUSEL MEJORADA ---
    const carouselContainer = document.querySelector('.carousel-container');
    if (carouselContainer) {
        const carouselSlide = carouselContainer.querySelector('.carousel-slide');
        const prevBtn = carouselContainer.querySelector('.prev-btn');
        const nextBtn = carouselContainer.querySelector('.next-btn');
        
        let currentIndex = 0;
        let slides = [];
        let autoSlideInterval;

        function moveToSlide(index) {
            carouselSlide.style.transition = 'transform 0.5s ease-in-out';
            carouselSlide.style.transform = `translateX(-${index * 100}%)`;
        }

        function handleLoop() {
            if (currentIndex === slides.length - 1) { // Si es el último slide (clon del primero)
                setTimeout(() => {
                    carouselSlide.style.transition = 'none';
                    currentIndex = 1;
                    carouselSlide.style.transform = `translateX(-${currentIndex * 100}%)`;
                }, 500);
            }
            if (currentIndex === 0) { // Si es el primer slide (clon del último)
                setTimeout(() => {
                    carouselSlide.style.transition = 'none';
                    currentIndex = slides.length - 2;
                    carouselSlide.style.transform = `translateX(-${currentIndex * 100}%)`;
                }, 500);
            }
        }
        
        function nextSlide() {
            if (currentIndex >= slides.length - 1) return;
            currentIndex++;
            moveToSlide(currentIndex);
        }

        function prevSlide() {
            if (currentIndex <= 0) return;
            currentIndex--;
            moveToSlide(currentIndex);
        }

        function startAutoSlide() {
            clearInterval(autoSlideInterval);
            autoSlideInterval = setInterval(nextSlide, 5000);
        }

        // Cargar imágenes dinámicamente
        fetch('/api/carousel_images')
            .then(response => response.json())
            .then(imageUrls => {
                if (imageUrls.length === 0) return;

                // Crear los slides
                imageUrls.forEach(imageData => { // Nos aseguramos de que el parámetro se llame 'imageData'
                    const slide = document.createElement('div');
                    slide.className = 'slide';
                    const img = document.createElement('img');
                    
                    // Usamos consistentemente 'imageData.path' y 'imageData.position'
                    img.src = imageData.path; 
                    img.alt = 'Trabajo de piercing';
                    img.style.objectPosition = imageData.position;
                    
                    slide.appendChild(img);
                    carouselSlide.appendChild(slide);
                });

                // Configurar el bucle infinito
                slides = document.querySelectorAll('.slide');
                const firstClone = slides[0].cloneNode(true);
                const lastClone = slides[slides.length - 1].cloneNode(true);
                carouselSlide.appendChild(firstClone);
                carouselSlide.insertBefore(lastClone, slides[0]);
                
                slides = document.querySelectorAll('.slide'); // Actualizar la lista de slides
                currentIndex = 1;
                carouselSlide.style.transform = `translateX(-${currentIndex * 100}%)`;

                // Añadir eventos
                nextBtn.addEventListener('click', () => { nextSlide(); startAutoSlide(); });
                prevBtn.addEventListener('click', () => { prevSlide(); startAutoSlide(); });
                addSwipeNavigation(categoryContainer, nextButton, prevButton);
                carouselSlide.addEventListener('transitionend', handleLoop);
                carouselContainer.addEventListener('mouseenter', () => clearInterval(autoSlideInterval));
                carouselContainer.addEventListener('mouseleave', startAutoSlide);
                startAutoSlide();
            });
    }

    // =============================================
    // ¡NUEVO! LÓGICA DE BUCLE INFINITO PARA GALERÍA DE TRABAJOS
    // =============================================
    const galleryContainer = document.querySelector('.gallery-carousel-container');
    if (galleryContainer) {
        const track = galleryContainer.querySelector('.gallery-track');
        let slides = Array.from(track.children);
        const nextButton = galleryContainer.querySelector('.next-btn-gallery');
        const prevButton = galleryContainer.querySelector('.prev-btn-gallery');
        let currentIndex = 0;

        if (slides.length > 1) {
            // 1. Clonar slides
            const firstClone = slides[0].cloneNode(true);
            const lastClone = slides[slides.length - 1].cloneNode(true);
            track.appendChild(firstClone);
            track.insertBefore(lastClone, slides[0]);

            slides = Array.from(track.children); // Actualizar la lista
            const slideWidth = slides[0].getBoundingClientRect().width;

            // 2. Posicionar al inicio
            currentIndex = 1;
            track.style.transform = `translateX(-${slideWidth * currentIndex}px)`;

            const moveToSlide = (index) => {
                track.style.transition = 'transform 0.5s ease-in-out';
                track.style.transform = `translateX(-${slideWidth * index}px)`;
            };
            
            const handleLoop = () => {
                if (currentIndex === 0) {
                    track.style.transition = 'none';
                    currentIndex = slides.length - 2;
                    track.style.transform = `translateX(-${slideWidth * currentIndex}px)`;
                }
                if (currentIndex === slides.length - 1) {
                    track.style.transition = 'none';
                    currentIndex = 1;
                    track.style.transform = `translateX(-${slideWidth * currentIndex}px)`;
                }
            };

            track.addEventListener('transitionend', handleLoop);
            nextButton.addEventListener('click', () => { if (currentIndex < slides.length - 1) { currentIndex++; moveToSlide(currentIndex); }});
            prevButton.addEventListener('click', () => { if (currentIndex > 0) { currentIndex--; moveToSlide(currentIndex); }});
            addSwipeNavigation(galleryContainer, nextButton, prevButton);
        }
    }

    // =============================================
    // SECCIÓN 2: LÓGICA PARA MODAL DE FEATURES
    // =============================================
    const featureModal = document.getElementById('feature-modal');
    const closeModalBtn = document.getElementById('close-feature-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalContent = document.getElementById('modal-content');
    
    document.querySelectorAll('.read-more-feature').forEach(button => {
        button.addEventListener('click', () => {
            modalTitle.textContent = button.dataset.title;
            modalContent.textContent = button.dataset.content;
            featureModal.classList.add('active');
        });
    });

    const closeFeatureModal = () => {
        featureModal.classList.remove('active');
    };

    if (closeModalBtn) closeModalBtn.addEventListener('click', closeFeatureModal);
    if (featureModal) featureModal.addEventListener('click', (e) => {
        if (e.target === featureModal) closeFeatureModal();
    });

    // =============================================
    // ¡NUEVO! LÓGICA DE BUCLE INFINITO PARA CATEGORÍAS
    // =============================================
    const categoryContainer = document.querySelector('.category-carousel-container');
    if (categoryContainer) {
        const track = categoryContainer.querySelector('.category-track');
        let cards = Array.from(track.children);
        const nextButton = categoryContainer.querySelector('.next-btn-category');
        const prevButton = categoryContainer.querySelector('.prev-btn-category');
        let currentIndex = 0;

        if (cards.length > 3) { // Solo activar si hay suficientes tarjetas
            const cardsToClone = 3;
            for(let i = 0; i < cardsToClone; i++) {
                track.appendChild(cards[i].cloneNode(true));
            }
            for(let i = cards.length - 1; i >= cards.length - cardsToClone; i--) {
                track.insertBefore(cards[i].cloneNode(true), track.firstChild);
            }

            cards = Array.from(track.children);
            currentIndex = cardsToClone;

            const updateCarousel = () => {
                const cardWidth = cards[0].offsetWidth;
                const gap = parseInt(window.getComputedStyle(track).gap);
                const offset = -currentIndex * (cardWidth + gap) + (categoryContainer.offsetWidth / 2 - cardWidth / 2);
                track.style.transform = `translateX(${offset}px)`;

                cards.forEach((card, index) => {
                    card.querySelector('.category-card').classList.toggle('center', index === currentIndex);
                });
            };
            
            const handleCategoryLoop = () => {
                 if (currentIndex >= cards.length - cardsToClone) {
                    track.style.transition = 'none';
                    currentIndex = cardsToClone;
                    updateCarousel();
                }
                if (currentIndex < cardsToClone) {
                    track.style.transition = 'none';
                    currentIndex = cards.length - cardsToClone - 1;
                    updateCarousel();
                }
            };
            
            track.addEventListener('transitionend', () => {
                setTimeout(handleCategoryLoop, 100); // Pequeño delay para asegurar la transición
            });

            nextButton.addEventListener('click', () => {
                track.style.transition = 'transform 0.5s ease-in-out';
                currentIndex++;
                updateCarousel();
            });
            prevButton.addEventListener('click', () => {
                track.style.transition = 'transform 0.5s ease-in-out';
                currentIndex--;
                updateCarousel();
            });
            addSwipeNavigation(categoryContainer, nextButton, prevButton);
            
            // Lógica de hover (sin cambios)
            // ...
            
            window.addEventListener('load', () => setTimeout(updateCarousel, 100)); // Delay para asegurar carga de CSS
            window.addEventListener('resize', updateCarousel);
        }
    }


// ======================================================
// LÓGICA MEJORADA PARA CARRUSEL INFINITO DE TARJETAS GUÍA
// ======================================================
const guideSlider = document.querySelector('.guide-cards-container');

if (guideSlider) {
    const track = guideSlider.querySelector('.guide-cards-track');
    let cards = Array.from(track.children);
    const nextButton = guideSlider.querySelector('.next-btn-guide');
    const prevButton = guideSlider.querySelector('.prev-btn-guide');

    let currentIndex = 0;
    let autoSlideInterval;
    const cardsVisible = 4; // Número de tarjetas visibles en escritorio

    // --- 1. Clonamos las tarjetas para el efecto de bucle ---
    // Clonamos las primeras 'cardsVisible' y las añadimos al final
    for (let i = 0; i < cardsVisible; i++) {
        track.appendChild(cards[i].cloneNode(true));
    }
    // Clonamos las últimas 'cardsVisible' y las añadimos al principio
    for (let i = cards.length - 1; i >= cards.length - cardsVisible; i--) {
        track.insertBefore(cards[i].cloneNode(true), track.firstChild);
    }

    // Actualizamos nuestra lista de tarjetas para incluir los clones
    cards = Array.from(track.children);
    
    const cardWidth = cards[0].offsetWidth;
    const gap = parseInt(window.getComputedStyle(track).gap);
    const slideWidth = cardWidth + gap;

    // --- 2. Posicionamos el carrusel en el primer set de tarjetas "reales" ---
    currentIndex = cardsVisible;
    track.style.transform = `translateX(-${currentIndex * slideWidth}px)`;


    const moveToSlide = (index) => {
        track.style.transition = 'transform 0.5s ease-in-out';
        track.style.transform = `translateX(-${index * slideWidth}px)`;
    };

    const handleTransitionEnd = () => {
        // Si llegamos a los clones del final, saltamos sin animación al inicio
        if (currentIndex >= cards.length - cardsVisible) {
            track.style.transition = 'none';
            currentIndex = cardsVisible;
            track.style.transform = `translateX(-${currentIndex * slideWidth}px)`;
        }
        // Si llegamos a los clones del principio, saltamos sin animación al final
        if (currentIndex < cardsVisible) {
            track.style.transition = 'none';
            currentIndex = cards.length - cardsVisible - 1; // Ajustado para un salto correcto
            track.style.transform = `translateX(-${currentIndex * slideWidth}px)`;
        }
    };

    track.addEventListener('transitionend', handleTransitionEnd);

    const slideNext = () => {
        currentIndex++;
        moveToSlide(currentIndex);
    };

    const slidePrev = () => {
        currentIndex--;
        moveToSlide(currentIndex);
    };

    nextButton.addEventListener('click', slideNext);
    prevButton.addEventListener('click', slidePrev);
    addSwipeNavigation(categoryContainer, nextButton, prevButton);

    const startAutoSlide = () => {
        clearInterval(autoSlideInterval);
        autoSlideInterval = setInterval(slideNext, 5000);
    };

    guideSlider.addEventListener('mouseenter', () => clearInterval(autoSlideInterval));
    guideSlider.addEventListener('mouseleave', startAutoSlide);

    // Iniciar el deslizamiento automático
    startAutoSlide();
}

    // --- LÓGICA DEL MENÚ MÓVIL ---
    const menuToggle = document.getElementById('mobile-menu');
    const navLinks = document.getElementById('nav-links');

    if (menuToggle && navLinks) {
        menuToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
            menuToggle.classList.toggle('active');
        });

        document.querySelectorAll('.nav-links a').forEach(link => {
            link.addEventListener('click', () => {
                if (navLinks.classList.contains('active')) {
                    navLinks.classList.remove('active');
                    menuToggle.classList.remove('active');
                }
            });
        });
    }
    
});