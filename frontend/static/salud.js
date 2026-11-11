// salud.js: pantalla del PACIENTE. Solo muestra sus datos y deja registrar el peso.
// Los gráficos y el historial de tomas están en la pantalla de salud del supervisor.
// No necesita Chart.js ni graficos.js: la pantalla del paciente carga lo mínimo.
(() => {
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

    // ---- Datos de salud ----
    async function cargarDatos() {
        try {
            const s = await pedirJSON('/api/mi-salud');
            document.querySelectorAll('[data-campo]').forEach(el => {
                const v = s[el.dataset.campo];
                el.textContent = (v === null || v === undefined || v === '') ? '—' : v;
            });
        } catch (e) {
            console.error('[salud] no se pudieron cargar los datos (se quedan los guiones)', e);   // 3.18
        }
    }

    // ---- Registrar peso ----
    document.getElementById('peso-fecha').value = hoy();
    document.getElementById('peso-fecha').max = hoy();

    document.getElementById('form-peso').addEventListener('submit', async (ev) => {
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
            cargarDatos();          // el "Peso (kg)" y el IMC de arriba se actualizan
        } catch (e) {
            console.error('[salud] no se pudo guardar el peso', e);                                // 3.18
            msg.textContent = e.name === 'AbortError' || e instanceof TypeError
                ? 'Sin conexión: no se pudo guardar el peso. Inténtalo de nuevo.' : e.message;
            msg.className = 'mensaje error';
        }
    });
    document.addEventListener('ficha-guardada', cargarDatos);
    cargarDatos();
})();