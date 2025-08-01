// static/contact.js

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('contact-form');
    const formStatus = document.getElementById('form-status');
    const submitButton = document.getElementById('submit-button');

    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

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