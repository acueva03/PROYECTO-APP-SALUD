// salud.js: pantalla del PACIENTE. Los gráficos y el historial viven en graficos.js (compartido
// con el supervisor); aquí solo queda lo propio del paciente: sus datos y el formulario de peso.
(() => {
    const { hoy, pedirJSON, dibujarPeso, dibujarAdherencia, dibujarHistorial } = window.Graficos;

    const canvasPeso = document.getElementById('grafico-peso');
    const avisoPeso = document.getElementById('aviso-grafico');
    const canvasTomas = document.getElementById('grafico-tomas');
    const listaHistorial = document.getElementById('lista-historial');

    // ---- Datos de salud ----
    async function cargarDatos() {
        try {
            const s = await pedirJSON('/api/mi-salud');
            document.querySelectorAll('[data-campo]').forEach(el => {
                const v = s[el.dataset.campo];
                el.textContent = (v === null || v === undefined || v === '') ? '—' : v;
            });
        } catch (e) { /* se queda con los guiones */ }
    }

    // ---- Peso ----
    async function cargarPeso() {
        try {
            dibujarPeso(canvasPeso, avisoPeso, await pedirJSON('/api/mi-peso'), 'Todavía no hay pesajes. Guarda el primero arriba.');
        } catch (e) {}
    }

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
            cargarPeso();
            cargarDatos();
        } catch (e) {
            msg.textContent = e.message;
            msg.className = 'mensaje error';
        }
    });

    // ---- Medicamentos ----
    async function cargarTomas() {
        try {
            const tomas = await pedirJSON('/api/mi-historial-tomas?dias=30');
            dibujarAdherencia(canvasTomas, tomas);
            dibujarHistorial(listaHistorial, tomas);
        } catch (e) {}
    }

    cargarDatos();
    cargarPeso();
    cargarTomas();
    setInterval(cargarTomas, 60000);   // para que se refleje una toma recién confirmada
})();