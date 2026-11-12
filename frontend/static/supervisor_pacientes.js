// Se encarga de: las pestañas (chips), las tarjetas del Resumen y las subpestañas de cada paciente.
// supervisor.js sigue encargándose de las alertas SOS, el sonido y la conexión.
// Todo el texto que viene del servidor se pone con textContent (nunca innerHTML).
(() => {
    const TIMEOUT_MS = 4000;
    const INTERVALO_RESUMEN_MS = 5000;     // cada cuánto se refrescan las tarjetas
    const MINUTOS_PARA_AVISO_ROJO = 15;    // igual que en supervisor.js
    const NOMBRES_DIAS = ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom'];

    const chips = document.querySelectorAll('.chip[data-vista]');
    const vistas = document.querySelectorAll('.vista');
    const contenedorTarjetas = document.getElementById('tarjetas-pacientes');   // null si no hay pacientes
    const avisoListaCambiada = document.getElementById('aviso-lista-cambiada');

    // Los pacientes con los que Jinja pintó la página (para detectar si luego cambia la lista)
    const idsPintados = [...document.querySelectorAll('.vista[data-paciente-id]')].map(v => v.dataset.pacienteId);

    // ---------- Utilidades ----------
    // fetch con límite de tiempo; lanza Error con el mensaje del servidor si la respuesta no es 2xx
    async function pedirJSON(url) {
        const controller = new AbortController();
        const t = setTimeout(() => controller.abort(), TIMEOUT_MS);
        try {
            const r = await fetch(url, { signal: controller.signal });
            const datos = await r.json();
            if (!r.ok) throw new Error(datos.error || 'HTTP ' + r.status);
            return datos;
        } finally {
            clearTimeout(t);
        }
    }

    const fechaHora = (iso) => new Date(iso).toLocaleString('es-ES',
        { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });

    function liTexto(texto, clase) {
        const li = document.createElement('li');
        if (clase) li.className = clase;
        li.textContent = texto;
        return li;
    }

    // ---------- Navegación entre pestañas ----------
    // destino = 'resumen' o el id de un paciente (número o texto)
    function abrir(destino) {
        const nombre = destino === 'resumen' ? 'resumen' : 'paciente-' + destino;
        const vista = document.querySelector('.vista[data-vista="' + nombre + '"]');
        if (!vista) return;                                   // id que no existe: no hace nada
        vistas.forEach(v => { v.hidden = (v !== vista); });
        chips.forEach(c => {
            const activo = c.dataset.vista === nombre;
            c.classList.toggle('activo', activo);
            if (activo) c.setAttribute('aria-current', 'true'); else c.removeAttribute('aria-current');
        });
        if (vista.dataset.pacienteId) cargarSub(vista, subActiva(vista));
        window.scrollTo({ top: 0 });
    }

    chips.forEach(c => c.addEventListener('click',
        () => abrir(c.dataset.vista === 'resumen' ? 'resumen' : c.dataset.pacienteId)));

    // ---------- Subpestañas de un paciente ----------
    const subActiva = (vista) => vista.querySelector('.subpestana.activo').dataset.sub;

    function activarSub(vista, sub) {
        vista.querySelectorAll('.subpestana').forEach(b => {
            const activo = b.dataset.sub === sub;
            b.classList.toggle('activo', activo);
            if (activo) b.setAttribute('aria-current', 'true'); else b.removeAttribute('aria-current');
        });
        vista.querySelectorAll('.subvista').forEach(s => { s.hidden = (s.dataset.sub !== sub); });
        cargarSub(vista, sub);
    }

    document.querySelectorAll('.vista[data-paciente-id]').forEach(vista => {
        vista.querySelectorAll('.subpestana').forEach(b =>
            b.addEventListener('click', () => activarSub(vista, b.dataset.sub)));
    });

    // Carga los datos de la subpestaña que se está viendo
    async function cargarSub(vista, sub) {
        const id = vista.dataset.pacienteId;
        const mensaje = vista.querySelector('[data-mensaje]');
        try {
            if (sub === 'alertas') {
                pintarAlertas(vista, await pedirJSON('/api/supervisor/pacientes/' + id + '/alertas'));
            } else if (sub === 'medicacion') {
                pintarMedicacion(vista, await pedirJSON('/api/supervisor/pacientes/' + id + '/medicacion'));
            } else {
                // 'salud' y 'ficha' usan el mismo endpoint (el de P4): rellena todos los [data-campo]
                const s = await pedirJSON('/api/supervisor/pacientes/' + id + '/salud');
                vista.querySelectorAll('[data-campo]').forEach(el => {
                    const v = s[el.dataset.campo];
                    el.textContent = (v === null || v === undefined || v === '') ? '—' : v;
                });
            }
            mensaje.hidden = true;
        } catch (e) {
            mensaje.textContent = 'No se pudieron cargar los datos: ' + e.message;
            mensaje.hidden = false;
        }
    }

    function pintarAlertas(vista, alertas) {
        const ul = vista.querySelector('[data-lista="alertas"]');
        ul.replaceChildren();
        if (alertas.length === 0) {
            ul.append(liTexto('Este paciente no ha enviado ningún SOS.', 'lista-vacia'));
            return;
        }
        for (const a of alertas) {
            const activa = a.estado === 'ACTIVA';
            // Icono + texto: el estado no depende solo del color
            const li = liTexto((activa ? '⚠ SOS ACTIVO' : '✓ Atendido') + ' · ' + fechaHora(a.fecha_hora),
                               activa ? 'toma-tarde' : '');
            // atenderAlerta es la función de supervisor.js (declarada con "function", así que es global)
            if (activa && typeof window.atenderAlerta === 'function') {
                const boton = document.createElement('button');
                boton.type = 'button';
                boton.className = 'btn-atender';
                boton.textContent = 'Marcar como atendida';
                boton.addEventListener('click', async () => {
                    await window.atenderAlerta(a.alerta_id);
                    refrescar();
                });
                li.append(document.createElement('br'), boton);
            }
            ul.append(li);
        }
    }

    function descripcionRepeticion(a) {
        if (!a.es_repetitiva) return a.fecha ? 'una vez (' + a.fecha.split('-').reverse().join('/') + ')' : 'una vez';
        if (a.dias.length === 0) return 'todos los días';
        return a.dias.map(d => NOMBRES_DIAS[d]).join(', ');
    }

    function pintarMedicacion(vista, datos) {
        const pendientes = vista.querySelector('[data-lista="pendientes"]');
        pendientes.replaceChildren();
        if (datos.tomas_pendientes.length === 0) {
            pendientes.append(liTexto('Todo confirmado: no hay recordatorios pendientes.', 'lista-vacia'));
        }
        for (const t of datos.tomas_pendientes) {
            const minutos = Math.floor((Date.now() - new Date(t.creado).getTime()) / 60000);
            pendientes.append(liTexto(
                t.titulo + (t.dosis ? ' (' + t.dosis + ')' : '') + ' · prevista a las ' + t.hora_prevista +
                ' · sin confirmar desde hace ' + minutos + ' min',
                minutos >= MINUTOS_PARA_AVISO_ROJO ? 'toma-tarde' : ''));
        }

        const alarmas = vista.querySelector('[data-lista="alarmas"]');
        alarmas.replaceChildren();
        if (datos.alarmas.length === 0) {
            alarmas.append(liTexto('Este paciente no tiene alarmas programadas.', 'lista-vacia'));
        }
        for (const a of datos.alarmas) {
            alarmas.append(liTexto(
                a.hora + ' · ' + a.titulo + (a.dosis ? ' (' + a.dosis + ')' : '') +
                ' · ' + descripcionRepeticion(a) + (a.activa ? '' : ' · desactivada')));
        }

        // Riesgo 3.14.3: alarmas que el paciente eliminó, visibles para que el supervisor pueda restaurarlas
        const bloqueEliminadas = vista.querySelector('[data-bloque="eliminadas"]');
        const listaEliminadas = vista.querySelector('[data-lista="eliminadas"]');
        if (bloqueEliminadas && listaEliminadas) {
            listaEliminadas.replaceChildren();
            const eliminadas = datos.eliminadas || [];
            bloqueEliminadas.hidden = (eliminadas.length === 0);
            for (const a of eliminadas) {
                const li = liTexto(
                    a.hora + ' · ' + a.titulo + (a.dosis ? ' (' + a.dosis + ')' : '') +
                    (a.eliminada_en ? ' · eliminada el ' + fechaHora(a.eliminada_en) : ' · eliminada'));
                const boton = document.createElement('button');
                boton.type = 'button';
                boton.className = 'btn-restaurar';
                boton.textContent = 'Restaurar alarma';
                boton.addEventListener('click', async () => {
                    boton.disabled = true;
                    try {
                        const r = await fetch('/api/alarmas/' + a.id + '/restaurar', { method: 'POST' });
                        const res = await r.json();
                        if (!r.ok) throw new Error(res.error || 'HTTP ' + r.status);
                        refrescar();
                    } catch (err) {
                        const mensaje = vista.querySelector('[data-mensaje]');
                        if (mensaje) {
                            mensaje.textContent = 'No se pudo restaurar la alarma: ' + err.message;
                            mensaje.hidden = false;
                        }
                        boton.disabled = false;
                    }
                });
                li.append(document.createElement('br'), boton);
                listaEliminadas.append(li);
            }
        }
    }

    // ---------- Tarjetas del Resumen ----------
    function crearTarjeta(p) {
        const tarjeta = document.createElement('article');
        tarjeta.className = 'tarjeta-paciente' + (p.sos_activo ? ' con-sos' : '');

        const cabecera = document.createElement('div');
        cabecera.className = 'tarjeta-paciente-cab';
        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.setAttribute('aria-hidden', 'true');
        avatar.textContent = p.iniciales;
        const nombre = document.createElement('h3');
        nombre.textContent = p.nombre;
        cabecera.append(avatar, nombre);

        const estado = document.createElement('p');
        estado.className = 'estado-paciente ' + (p.sos_activo ? 'sos' : 'ok');
        estado.textContent = p.sos_activo ? '⚠ SOS activo' : '✓ Todo bien';

        const detalle = document.createElement('p');
        detalle.className = 'texto-suave';
        detalle.textContent = 'Última toma: ' + (p.ultima_toma ? fechaHora(p.ultima_toma) : 'sin tomas confirmadas') +
            ' · ' + p.tomas_pendientes + (p.tomas_pendientes === 1 ? ' toma sin confirmar' : ' tomas sin confirmar');

        const boton = document.createElement('button');
        boton.type = 'button';
        boton.className = 'btn btn-secundario';
        boton.textContent = 'Ver a ' + p.nombre;
        boton.addEventListener('click', () => abrir(p.id));

        tarjeta.append(cabecera, estado, detalle, boton);
        return tarjeta;
    }

    let ultimaHuella = '';

    async function refrescarResumen() {
        try {
            const pacientes = await pedirJSON('/api/supervisor/pacientes');

            // ¿Ha cambiado la lista de pacientes desde que se cargó la página?
            const ids = pacientes.map(p => String(p.id)).sort().join(',');
            avisoListaCambiada.hidden = (ids === [...idsPintados].sort().join(','));

            // Solo se repinta si algo ha cambiado (así no parpadea ni se pierde el foco del teclado)
            const huella = JSON.stringify(pacientes);
            if (huella !== ultimaHuella) {
                ultimaHuella = huella;
                if (contenedorTarjetas) contenedorTarjetas.replaceChildren(...pacientes.map(crearTarjeta));
                for (const p of pacientes) {
                    const chipSOS = document.querySelector('.chip[data-paciente-id="' + p.id + '"] .chip-sos');
                    if (chipSOS) chipSOS.hidden = !p.sos_activo;
                    const estado = document.querySelector('.vista[data-paciente-id="' + p.id + '"] [data-estado-paciente]');
                    if (estado) estado.textContent = p.sos_activo ? '⚠ SOS activo' : '✓ Todo bien';
                }
            }
        } catch (e) {
            // Sin conexión: supervisor.js ya enseña el aviso. Aquí no hace falta repetirlo.
        }
    }

    // Refresca el resumen y, si hay un paciente abierto en Alertas o Medicación, esa pestaña también
    async function refrescar() {
        await refrescarResumen();
        const abierta = document.querySelector('.vista[data-paciente-id]:not([hidden])');
        if (abierta) {
            const sub = subActiva(abierta);
            if (sub === 'alertas' || sub === 'medicacion') cargarSub(abierta, sub);
        }
    }

    // supervisor.js lo usa: window.PanelPacientes.abrir(idPaciente) o abrir('resumen')
    window.PanelPacientes = { abrir };

    refrescar();
    setInterval(refrescar, INTERVALO_RESUMEN_MS);
})();