// Gestión de preferencias de notificaciones push del supervisor (P4 - Andrés)
(() => {
    const form = document.getElementById('form-preferencias-notificacion');
    const msgExito = document.getElementById('msg-preferencias');

    if (!form) return;

    let temporizadorMensaje = null;

    function mostrarMensajeExito() {
        if (!msgExito) return;
        msgExito.hidden = false;
        if (temporizadorMensaje) clearTimeout(temporizadorMensaje);
        temporizadorMensaje = setTimeout(() => {
            msgExito.hidden = true;
        }, 3000);
    }

    async function cargarPreferencias() {
        try {
            const resp = await fetch('/api/mis-preferencias-notificacion');
            if (!resp.ok) {
                console.warn('[Preferencias] Error al cargar preferencias:', resp.status);
                return;
            }
            const data = await resp.json();

            // Actualizar cada checkbox según la respuesta
            const inputs = form.querySelectorAll('.switch-input');
            inputs.forEach((input) => {
                const tipo = input.getAttribute('data-tipo');
                if (tipo && typeof data[tipo] === 'boolean') {
                    input.checked = data[tipo];
                }
            });
        } catch (err) {
            console.error('[Preferencias] Fallo al consultar preferencias del servidor:', err);
        }
    }

    async function guardarPreferencia(tipo, activa, inputElement) {
        try {
            const cuerpo = {};
            cuerpo[tipo] = activa;

            const resp = await fetch('/api/mis-preferencias-notificacion', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(cuerpo)
            });

            if (resp.ok) {
                mostrarMensajeExito();
                console.log(`[Preferencias] Preferencia ${tipo} actualizada a ${activa}`);
            } else {
                console.warn('[Preferencias] Error al guardar preferencia:', resp.status);
                // Revertir estado si el servidor falló
                inputElement.checked = !activa;
            }
        } catch (err) {
            console.error('[Preferencias] Fallo de red al guardar preferencia:', err);
            inputElement.checked = !activa;
        }
    }

    // Escuchar cambios en los interruptores
    form.addEventListener('change', (e) => {
        const input = e.target;
        if (input && input.classList.contains('switch-input')) {
            const tipo = input.getAttribute('data-tipo');
            if (tipo) {
                guardarPreferencia(tipo, input.checked, input);
            }
        }
    });

    cargarPreferencias();
})();
