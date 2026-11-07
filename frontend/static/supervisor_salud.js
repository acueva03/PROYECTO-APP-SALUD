// supervisor_salud.js: tarjeta "Salud" del panel del SUPERVISOR (solo lectura).
// Usa graficos.js. Lee el paciente de data-paciente-id; cuando P3 meta las pestañas por paciente,
// basta con llamar a SaludSupervisor.cargar(idDelPaciente) al cambiar de pestaña.
(() => {
    const seccion = document.getElementById('seccion-salud-supervisor');
    if (!seccion) return;        // sin paciente vinculado no hay nada que dibujar
    const { pedirJSON, dibujarPeso, dibujarAdherencia, dibujarHistorial } = window.Graficos;

    const canvasPeso = document.getElementById('grafico-peso');
    const avisoPeso = document.getElementById('aviso-grafico');
    const canvasTomas = document.getElementById('grafico-tomas');
    const lista = document.getElementById('lista-historial');
    const mensaje = document.getElementById('mensaje-salud');

    let pacienteId = seccion.dataset.pacienteId;
    let temporizador = null;

    const url = (parte) => '/api/supervisor/pacientes/' + pacienteId + '/' + parte;
    function error(texto) { mensaje.textContent = texto; mensaje.hidden = !texto; }

    async function cargarDatos() {
        const id = pacienteId;
        try {
            const s = await pedirJSON(url('salud'));
            if (id !== pacienteId) return;           // el supervisor cambió de paciente mientras cargaba
            seccion.querySelectorAll('[data-campo]').forEach(el => {
                const v = s[el.dataset.campo];
                el.textContent = (v === null || v === undefined || v === '') ? '—' : v;
            });
            error('');
        } catch (e) { error('No se pudieron cargar los datos de salud. Reintentando…'); }
    }

    async function cargarPeso() {
        const id = pacienteId;
        try {
            const registros = await pedirJSON(url('peso'));
            if (id !== pacienteId) return;
            dibujarPeso(canvasPeso, avisoPeso, registros, 'Este paciente todavía no ha registrado su peso.');
        } catch (e) { error('No se pudo cargar el peso. Reintentando…'); }
    }

    async function cargarTomas() {
        const id = pacienteId;
        try {
            const tomas = await pedirJSON(url('tomas?dias=30'));
            if (id !== pacienteId) return;
            dibujarAdherencia(canvasTomas, tomas);
            dibujarHistorial(lista, tomas);
        } catch (e) { error('No se pudieron cargar las tomas. Reintentando…'); }
    }

    function cargar(id) {
        if (id !== undefined) pacienteId = String(id);
        clearInterval(temporizador);
        cargarDatos();
        cargarPeso();
        cargarTomas();
        temporizador = setInterval(cargarTomas, 60000);   // refleja tomas confirmadas sin recargar
    }

    window.SaludSupervisor = { cargar };
    cargar();
})();