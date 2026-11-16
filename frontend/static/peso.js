// peso.js: formulario "Registrar mi peso" de la pantalla "Ficha médica" del PACIENTE.
// (Antes estaba dentro de salud.js, en la pantalla principal.)
(() => {
    const form = document.getElementById('form-peso');
    if (!form) return;
    const TIMEOUT_MS = 4000;

    const hoy = () => {
        const d = new Date();
        return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
    };

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

    document.getElementById('peso-fecha').value = hoy();
    document.getElementById('peso-fecha').max = hoy();

    form.addEventListener('submit', async (ev) => {
        ev.preventDefault();
        const msg = document.getElementById('mensaje-peso');
        try {
            await pedirJSON('/api/mi-peso', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    kg: document.getElementById('peso-kg').value,
                    fecha: document.getElementById('peso-fecha').value
                })
            });
            msg.textContent = 'Peso guardado';
            msg.className = 'mensaje ok';
            document.getElementById('peso-kg').value = '';
        } catch (e) {
            console.error('[peso] no se pudo guardar el peso', e);                                // 3.18
            msg.textContent = e.name === 'AbortError' || e instanceof TypeError
                ? 'Sin conexión: no se pudo guardar el peso. Inténtalo de nuevo.' : e.message;
            msg.className = 'mensaje error';
        }
    });
})();