// static/app.js
document.addEventListener('DOMContentLoaded', () => {
    
    // --- LÓGICA DEL CARRUSEL ---
    const carouselSlide = document.querySelector('.carousel-slide');
    if (carouselSlide) {
        const slides = document.querySelectorAll('.slide');
        const prevBtn = document.querySelector('.prev-btn');
        const nextBtn = document.querySelector('.next-btn');
        
        let currentIndex = 1;
        const totalSlides = slides.length;
        let slideWidth = slides.length > 0 ? slides[0].clientWidth : 0;
        let autoSlideInterval;
        let isTransitioning = false;

        if (slides.length > 1) {
            const firstClone = slides[0].cloneNode(true);
            const lastClone = slides[totalSlides - 1].cloneNode(true);
            carouselSlide.insertBefore(lastClone, carouselSlide.firstChild);
            carouselSlide.appendChild(firstClone);
            carouselSlide.style.transform = `translateX(-${slideWidth}px)`;
        }

        function moveToSlide(index) {
            if (isTransitioning || slides.length <= 1) return;
            isTransitioning = true;
            carouselSlide.style.transition = 'transform 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
            carouselSlide.style.transform = `translateX(-${index * slideWidth}px)`;
            currentIndex = index;
        }

        function handleTransitionEnd() {
            isTransitioning = false;
            if (currentIndex === 0) {
                carouselSlide.style.transition = 'none';
                carouselSlide.style.transform = `translateX(-${totalSlides * slideWidth}px)`;
                currentIndex = totalSlides;
            } else if (currentIndex === totalSlides + 1) {
                carouselSlide.style.transition = 'none';
                carouselSlide.style.transform = `translateX(-${slideWidth}px)`;
                currentIndex = 1;
            }
        }

        function nextSlide() { moveToSlide(currentIndex + 1); }
        function prevSlide() { moveToSlide(currentIndex - 1); }

        function startAutoSlide() {
            clearInterval(autoSlideInterval);
            autoSlideInterval = setInterval(() => { if (!isTransitioning) nextSlide(); }, 5000);
        }

        nextBtn.addEventListener('click', () => { if (!isTransitioning) { clearInterval(autoSlideInterval); nextSlide(); startAutoSlide(); } });
        prevBtn.addEventListener('click', () => { if (!isTransitioning) { clearInterval(autoSlideInterval); prevSlide(); startAutoSlide(); } });
        carouselSlide.addEventListener('transitionend', handleTransitionEnd);
        
        const container = carouselSlide.parentElement;
        container.addEventListener('mouseenter', () => clearInterval(autoSlideInterval));
        container.addEventListener('mouseleave', startAutoSlide);

        window.addEventListener('resize', () => {
            slideWidth = slides[0].clientWidth;
            carouselSlide.style.transition = 'none';
            carouselSlide.style.transform = `translateX(-${currentIndex * slideWidth}px)`;
        });

        if (slides.length > 1) {
            startAutoSlide();
        }
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