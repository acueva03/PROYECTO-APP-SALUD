// checkin.js: tarjeta «¿Cómo estás hoy?» (check-in diario) de la pantalla del PACIENTE.
// Va DESPUÉS de errores.js, accesibilidad.js y conexion.js (ver paciente.html).
// Qué hace:
//   - Carga el estado de hoy (GET /api/mi-checkin) y lo pinta.
//   - Al pulsar «Estoy bien» envía POST /api/checkin y deshabilita el botón hasta mañana.
//   - Permite cambiar la hora límite y activar/desactivar el aviso (PUT /api/mi-checkin/config).
// Reglas del proyecto (riesgo 3.18): ningún catch vacío; se distingue fallo de red / servidor / código.
(() => {
    const boton = document.getElementById('btn-checkin');
    if (!boton) return;                       // la tarjeta no está en esta pantalla

    const TIMEOUT_MS = 4000;
    const RECARGA_MS = 5 * 60 * 1000;         // se vuelve a consultar cada 5 min (así el botón se reactiva al cambiar de día)

    // errores.js y accesibilidad.js son opcionales: si faltan, se usan versiones mínimas
    const Errores = window.AppErrores || {
        registrar: (contexto, error) => { console.error('[' + contexto + ']', error); return 'codigo'; },
        ErrorServidor: class extends Error { constructor(status, mensaje) { super(mensaje || 'El servidor respondió con el error ' + status); } }
    };
    const Accesibilidad = window.AppAccesibilidad || { leer: () => Promise.resolve(false), anunciar: () => {} };

    const $ = (id) => document.getElementById(id);
    const selectAnimo = $('checkin-animo');
    const texto = $('texto-checkin');
    const mensaje = $('mensaje-checkin');
    const formConfig = $('form-checkin-config');
    const inputHora = $('checkin-hora-limite');
    const inputActivo = $('checkin-activo');
    const mensajeConfig = $('mensaje-checkin-config');
    let opcionesPintadas = false;

    // fetch con límite de tiempo. Si el servidor responde con error lanza ErrorServidor (con su mensaje)
    async function pedirJSON(url, opciones = {}) {
        const controller = new AbortController();
        const t = setTimeout(() => controller.abort(), TIMEOUT_MS);
        try {
            const r = await fetch(url, { ...opciones, signal: controller.signal });
            const datos = await r.json().catch(() => ({}));
            if (!r.ok) throw new Errores.ErrorServidor(r.status, datos.error);
            return datos;
        } finally {
            clearTimeout(t);
        }
    }

    // Mensaje para el paciente según el tipo de fallo
    function textoDeError(contexto, error) {
        const tipo = Errores.registrar(contexto, error);
        if (tipo === 'red') return 'Sin conexión: no se ha podido guardar. Inténtalo de nuevo.';
        if (tipo === 'servidor') return error.message;
        return 'Algo ha fallado. Recarga la página.';
    }

    function mostrar(elemento, textoMensaje, ok) {
        elemento.textContent = textoMensaje;
        elemento.className = 'mensaje ' + (ok ? 'ok' : 'error');
    }

    // Rellena el selector de ánimo con las opciones que manda el servidor (una sola vez)
    function pintarOpciones(estados) {
        if (opcionesPintadas) return;
        for (const e of estados) {
            const op = document.createElement('option');
            op.value = e;
            op.textContent = e;
            selectAnimo.appendChild(op);
        }
        opcionesPintadas = true;
    }

    // Pinta el estado de hoy: botón activo si aún no lo ha hecho, o desactivado con la hora si ya lo hizo
    function pintar(estado) {
        pintarOpciones(estado.estados_animo || []);
        if (estado.hecho) {
            boton.disabled = true;
            selectAnimo.disabled = true;
            selectAnimo.value = estado.estado_animo || '';
            texto.textContent = 'Hoy ya has confirmado que estás bien (a las ' + estado.hora + '). ¡Gracias! Mañana podrás volver a hacerlo.';
        } else {
            boton.disabled = false;
            selectAnimo.disabled = false;
            texto.textContent = 'Pulsa el botón una vez al día para que tu supervisor sepa que estás bien.' +
                (estado.activo ? ' Si no lo haces antes de las ' + estado.hora_limite + ', tu supervisor recibirá un aviso.' : '');
        }
        // La configuración solo se rellena si el paciente no la está editando ahora mismo
        if (!formConfig.contains(document.activeElement)) {
            inputHora.value = estado.hora_limite;
            inputActivo.checked = estado.activo;
        }
    }

    async function cargar() {
        try {
            pintar(await pedirJSON('/api/mi-checkin'));
        } catch (e) {
            mostrar(mensaje, textoDeError('checkin: cargar', e), false);
        }
    }

    boton.addEventListener('click', async () => {
        boton.disabled = true;                                  // evita el doble toque mientras se envía
        mostrar(mensaje, 'Guardando…', true);
        try {
            const datos = await pedirJSON('/api/checkin', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ estado_animo: selectAnimo.value })
            });
            const aviso = datos.ya_hecho
                ? 'Hoy ya lo habías confirmado a las ' + datos.hora + '.'
                : '¡Hecho! Has confirmado que estás bien a las ' + datos.hora + '.';
            mostrar(mensaje, aviso, true);
            Accesibilidad.leer(aviso);                          // lectura en voz alta si el paciente la tiene activada
            await cargar();                                     // deja el botón deshabilitado hasta mañana
        } catch (e) {
            boton.disabled = false;                             // si falló, puede reintentar
            mostrar(mensaje, textoDeError('checkin: guardar', e), false);
        }
    });

    formConfig.addEventListener('submit', async (ev) => {
        ev.preventDefault();
        mostrar(mensajeConfig, 'Guardando…', true);
        try {
            await pedirJSON('/api/mi-checkin/config', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ hora_limite: inputHora.value, activo: inputActivo.checked })
            });
            mostrar(mensajeConfig, 'Configuración guardada', true);
            await cargar();
        } catch (e) {
            mostrar(mensajeConfig, textoDeError('checkin: configuración', e), false);
        }
    });

    cargar();
    setInterval(cargar, RECARGA_MS);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) cargar(); });
})();