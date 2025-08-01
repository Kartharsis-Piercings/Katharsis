// static/contact.js

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('contact-form');
    const formStatus = document.getElementById('form-status');
    const submitButton = document.getElementById('submit-button');

    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const emailInput = document.getElementById('email');
        const phoneInput = document.getElementById('phone');
        
        // --- NUEVO BLOQUE DE VALIDACIÓN ---
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        const phoneRegex = /^\d{9}$/;

        if (!emailRegex.test(emailInput.value)) {
            formStatus.className = 'form-status error';
            formStatus.textContent = 'Por favor, ingresa un correo electrónico válido (ej: correo@dominio.com).';
            formStatus.style.display = 'block';
            return; // Detiene el envío
        }

        if (!phoneRegex.test(phoneInput.value)) {
            formStatus.className = 'form-status error';
            formStatus.textContent = 'El número de teléfono debe contener exactamente 9 dígitos.';
            formStatus.style.display = 'block';
            return; // Detiene el envío
        }

        // Mostrar estado de carga
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enviando...';
        formStatus.style.display = 'none';

        // Recolectar datos del formulario
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        try {
            const response = await fetch('/submit_contact', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            const result = await response.json();

            // Mostrar resultado
            formStatus.className = 'form-status'; // Reset class
            formStatus.textContent = result.message;

            if (response.ok) {
                formStatus.classList.add('success');
                form.reset(); // Limpiar el formulario
            } else {
                formStatus.classList.add('error');
            }
            formStatus.style.display = 'block';

        } catch (error) {
            console.error('Error al enviar el formulario:', error);
            formStatus.className = 'form-status error';
            formStatus.textContent = 'Hubo un error al conectar con el servidor. Por favor, inténtalo más tarde.';
            formStatus.style.display = 'block';
        } finally {
            // Restaurar botón
            submitButton.disabled = false;
            submitButton.innerHTML = '<i class="fas fa-paper-plane"></i> Enviar Mensaje';
        }
    });
});