// conexion.js: ALARMAS de la pantalla del paciente.
// El botón SOS está en sos.js (riesgo 3.18): un fallo aquí nunca puede dejar sin SOS al paciente.
// Necesita errores.js (window.AppErrores) y, si está, accesibilidad.js (window.AppAccesibilidad).
//
// Riesgos de esta pantalla:
//   3.12 Las alarmas solo suenan con la pestaña abierta -> aviso fijo, pantalla encendida (Wake Lock) y
//        comprobación inmediata al volver a la pestaña.
//   3.14 Borrado accidental -> diálogo propio con nombre y dosis, "Desactivar" como acción principal,
//        borrado lógico con "Deshacer" y papelera de alarmas eliminadas.
//   3.16 Confirmación en bloque -> cada aviso tiene sus propios botones y "Deshacer" durante 1 minuto.
//   3.18 Errores ocultos -> ningún catch vacío; se distingue fallo de red de error del servidor y de código.

const Errores = window.AppErrores;
const Accesibilidad = window.AppAccesibilidad || {
    leer: () => Promise.resolve(false), anunciar: () => {}, vozActivada: () => false
};

// ===================================================================
// CONFIGURACIÓN Y ELEMENTOS
// ===================================================================
const INTERVALO_COMPROBACION_MS = 1000;
const INTERVALO_RECARGA_MS = 30000;
const TIMEOUT_MS = 2500;
const POSPONER_MS = 10 * 60 * 1000;
const DESHACER_TOMA_MS = 60 * 1000;          // 3.16.3: "Deshacer" visible durante 1 minuto
const DESHACER_ELIMINAR_MS = 30 * 1000;      // 3.14: "Deshacer" tras eliminar una alarma
const VOLUMEN_MIENTRAS_HABLA = 0.25;         // baja la alarma mientras se lee el aviso en voz alta

const sonidoAlarma = new Audio('/static/alarma.mp3');
sonidoAlarma.loop = true;

const $ = (id) => document.getElementById(id);
const avisoAlarma = $('aviso-alarma');
const tituloAvisoAlarma = $('titulo-aviso-alarma');
const listaAvisos = $('lista-avisos');
const btnLeerAvisos = $('btn-leer-avisos');
const bloqueHechas = $('tomas-hechas');
const listaHechas = $('lista-hechas');
const btnSonidoAlarma = $('btn-activar-sonido-alarma');
const estadoPantalla = $('estado-pantalla');
const estadoSistema = document.querySelector('.estado-sistema');
const puntoEstado = $('punto-estado');
const textoEstado = $('texto-estado');

const formAlarma = $('form-alarma');
const selectRepeticion = $('alarma-repeticion');
const fieldsetDias = $('alarma-dias');
const inputTitulo = $('alarma-titulo');
const inputDosis = $('alarma-dosis');
const inputFecha = $('alarma-fecha');
const inputHora = $('alarma-hora');
const mensajeAlarma = $('mensaje-alarma');
const accionDeshacerEliminar = $('accion-deshacer-eliminar');
const listaAlarmas = $('lista-alarmas');
const listaInactivas = $('lista-inactivas');
const listaEliminadas = $('lista-eliminadas');
const contadorPapelera = $('contador-papelera');
const dialogoEliminar = $('dialogo-eliminar');

// ===================================================================
// UTILIDADES
// ===================================================================
function horaActual() {
    const ahora = new Date();
    return String(ahora.getHours()).padStart(2, '0') + ':' + String(ahora.getMinutes()).padStart(2, '0');
}
function formatearFecha(d) {
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}
function fechaActual() { return formatearFecha(new Date()); }
function fechaLegible(fecha) { return fecha.split('-').reverse().join('/'); }
function momentoAlarma(alarma) { return new Date(alarma.fecha + 'T' + alarma.hora + ':00'); }
function proximaFecha(hora) {
    const d = new Date();
    if (hora <= horaActual()) d.setDate(d.getDate() + 1);
    return formatearFecha(d);
}
const esperar = (ms) => new Promise(r => setTimeout(r, ms));

// "Paracetamol (500 mg)" o "Beber agua"
function nombreConDosis(alarma) {
    return alarma.titulo + (alarma.dosis ? ' (' + alarma.dosis + ')' : '');
}

const NOMBRES_DIAS = ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom'];
function textoRepeticion(alarma) {
    if (!alarma.es_repetitiva) return '';
    const dias = alarma.dias || [];
    if (dias.length === 0 || dias.length === 7) return ' (cada día)';
    if (dias.join() === '0,1,2,3,4') return ' (lunes a viernes)';
    if (dias.join() === '5,6') return ' (fines de semana)';
    return ' (' + dias.map(d => NOMBRES_DIAS[d]).join(', ') + ')';
}

// fetch con tiempo máximo. El cuerpo se construye ANTES de llamar (fuera del try de red, 3.18.1):
// así un fallo al prepararlo es un error de código y no se confunde con "sin conexión".
// Devuelve la respuesta; lanza ErrorServidor si no es 2xx, o el error de red tal cual.
async function pedir(url, { metodo = 'GET', cuerpo, timeout = TIMEOUT_MS } = {}) {
    const opciones = { method: metodo };
    if (cuerpo !== undefined) {
        opciones.headers = { 'Content-Type': 'application/json' };
        opciones.body = JSON.stringify(cuerpo);
    }
    const controller = new AbortController();
    opciones.signal = controller.signal;
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    let respuesta;
    try {
        respuesta = await fetch(url, opciones);
    } finally {
        clearTimeout(timeoutId);
    }
    if (respuesta.status === 401) {               // sesión caducada: banner y a iniciar sesión (riesgo 3.17)
        document.body.insertAdjacentHTML('afterbegin', '<div style="background-color: #f44336; color: white; text-align: center; padding: 15px; position: fixed; top: 0; left: 0; width: 100%; z-index: 9999; font-weight: bold; font-size: 1.2rem;">Tu sesión ha caducado. Redirigiendo al login...</div>');
        setTimeout(() => { window.location.href = '/login'; }, 3000);
        throw new Errores.ErrorServidor(401, 'Tu sesión ha caducado');
    }
    if (!respuesta.ok) {
        let mensaje = '';
        try {
            mensaje = (await respuesta.json()).error || '';
        } catch (error) {
            console.error('Respuesta de error sin JSON', error);
        }
        throw new Errores.ErrorServidor(respuesta.status, mensaje);
    }
    return respuesta;
}

// Mensaje para el paciente según el tipo de error (3.18.3: decir qué ha fallado)
function textoDeError(error, accion) {
    const tipo = Errores.registrar(accion, error);
    if (tipo === 'red') return 'Sin conexión: no se pudo ' + accion + '. Inténtalo de nuevo.';
    if (tipo === 'servidor') return error.message || ('El servidor no pudo ' + accion + '.');
    return 'Error de la aplicación al ' + accion + '. Recarga la página.';
}

function marcarConexion(ok) {
    const texto = ok ? 'Sistema activo' : 'Sin conexión con el servidor';
    if (textoEstado.textContent === texto) return;      // no repetir el anuncio del role="status"
    estadoSistema.classList.toggle('sin-conexion', !ok);
    puntoEstado.classList.remove('gris');
    puntoEstado.classList.toggle('verde', ok);
    puntoEstado.classList.toggle('rojo', !ok);
    textoEstado.textContent = texto;
}

// ===================================================================
// 3.12: PANTALLA ENCENDIDA (Screen Wake Lock API)
// ===================================================================
let bloqueoPantalla = null;

function mostrarEstadoPantalla(texto) {
    if (estadoPantalla && estadoPantalla.textContent !== texto) estadoPantalla.textContent = texto;
}

async function mantenerPantallaEncendida() {
    if (!('wakeLock' in navigator)) {
        mostrarEstadoPantalla('Tu navegador no puede mantener la pantalla encendida: quita el bloqueo automático del móvil mientras uses la app.');
        return;
    }
    if (document.visibilityState !== 'visible' || bloqueoPantalla) return;
    try {
        bloqueoPantalla = await navigator.wakeLock.request('screen');
        mostrarEstadoPantalla('La pantalla no se apagará sola mientras esta página esté abierta.');
        bloqueoPantalla.addEventListener('release', () => { bloqueoPantalla = null; });
    } catch (error) {
        // Sin HTTPS, con ahorro de batería, o el navegador lo deniega: no es un error de código
        console.error('No se pudo mantener la pantalla encendida', error);
        mostrarEstadoPantalla('No se puede mantener la pantalla encendida: quita el bloqueo automático del móvil mientras uses la app.');
    }
}

// Al volver a la pestaña: el navegador suelta el bloqueo al ocultarla, así que se pide otra vez,
// y se comprueban YA las alarmas (en segundo plano los temporizadores van frenados o parados)
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState !== 'visible') return;
    mantenerPantallaEncendida();
    comprobarAlarmas();
    cargarAlarmas().then(comprobarAlarmas);
});

// ===================================================================
// CARGA DE ALARMAS
// ===================================================================
let alarmas = [];
let alarmasInactivas = [];
let alarmasCargadasUnaVez = false;
let huellaAlarmas = '';
const yaDisparadas = new Set();

async function cargarAlarmas() {
    try {
        const respuesta = await pedir('/api/mis-alarmas?todas=1');
        const todas = await respuesta.json();
        alarmas = todas.filter(a => a.activa);
        alarmasInactivas = todas.filter(a => !a.activa);
        alarmasCargadasUnaVez = true;
        marcarConexion(true);
        // Solo se repinta si algo cambió: repintar cada 30 s hacía perder el foco del teclado
        // y del lector de pantalla a quien estuviera en un botón de la lista
        const huella = JSON.stringify(todas);
        if (huella !== huellaAlarmas) {
            huellaAlarmas = huella;
            mostrarListaAlarmas();
        }
    } catch (error) {
        const tipo = Errores.registrar('cargar las alarmas', error);
        if (tipo !== 'codigo') marcarConexion(false);
        if (!alarmasCargadasUnaVez) {
            listaAlarmas.replaceChildren(crearItemVacio('No se pudieron cargar tus alarmas. Reintentando…'));
        }
    }
}

// ===================================================================
// 3.16: AVISOS INDIVIDUALES (cada uno con sus botones)
// ===================================================================
let avisosEnPantalla = [];
let siguienteIdAviso = 1;

function textoParaVoz(avisos) {
    return avisos.map(a => 'Es la hora de ' + a.titulo + (a.dosis ? ', ' + a.dosis : '') +
        (a.nota ? '. ' + a.nota : '')).join('. ') + '.';
}

// Solo cambia el título. Los avisos se añaden y se quitan de uno en uno (no se repinta la lista):
// así el foco del teclado o del lector de pantalla no salta cuando llega un aviso nuevo
function actualizarTituloAvisos() {
    tituloAvisoAlarma.textContent = avisosEnPantalla.length === 1
        ? 'Es la hora de:'
        : 'Tienes ' + avisosEnPantalla.length + ' avisos:';
}

function crearItemAviso(aviso) {
    const li = document.createElement('li');
    li.className = 'item-aviso';
    li.dataset.aviso = aviso.id;

    const texto = document.createElement('p');
    texto.className = 'item-aviso-texto';
    const titulo = document.createElement('strong');
    titulo.textContent = aviso.titulo;
    texto.append(titulo);
    if (aviso.dosis) {
        const dosis = document.createElement('span');
        dosis.className = 'item-aviso-dosis';
        dosis.textContent = aviso.dosis;
        texto.append(' ', dosis);
    }
    if (aviso.nota) {
        const nota = document.createElement('span');
        nota.className = 'item-aviso-nota';
        nota.textContent = aviso.nota;
        texto.append(nota);
    }

    const acciones = document.createElement('div');
    acciones.className = 'item-aviso-acciones';
    const hecho = crearBoton('✔ Ya lo hice', () => confirmarAviso(aviso), 'btn btn-primario btn-grande');
    hecho.setAttribute('aria-label', 'Ya lo hice: ' + aviso.titulo + (aviso.dosis ? ', ' + aviso.dosis : ''));
    const posponer = crearBoton('Posponer 10 minutos', () => posponerAviso(aviso), 'btn btn-secundario');
    posponer.setAttribute('aria-label', 'Posponer 10 minutos: ' + aviso.titulo);
    acciones.append(hecho, posponer);

    li.append(texto, acciones);
    return li;
}

function reproducirSonido() {
    sonidoAlarma.play()
        .then(() => { btnSonidoAlarma.hidden = true; })
        .catch((error) => {
            // El navegador bloquea el sonido hasta que se toca la página: se enseña el botón para activarlo
            console.error('El navegador no deja sonar la alarma todavía', error);
            btnSonidoAlarma.hidden = false;
        });
}

async function leerAvisos(avisos) {
    if (!Accesibilidad.vozActivada() || avisos.length === 0) return;
    sonidoAlarma.volume = VOLUMEN_MIENTRAS_HABLA;
    await Accesibilidad.leer(textoParaVoz(avisos));
    sonidoAlarma.volume = 1;
}

function mostrarAviso(aviso) {
    const estabaCerrado = avisoAlarma.hidden;
    aviso.id = siguienteIdAviso++;
    avisosEnPantalla.push(aviso);
    listaAvisos.append(crearItemAviso(aviso));
    actualizarTituloAvisos();
    avisoAlarma.hidden = false;
    if (estabaCerrado) {
        // Patrón alertdialog: el foco va al primer botón y el lector lee el aviso
        const primerBoton = listaAvisos.querySelector('button');
        if (primerBoton) primerBoton.focus();
    } else {
        Accesibilidad.anunciar('Nuevo aviso: ' + aviso.titulo + (aviso.dosis ? ', ' + aviso.dosis : ''), true);
    }
    reproducirSonido();
    if (navigator.vibrate) navigator.vibrate([500, 300, 500]);
    leerAvisos([aviso]);
}

function quitarDePantalla(aviso) {
    avisosEnPantalla = avisosEnPantalla.filter(a => a !== aviso);
    const li = listaAvisos.querySelector('[data-aviso="' + aviso.id + '"]');
    if (li) li.remove();
    if (avisosEnPantalla.length === 0) {
        detenerAviso();
        return;
    }
    actualizarTituloAvisos();
    const primerBoton = listaAvisos.querySelector('button');
    if (primerBoton) primerBoton.focus();
}

function detenerAviso() {
    sonidoAlarma.pause();
    sonidoAlarma.currentTime = 0;
    if (navigator.vibrate) navigator.vibrate(0);
    if (Accesibilidad.vozActivada()) window.speechSynthesis.cancel();
    avisoAlarma.hidden = true;
}

// ----- Ya lo hice -----
function confirmarAviso(aviso) {
    quitarDePantalla(aviso);
    aviso.confirmado = true;
    if (aviso.registroId) aviso.confirmando = confirmarToma(aviso);
    else aviso.confirmarAlLlegar = true;     // registrarSonada confirmará en cuanto el servidor responda
    anadirAHechas(aviso);
    Accesibilidad.anunciar('Hecho: ' + aviso.titulo + '. Tienes un minuto para deshacerlo.');
}

// Reintenta: si la confirmación no llega, el supervisor vería la toma como pendiente
async function confirmarToma(aviso, intento = 1) {
    try {
        await pedir('/api/tomas/' + aviso.registroId + '/confirmar', { metodo: 'POST' });
        return true;
    } catch (error) {
        const tipo = Errores.registrar('confirmar la toma', error);
        if (tipo === 'red' && intento < 5) {
            await esperar(3000 * intento);
            if (!aviso.confirmado) return false;          // se deshizo mientras tanto
            return confirmarToma(aviso, intento + 1);
        }
        mostrarMensajeAlarma('No se pudo guardar que hiciste «' + aviso.titulo + '». Tu supervisor lo verá como pendiente.', true);
        return false;
    }
}

// ----- Deshacer (3.16.3) -----
function anadirAHechas(aviso) {
    const li = document.createElement('li');
    const texto = document.createElement('span');
    texto.textContent = '✔ Hecho: ' + aviso.titulo + (aviso.dosis ? ' (' + aviso.dosis + ')' : '');
    const deshacer = crearBoton('Deshacer', () => deshacerConfirmacion(aviso, li), 'btn-neutro-alarma');
    deshacer.setAttribute('aria-label', 'Deshacer: ' + aviso.titulo);
    li.append(texto, deshacer);
    listaHechas.append(li);
    bloqueHechas.hidden = false;
    if (avisoAlarma.hidden) deshacer.focus();             // que el foco no se pierda al cerrarse el aviso
    aviso.temporizadorDeshacer = setTimeout(() => quitarDeHechas(li), DESHACER_TOMA_MS);
}

function quitarDeHechas(li) {
    li.remove();
    bloqueHechas.hidden = listaHechas.children.length === 0;
}

async function deshacerConfirmacion(aviso, li) {
    clearTimeout(aviso.temporizadorDeshacer);
    quitarDeHechas(li);
    aviso.confirmado = false;
    aviso.confirmarAlLlegar = false;
    if (aviso.confirmando) await aviso.confirmando;       // espera a que termine la confirmación en curso
    if (aviso.registroId) {
        try {
            await pedir('/api/tomas/' + aviso.registroId + '/deshacer', { metodo: 'POST' });
        } catch (error) {
            mostrarMensajeAlarma(textoDeError(error, 'deshacer'), true);
            return;
        }
    }
    // Se vuelve a mostrar el MISMO aviso: si el servidor aún no había dado el registroId, llegará a este objeto
    mostrarAviso(aviso);
}

// ----- Posponer -----
function posponerAviso(aviso) {
    quitarDePantalla(aviso);
    const vuelve = new Date(Date.now() + POSPONER_MS);
    const hora = String(vuelve.getHours()).padStart(2, '0') + ':' + String(vuelve.getMinutes()).padStart(2, '0');
    mostrarMensajeAlarma('«' + aviso.titulo + '» te lo recordaré a las ' + hora + '.', false);
    setTimeout(() => mostrarAviso(aviso), POSPONER_MS);      // el mismo objeto (ver deshacerConfirmacion)
}

btnLeerAvisos.addEventListener('click', () => {
    Accesibilidad.leer(textoParaVoz(avisosEnPantalla), { forzar: true });
});

// ===================================================================
// DISPARO DE ALARMAS
// ===================================================================
function dispararAlarma(alarma, retrasoMin) {
    const aviso = {
        titulo: alarma.titulo,
        dosis: alarma.dosis || '',
        nota: retrasoMin >= 2 ? 'Perdida: era el ' + fechaLegible(alarma.fecha) + ' a las ' + alarma.hora : '',
        registroId: null,
        confirmarAlLlegar: false
    };
    mostrarAviso(aviso);
    return aviso;
}

function comprobarAlarmas() {
    const ahoraMs = Date.now();
    for (const alarma of alarmas) {
        if (!alarma.fecha) continue;
        const momento = momentoAlarma(alarma);
        if (isNaN(momento) || momento.getTime() > ahoraMs) continue;
        const clave = alarma.id + '|' + alarma.fecha + '|' + alarma.hora;
        if (yaDisparadas.has(clave)) continue;
        yaDisparadas.add(clave);
        const retrasoMin = Math.floor((ahoraMs - momento.getTime()) / 60000);
        const aviso = dispararAlarma(alarma, retrasoMin);
        registrarSonada(alarma, fechaActual(), horaActual(), aviso);
    }
}

async function registrarSonada(alarma, fechaLocal, horaLocal, aviso, intento = 1) {
    const cuerpo = { fecha_local: fechaLocal, hora_local: horaLocal, fecha_prevista: alarma.fecha };
    try {
        const r = await pedir('/api/alarmas/' + alarma.id + '/sonada',
                              { metodo: 'POST', cuerpo, timeout: TIMEOUT_MS * 2 });
        const datos = await r.json();
        aviso.registroId = datos.registro_id;
        if (aviso.confirmarAlLlegar) aviso.confirmando = confirmarToma(aviso);
        await cargarAlarmas();
    } catch (error) {
        const tipo = Errores.registrar('registrar la alarma', error);
        // 400 (reloj del móvil mal), 403, 404 (alarma eliminada): reintentar no arregla nada
        if (tipo === 'red' && intento < 10) {
            setTimeout(() => registrarSonada(alarma, fechaLocal, horaLocal, aviso, intento + 1), 5000 * intento);
        } else if (tipo === 'servidor' && error.status >= 500 && intento < 10) {
            setTimeout(() => registrarSonada(alarma, fechaLocal, horaLocal, aviso, intento + 1), 5000 * intento);
        }
    }
}

async function cargarTomasPendientes() {
    try {
        const r = await pedir('/api/mis-tomas-pendientes');
        const tomas = await r.json();
        for (const t of tomas) {
            const cuando = (t.fecha_prevista === fechaActual() ? '' : fechaLegible(t.fecha_prevista) + ' ') + t.hora_prevista;
            mostrarAviso({
                titulo: t.titulo,
                dosis: t.dosis || '',
                nota: 'Pendiente: era a las ' + cuando,
                registroId: t.toma_id,
                confirmarAlLlegar: false
            });
        }
    } catch (error) {
        // Si falla, no se pierde nada: comprobarAlarmas sigue funcionando y se reintenta al recargar
        Errores.registrar('cargar las tomas pendientes', error);
    }
}

btnSonidoAlarma.addEventListener('click', async () => {
    mantenerPantallaEncendida();            // aprovecha el toque del usuario
    try {
        await sonidoAlarma.play();
        if (avisoAlarma.hidden) { sonidoAlarma.pause(); sonidoAlarma.currentTime = 0; }
        btnSonidoAlarma.hidden = true;
        Accesibilidad.anunciar('Sonido de alarmas activado.');
    } catch (error) {
        Errores.registrar('activar el sonido', error);
        mostrarMensajeAlarma('El navegador no deja reproducir sonido. Revisa que el móvil no esté en silencio.', true);
    }
});

// ===================================================================
// LISTAS DE ALARMAS
// ===================================================================
function mostrarMensajeAlarma(texto, esError) {
    mensajeAlarma.textContent = texto;
    mensajeAlarma.className = 'mensaje-alarma ' + (esError ? 'error' : 'ok');
}

function crearItemVacio(mensaje) {
    const vacio = document.createElement('li');
    vacio.className = 'lista-vacia';
    vacio.textContent = mensaje;
    return vacio;
}

function crearItemAlarma(textoAlarma, ...botones) {
    const li = document.createElement('li');
    const texto = document.createElement('span');
    texto.textContent = textoAlarma;
    const acciones = document.createElement('div');
    acciones.className = 'acciones-alarma';
    acciones.append(...botones);
    li.append(texto, acciones);
    return li;
}

function crearBoton(etiqueta, alHacerClic, clase = 'btn-quitar-alarma', etiquetaAccesible = '') {
    const boton = document.createElement('button');
    boton.type = 'button';
    boton.className = clase;
    boton.textContent = etiqueta;
    if (etiquetaAccesible) boton.setAttribute('aria-label', etiquetaAccesible);
    boton.addEventListener('click', alHacerClic);
    return boton;
}

function mostrarListaAlarmas() {
    listaAlarmas.replaceChildren();
    if (alarmas.length === 0) listaAlarmas.append(crearItemVacio('No tienes alarmas activas.'));
    const ordenadas = [...alarmas].sort((a, b) => ((a.fecha || '') + a.hora).localeCompare((b.fecha || '') + b.hora));
    for (const alarma of ordenadas) {
        const texto = (alarma.fecha ? fechaLegible(alarma.fecha) + ' ' : '') + alarma.hora + ' · ' + nombreConDosis(alarma) + textoRepeticion(alarma);
        const btnDesactivar = crearBoton('Desactivar', () => desactivarAlarma(alarma), 'btn-neutro-alarma',
                                         'Desactivar la alarma ' + nombreConDosis(alarma));
        const btnEliminar = crearBoton('Eliminar', () => eliminarAlarma(alarma), 'btn-quitar-alarma',
                                       'Eliminar la alarma ' + nombreConDosis(alarma));
        listaAlarmas.append(crearItemAlarma(texto, btnDesactivar, btnEliminar));
    }

    listaInactivas.replaceChildren();
    if (alarmasInactivas.length === 0) {
        listaInactivas.append(crearItemVacio('Todavía no hay alarmas desactivadas ni que hayan sonado.'));
        return;
    }
    const recientes = [...alarmasInactivas].sort((a, b) => ((b.fecha || '') + b.hora).localeCompare((a.fecha || '') + a.hora)).slice(0, 10);
    for (const alarma of recientes) {
        let estado = 'desactivada';
        if (alarma.ultima_vez_sono) {
            estado = 'sonó el ' + new Date(alarma.ultima_vez_sono).toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' });
        }
        const texto = alarma.hora + ' · ' + nombreConDosis(alarma) + ' (' + estado + ')';
        const btnReactivar = crearBoton('Reactivar', () => reactivarAlarma(alarma), 'btn-neutro-alarma',
                                        'Reactivar la alarma ' + nombreConDosis(alarma));
        const btnEliminar = crearBoton('Eliminar', () => eliminarAlarma(alarma), 'btn-quitar-alarma',
                                       'Eliminar la alarma ' + nombreConDosis(alarma));
        listaInactivas.append(crearItemAlarma(texto, btnReactivar, btnEliminar));
    }
}

async function desactivarAlarma(alarma) {
    try {
        await pedir('/api/alarmas/' + alarma.id + '/estado', { metodo: 'PATCH', cuerpo: { activa: false } });
        mostrarMensajeAlarma('Alarma desactivada: ' + nombreConDosis(alarma) + '. Puedes reactivarla cuando quieras.', false);
    } catch (error) {
        mostrarMensajeAlarma(textoDeError(error, 'desactivar la alarma'), true);
    }
    await cargarAlarmas();
}

async function reactivarAlarma(alarma) {
    try {
        await pedir('/api/alarmas/' + alarma.id + '/estado',
                    { metodo: 'PATCH', cuerpo: { activa: true, fecha: proximaFecha(alarma.hora) } });
        mostrarMensajeAlarma('Alarma reactivada: ' + nombreConDosis(alarma) + '.', false);
    } catch (error) {
        mostrarMensajeAlarma(textoDeError(error, 'reactivar la alarma'), true);
    }
    await cargarAlarmas();
}

// ===================================================================
// 3.14: ELIMINAR CON DIÁLOGO PROPIO, DESHACER Y PAPELERA
// ===================================================================
// Devuelve una promesa con 'desactivar', 'eliminar' o '' (cancelar / tecla Esc)
function preguntarEliminar(alarma) {
    const conDosis = Boolean(alarma.dosis);
    $('texto-dialogo-eliminar').textContent = conDosis
        ? 'Vas a eliminar la alarma de ' + alarma.titulo + ' ' + alarma.dosis + '.'
        : 'Vas a eliminar la alarma «' + alarma.titulo + '».';
    $('ayuda-dialogo-eliminar').textContent = conDosis
        ? 'Si solo quieres que deje de sonar, desactívala: podrás reactivarla cuando quieras.'
        : 'Podrás recuperarla durante 30 días desde «Alarmas eliminadas».';
    // Con dosis (medicación) la acción destacada es Desactivar y Eliminar queda en segundo plano
    $('btn-dialogo-desactivar').hidden = !conDosis || !alarma.activa;
    $('btn-dialogo-eliminar').className = conDosis ? 'btn btn-peligro-discreto' : 'btn btn-peligro btn-grande';

    if (!dialogoEliminar || typeof dialogoEliminar.showModal !== 'function') {
        // Navegador antiguo sin <dialog>: se usa la confirmación del navegador
        return Promise.resolve(window.confirm($('texto-dialogo-eliminar').textContent + ' ¿Eliminarla?') ? 'eliminar' : '');
    }
    return new Promise((resolver) => {
        dialogoEliminar.returnValue = '';
        dialogoEliminar.addEventListener('close', () => resolver(dialogoEliminar.returnValue), { once: true });
        dialogoEliminar.showModal();
        // El foco empieza en la opción SEGURA, nunca en Eliminar
        const primero = conDosis && alarma.activa ? $('btn-dialogo-desactivar') : $('btn-dialogo-cancelar');
        primero.focus();
    });
}

async function eliminarAlarma(alarma) {
    const decision = await preguntarEliminar(alarma);
    if (decision === 'desactivar') { await desactivarAlarma(alarma); return; }
    if (decision !== 'eliminar') return;
    try {
        await pedir('/api/alarmas/' + alarma.id, { metodo: 'DELETE' });
        mostrarMensajeAlarma('Alarma eliminada: ' + nombreConDosis(alarma) + '.', false);
        ofrecerDeshacerEliminar(alarma);
    } catch (error) {
        mostrarMensajeAlarma(textoDeError(error, 'eliminar la alarma'), true);
    }
    await Promise.all([cargarAlarmas(), cargarEliminadas()]);
}

let temporizadorDeshacerEliminar = null;
function ofrecerDeshacerEliminar(alarma) {
    clearTimeout(temporizadorDeshacerEliminar);
    const boton = crearBoton('Deshacer', async () => {
        accionDeshacerEliminar.replaceChildren();
        await restaurarAlarma(alarma);
    }, 'btn-neutro-alarma', 'Deshacer: recuperar la alarma ' + nombreConDosis(alarma));
    accionDeshacerEliminar.replaceChildren(boton);
    boton.focus();
    temporizadorDeshacerEliminar = setTimeout(() => accionDeshacerEliminar.replaceChildren(), DESHACER_ELIMINAR_MS);
}

async function restaurarAlarma(alarma) {
    try {
        const r = await pedir('/api/alarmas/' + alarma.id + '/restaurar', { metodo: 'POST' });
        const datos = await r.json();
        const a = datos.alarma;
        mostrarMensajeAlarma('Alarma recuperada: ' + nombreConDosis(a) +
            (a.activa ? '. Sonará el ' + fechaLegible(a.fecha) + ' a las ' + a.hora + '.' : '.'), false);
    } catch (error) {
        mostrarMensajeAlarma(textoDeError(error, 'recuperar la alarma'), true);
    }
    await Promise.all([cargarAlarmas(), cargarEliminadas()]);
}

let huellaEliminadas = '';
async function cargarEliminadas() {
    try {
        const r = await pedir('/api/mis-alarmas-eliminadas');
        const eliminadas = await r.json();
        const huella = JSON.stringify(eliminadas);
        if (huella === huellaEliminadas) return;
        huellaEliminadas = huella;
        contadorPapelera.textContent = eliminadas.length;
        listaEliminadas.replaceChildren();
        if (eliminadas.length === 0) {
            listaEliminadas.append(crearItemVacio('No has eliminado ninguna alarma en los últimos 30 días.'));
            return;
        }
        for (const a of eliminadas) {
            const cuando = new Date(a.eliminada_en).toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' });
            const boton = crearBoton('Recuperar', () => restaurarAlarma(a), 'btn-neutro-alarma',
                                     'Recuperar la alarma ' + nombreConDosis(a));
            listaEliminadas.append(crearItemAlarma(a.hora + ' · ' + nombreConDosis(a) + ' (eliminada el ' + cuando + ')', boton));
        }
    } catch (error) {
        Errores.registrar('cargar las alarmas eliminadas', error);
    }
}

// ===================================================================
// CREAR ALARMA
// ===================================================================
function prepararCampoFecha() { inputFecha.min = fechaActual(); inputFecha.value = fechaActual(); }

selectRepeticion.addEventListener('change', () => {
    fieldsetDias.hidden = selectRepeticion.value !== 'personalizada';
});

function datosRepeticion() {
    const opcion = selectRepeticion.value;
    if (opcion === 'una') return { repeticion: 'una' };
    if (opcion === 'diaria') return { repeticion: 'diaria' };
    if (opcion === 'laborables') return { repeticion: 'dias', dias: [0, 1, 2, 3, 4] };
    if (opcion === 'finde') return { repeticion: 'dias', dias: [5, 6] };
    const dias = [...fieldsetDias.querySelectorAll('input[name="dia"]:checked')].map(c => Number(c.value));
    return { repeticion: 'dias', dias: dias };
}

formAlarma.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    const momento = new Date(inputFecha.value + 'T' + inputHora.value + ':00');
    if (isNaN(momento) || momento.getTime() <= Date.now()) {
        mostrarMensajeAlarma('Esa fecha y hora ya han pasado.', true);
        return;
    }
    const repeticion = datosRepeticion();
    if (repeticion.repeticion === 'dias' && repeticion.dias.length === 0) {
        mostrarMensajeAlarma('Marca al menos un día de la semana.', true);
        return;
    }
    // El cuerpo se prepara FUERA del try de red (3.18.1)
    const cuerpo = {
        titulo: inputTitulo.value.trim(),
        dosis: inputDosis.value.trim(),
        fecha: inputFecha.value,
        hora: inputHora.value,
        ...repeticion
    };
    try {
        const respuesta = await pedir('/api/alarmas', { metodo: 'POST', cuerpo });
        const datos = await respuesta.json();
        mostrarMensajeAlarma('Alarma creada. Sonará el ' + fechaLegible(datos.alarma.fecha) + ' a las ' + datos.alarma.hora + '.', false);
        formAlarma.reset();
        fieldsetDias.hidden = true;     // reset() vuelve a "Solo una vez"
        prepararCampoFecha();
        await cargarAlarmas();
    } catch (error) {
        mostrarMensajeAlarma(textoDeError(error, 'crear la alarma'), true);
    }
});

// ===================================================================
// ARRANQUE
// ===================================================================
prepararCampoFecha();
mantenerPantallaEncendida();
cargarAlarmas();
cargarEliminadas();
setInterval(cargarAlarmas, INTERVALO_RECARGA_MS);
cargarTomasPendientes().finally(() => setInterval(comprobarAlarmas, INTERVALO_COMPROBACION_MS));
