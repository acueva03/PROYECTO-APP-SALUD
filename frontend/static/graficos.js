// graficos.js: funciones de gráficos e historial COMPARTIDAS por la pantalla del paciente (salud.js)
// y la del supervisor. Necesita Chart.js cargado antes. No toca ids concretos de ninguna pantalla:
// cada función recibe el elemento sobre el que dibuja, así se puede usar varias veces en una página.
(() => {
    const TIMEOUT_MS = 4000;

    // '2026-10-20' -> '20/10/2026'
    const legible = (f) => f.split('-').reverse().join('/');

    // Fecha LOCAL del navegador en formato AAAA-MM-DD (no usar toISOString: da la fecha en UTC)
    const fechaISO = (d) => d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
    const hoy = () => fechaISO(new Date());

    // fetch con límite de tiempo; lanza Error con el mensaje del servidor si la respuesta no es 2xx
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

    // Si el canvas ya tenía un gráfico, se destruye antes de dibujar otro encima
    function destruirGrafico(canvas) {
        const existente = Chart.getChart(canvas);
        if (existente) existente.destroy();
    }

    // ---- Peso: gráfica de líneas. registros = [{fecha: 'AAAA-MM-DD', kg: 62.5}, ...] ----
    // aviso (opcional): <p> donde se muestra "no hay pesajes" o "no se pudo cargar la librería"
    function dibujarPeso(canvas, aviso, registros, textoVacio = 'Todavía no hay pesajes.') {
        if (typeof Chart === 'undefined') {
            if (aviso) {
                aviso.textContent = 'No se pudo cargar la librería de gráficas.';
                aviso.hidden = false;
            }
            return;
        }
        if (aviso) {
            aviso.hidden = registros.length > 0;
            aviso.textContent = textoVacio;
        }
        destruirGrafico(canvas);
        new Chart(canvas, {
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

    // ---- Adherencia: % de tomas confirmadas en los últimos 14 días ----
    // tomas = [{fecha_prevista, estado, ...}, ...]
    function dibujarAdherencia(canvas, tomas) {
        if (typeof Chart === 'undefined') return;
        const dias = [];
        for (let i = 13; i >= 0; i--) {
            const d = new Date();
            d.setDate(d.getDate() - i);
            dias.push(fechaISO(d));
        }
        const porcentajes = dias.map(dia => {
            const delDia = tomas.filter(t => t.fecha_prevista === dia);
            if (delDia.length === 0) return null;   // día sin tomas: hueco, no 0 %
            return Math.round(100 * delDia.filter(t => t.estado === 'CONFIRMADA').length / delDia.length);
        });
        destruirGrafico(canvas);
        new Chart(canvas, {
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

    // ---- Historial de tomas: lista de las últimas 30 ----
    function dibujarHistorial(lista, tomas, maximo = 30) {
        lista.replaceChildren();
        if (tomas.length === 0) {
            const li = document.createElement('li');
            li.className = 'lista-vacia';
            li.textContent = 'Todavía no hay tomas registradas.';
            lista.append(li);
            return;
        }
        for (const t of tomas.slice(0, maximo)) {
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

    window.Graficos = { legible, hoy, pedirJSON, dibujarPeso, dibujarAdherencia, dibujarHistorial };
})();