(() => {
    const TIMEOUT_MS = 4000;
    let graficoPeso = null;
    let graficoTomas = null;

    const legible = (f) => f.split('-').reverse().join('/');
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
        } catch (e) { /* se queda con los guiones */ }
    }

    // ---- Peso ----
    function dibujarPeso(registros) {
        const aviso = document.getElementById('aviso-grafico');
        if (typeof Chart === 'undefined') {
            aviso.textContent = 'No se pudo cargar la librería de gráficas.';
            aviso.hidden = false;
            return;
        }
        aviso.hidden = registros.length > 0;
        aviso.textContent = 'Todavía no hay pesajes. Guarda el primero arriba.';
        if (graficoPeso) graficoPeso.destroy();
        graficoPeso = new Chart(document.getElementById('grafico-peso'), {
            type: 'line',
            data: {
                labels: registros.map(r => legible(r.fecha)),
                datasets: [{
                    label: 'Peso (kg)',
                    data: registros.map(r => r.kg),
                    borderColor: '#0F2C59',
                    backgroundColor: '#E8EEF8',
                    fill: true,
                    tension: 0.3
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });
    }

    async function cargarPeso() {
        try { dibujarPeso(await pedirJSON('/api/mi-peso')); } catch (e) {}
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
    function dibujarAdherencia(tomas) {
        if (typeof Chart === 'undefined') return;
        const dias = [];
        for (let i = 13; i >= 0; i--) {
            const d = new Date();
            d.setDate(d.getDate() - i);
            dias.push(d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'));
        }
        const porcentajes = dias.map(dia => {
            const delDia = tomas.filter(t => t.fecha_prevista === dia);
            if (delDia.length === 0) return null;   // día sin tomas: hueco, no 0 %
            return Math.round(100 * delDia.filter(t => t.estado === 'CONFIRMADA').length / delDia.length);
        });
        if (graficoTomas) graficoTomas.destroy();
        graficoTomas = new Chart(document.getElementById('grafico-tomas'), {
            type: 'bar',
            data: {
                labels: dias.map(d => legible(d).slice(0, 5)),
                datasets: [{ label: '% de tomas confirmadas', data: porcentajes, backgroundColor: '#2E7D32' }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { min: 0, max: 100 } }
            }
        });
    }

    function dibujarHistorial(tomas) {
        const lista = document.getElementById('lista-historial');
        lista.replaceChildren();
        if (tomas.length === 0) {
            const li = document.createElement('li');
            li.className = 'lista-vacia';
            li.textContent = 'Todavía no hay tomas registradas.';
            lista.append(li);
            return;
        }
        for (const t of tomas.slice(0, 30)) {
            const li = document.createElement('li');
            const izq = document.createElement('span');
            izq.textContent = legible(t.fecha_prevista) + ' ' + t.hora_prevista + ' · ' + t.titulo + (t.dosis ? ' (' + t.dosis + ')' : '');
            const der = document.createElement('strong');
            if (t.estado === 'CONFIRMADA') {
                der.textContent = '✔ Tomada';
                der.className = 'toma-ok';
            } else {
                der.textContent = '⏳ Sin confirmar';
                der.className = 'toma-pendiente';
            }
            li.append(izq, der);
            lista.append(li);
        }
    }

    async function cargarTomas() {
        try {
            const tomas = await pedirJSON('/api/mi-historial-tomas?dias=30');
            dibujarAdherencia(tomas);
            dibujarHistorial(tomas);
        } catch (e) {}
    }

    cargarDatos();
    cargarPeso();
    cargarTomas();
    setInterval(cargarTomas, 60000);   // para que se refleje una toma recién confirmada
})();