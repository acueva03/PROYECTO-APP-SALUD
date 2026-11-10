// ficha.js: formulario "Editar mis datos" de la pantalla del PACIENTE.
// Es independiente (la pantalla del paciente no carga graficos.js). Al guardar avisa a salud.js con el evento 'ficha-guardada'.
(() => {
    const form = document.getElementById('form-ficha');
    if (!form) return;
    const TIMEOUT_MS = 4000;

    async function pedirJSON(url, opciones = {}) {
        const controller = new AbortController();
        const t = setTimeout(() => controller.abort(), TIMEOUT_MS);
        try {
            const r = await fetch(url, { ...opciones, signal: controller.signal });
            const datos = await r.json();
            if (!r.ok) throw new Error(datos.error || 'HTTP ' + r.status);
            return datos;
        } finally {
            clearTimeout(t);
        }
    }
    const msg = document.getElementById('mensaje-ficha');
    const boton = form.querySelector('button[type="submit"]');
    const CAMPOS = ['edad', 'altura', 'telefono', 'grupo_sanguineo', 'alergias', 'enfermedades_cronicas',
                    'medicacion', 'contacto_emergencia_nombre', 'contacto_emergencia_telefono'];
    const entrada = (campo) => document.getElementById('ficha-' + campo);

    function mostrar(texto, ok) {
        msg.textContent = texto;
        msg.className = 'mensaje ' + (ok ? 'ok' : 'error');
    }

    async function cargarFicha() {
        try {
            const f = await pedirJSON('/api/mi-ficha');
            for (const c of CAMPOS) entrada(c).value = (f[c] === null || f[c] === undefined) ? '' : f[c];
        } catch (e) {
            console.error('[ficha] no se pudieron cargar los datos', e);                           // 3.18
            mostrar('No se pudieron cargar tus datos. Recarga la página.', false);
        }
    }

    form.addEventListener('submit', async (ev) => {
        ev.preventDefault();
        const cuerpo = {};
        for (const c of CAMPOS) cuerpo[c] = entrada(c).value;
        boton.disabled = true;
        mostrar('Guardando…', true);
        try {
            await pedirJSON('/api/mi-ficha', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(cuerpo)
            });
            mostrar('Datos guardados', true);
            document.dispatchEvent(new CustomEvent('ficha-guardada'));   // salud.js refresca "Mis datos"
            cargarFicha();
        } catch (e) {
            console.error('[ficha] no se pudieron guardar los datos', e);                          // 3.18
            mostrar(e.name === 'AbortError' ? 'El servidor tarda demasiado. Inténtalo de nuevo.' : e.message, false);
        } finally {
            boton.disabled = false;
        }
    });

    cargarFicha();
})();