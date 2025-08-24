// static/app.js
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
                imageUrls.forEach(url => {
                    const slide = document.createElement('div');
                    slide.className = 'slide';
                    const img = document.createElement('img');
                    img.src = url;
                    img.alt = 'Trabajo de piercing';
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
                carouselSlide.addEventListener('transitionend', handleLoop);
                carouselContainer.addEventListener('mouseenter', () => clearInterval(autoSlideInterval));
                carouselContainer.addEventListener('mouseleave', startAutoSlide);
                startAutoSlide();
            });
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