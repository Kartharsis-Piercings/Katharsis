document.addEventListener('DOMContentLoaded', () => {
    console.log("CARGA FORZADA: Script de reservas activo"); // Chivato de carga

    // --- VARIABLES DE ESTADO ---
    let state = {
        serviceId: null,
        serviceName: null,
        deposit: 0,
        date: null,
        time: null
    };

    // --- ELEMENTOS DEL DOM ---
    const step2 = document.getElementById('step-2');
    const step3 = document.getElementById('step-3');
    const timeSlotsContainer = document.getElementById('time-slots');
    
    // Resumen y Botones
    const summaryService = document.getElementById('summary-service');
    const summaryDate = document.getElementById('summary-date');
    const summaryTime = document.getElementById('summary-time');
    const summaryPrice = document.getElementById('summary-price');
    const btnPay = document.getElementById('btn-pay-booking');

    // Modal (Referencias exactas)
    const modal = document.getElementById('booking-modal');
    const closeModal = document.getElementById('close-booking-modal');
    const verificationForm = document.getElementById('booking-verification-form');

    // --- 1. LÓGICA DE SELECCIÓN DE SERVICIO ---
    // (Usamos addEventListener en lugar de onclick en el HTML para evitar errores)
    const serviceCards = document.querySelectorAll('.service-card');
    
    serviceCards.forEach(card => {
        card.addEventListener('click', () => {
            // 1. Efecto visual de selección
            serviceCards.forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            
            // 2. Guardar datos
            state.serviceId = card.dataset.id;
            state.serviceName = card.dataset.name;
            state.deposit = parseFloat(card.dataset.deposit);

            // 3. Actualizar resumen
            summaryService.textContent = state.serviceName;
            summaryPrice.textContent = `S/ ${state.deposit.toFixed(2)}`;
            
            // 4. Avanzar al paso 2
            step2.classList.remove('disabled');
            step2.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    });

    // --- 2. CALENDARIO ---
    if (document.getElementById("datepicker")) {
        flatpickr("#datepicker", {
            minDate: "today",
            disable: [
                function(date) { return (date.getDay() === 0 || date.getDay() === 1); } // Domingo(0) y Lunes(1) cerrados
            ],
            locale: "es", 
            dateFormat: "Y-m-d",
            onChange: function(selectedDates, dateStr) {
                state.date = dateStr;
                summaryDate.textContent = dateStr;
                loadTimeSlots(dateStr);
            }
        });
    }

    // --- 3. CARGAR HORARIOS ---
    async function loadTimeSlots(dateStr) {
        timeSlotsContainer.innerHTML = '<p class="loading-text">Cargando...</p>';
        state.time = null;
        summaryTime.textContent = '-';
        if(btnPay) btnPay.disabled = true;

        try {
            const response = await fetch(`/api/available_slots?date=${dateStr}`);
            const slots = await response.json();

            timeSlotsContainer.innerHTML = '';
            
            if (!slots || slots.length === 0) {
                timeSlotsContainer.innerHTML = '<p>No hay horarios.</p>';
                return;
            }

            slots.forEach(time => {
                const btn = document.createElement('div');
                btn.className = 'time-slot';
                btn.textContent = time;
                
                // Click en una hora
                btn.onclick = () => {
                    document.querySelectorAll('.time-slot').forEach(b => b.classList.remove('selected'));
                    btn.classList.add('selected');
                    state.time = time;
                    summaryTime.textContent = time;
                    step3.classList.remove('disabled'); // Habilitar datos
                    checkFormValidity();
                };
                
                timeSlotsContainer.appendChild(btn);
            });

        } catch (error) {
            console.error(error);
            timeSlotsContainer.innerHTML = '<p style="color:red">Error.</p>';
        }
    }

// --- 4. VALIDACIÓN DE FORMULARIO ---
    const clientName = document.getElementById('client-name');
    const clientPhone = document.getElementById('client-phone');
    const clientDni = document.getElementById('client-dni');
    const clientDob = document.getElementById('client-dob'); // Nuevo

    function checkFormValidity() {
        // Ahora validamos también que exista fecha de nacimiento
        if (state.serviceId && state.date && state.time && 
            clientName.value.trim() && clientPhone.value.trim() && clientDob.value) {
            if(btnPay) btnPay.disabled = false;
        } else {
            if(btnPay) btnPay.disabled = true;
        }
    }

    if(clientName) {
        // Escuchar cambios en todos los campos
        [clientName, clientPhone, clientDni, clientDob].forEach(input => {
            if(input) input.addEventListener('input', checkFormValidity);
        });
    }

    // ============================================================
    // --- 5. APERTURA DEL MODAL (APLICANDO TU LÓGICA DEL CARRITO) ---
    // ============================================================
    if(btnPay && modal) {
        btnPay.addEventListener('click', (e) => {
            e.preventDefault();
            console.log("Botón de Pagar presionado"); // Chivato 1

            // Actualizar monto visualmente
            const amountLabel = document.getElementById('modal-deposit-amount');
            if(amountLabel) amountLabel.textContent = state.deposit.toFixed(2);
            
            console.log("Intentando abrir modal..."); // Chivato 2
            
            // --- AQUI LA MAGIA DEL CARRITO ---
            modal.style.display = 'flex';
            modal.style.visibility = 'visible';
            modal.style.opacity = '1';
        });
    } else {
        console.error("ERROR CRÍTICO: No se encuentra el botón de pago o el modal en el HTML");
    }

    // Cerrar Modal
    if(closeModal) {
        closeModal.addEventListener('click', () => {
            if(modal) modal.style.display = 'none';
        });
    }
    
    window.addEventListener('click', (e) => {
        if (e.target === modal) modal.style.display = 'none';
    });

    // --- 6. ENVÍO FINAL ---
    if(verificationForm) {
        verificationForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = verificationForm.querySelector('button');
            const originalText = submitBtn.textContent;
            
            submitBtn.textContent = 'Procesando...';
            submitBtn.disabled = true;

            const bookingData = {
                service_id: state.serviceId,
                date: state.date,
                time: state.time,
                client_name: clientName.value,
                client_phone: clientPhone.value,
                client_dni: clientDni ? clientDni.value : '',
                client_dob: clientDob.value, // Enviamos el cumpleaños
                yape_code: document.getElementById('booking-yape-code').value
            };

            try {
                const response = await fetch('/book_appointment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(bookingData)
                });

                const result = await response.json();

                if (response.ok) {
                    alert('¡Cita Agendada! Te hemos enviado un mensaje de confirmación.');
                    window.location.href = result.redirect_url || '/';
                } else {
                    throw new Error(result.message);
                }

            } catch (error) {
                alert(`Error: ${error.message}`);
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
            }
        });
    }

});