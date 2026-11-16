// salud.js: pantalla del PACIENTE. Solo muestra sus datos de salud.
// Registrar el peso y editar la ficha están en la pantalla "Ficha médica" (peso.js y ficha.js).
// Los gráficos y el historial de tomas están en la pantalla de salud del supervisor.
// No necesita Chart.js ni graficos.js: la pantalla del paciente carga lo mínimo.
(() => {
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

    document.addEventListener('ficha-guardada', cargarDatos);
    cargarDatos();
})();