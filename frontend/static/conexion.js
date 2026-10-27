const botonSOS = document.getElementById('boton-sos');

// PARTE 1: BOTON SOS
botonSOS.addEventListener('click', async () => {
    botonSOS.disabled = true;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    try {
        const respuesta = await fetch('/api/sos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}), 
            signal: controller.signal
        });
        if (!respuesta.ok) throw new Error('Error del servidor');
        alert('Aviso enviado. Tu supervisor ha sido notificado.');
    } catch (error) {
        alert('Error de conexión: LLAME AL 112');
    } finally {
        clearTimeout(timeoutId);
        botonSOS.disabled = false;
    }
});

// PARTE 2: ALARMAS
const INTERVALO_COMPROBACION_MS = 1000;   
const INTERVALO_RECARGA_MS = 30000;       
const TIMEOUT_ALARMAS_MS = 2500;          

const sonidoAlarma = new Audio('/static/alarma.mp3');
sonidoAlarma.loop = true;                 

const avisoAlarma = document.getElementById('aviso-alarma');
const textoAlarma = document.getElementById('texto-alarma');
const btnEntendido = document.getElementById('btn-alarma-entendida');
const btnPosponer = document.getElementById('btn-alarma-posponer');
const avisoSonidoAlarma = document.getElementById('aviso-sonido-alarma');
const btnSonidoAlarma = document.getElementById('btn-activar-sonido-alarma');
const estadoSistema = document.querySelector('.estado-sistema');
const puntoEstado = document.getElementById('punto-estado');
const textoEstado = document.getElementById('texto-estado');

function marcarConexion(ok) {
    estadoSistema.classList.toggle('sin-conexion', !ok);
    puntoEstado.classList.remove('gris');
    puntoEstado.classList.toggle('verde', ok);
    puntoEstado.classList.toggle('rojo', !ok);
    textoEstado.textContent = ok ? 'Sistema activo' : 'Sin conexión con el servidor';
}

let alarmas = [];                          
let alarmasInactivas = [];                 
let alarmasCargadasUnaVez = false;         
const yaDisparadas = new Set();
let avisosEnPantalla = [];                 
const POSPONER_MS = 10 * 60 * 1000;        

function horaActual() {
    const ahora = new Date();
    const hh = String(ahora.getHours()).padStart(2, '0');
    const mm = String(ahora.getMinutes()).padStart(2, '0');
    return hh + ':' + mm;
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

async function cargarAlarmas() {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_ALARMAS_MS);
    try {
        const respuesta = await fetch('/api/mis-alarmas?todas=1', { signal: controller.signal });
        if (!respuesta.ok) throw new Error('HTTP ' + respuesta.status);
        const todas = await respuesta.json();
        alarmas = todas.filter(a => a.activa);
        alarmasInactivas = todas.filter(a => !a.activa);
        alarmasCargadasUnaVez = true;
        marcarConexion(true);
        mostrarListaAlarmas();
    } catch (error) {
        console.error('No se pudieron cargar las alarmas', error);
        marcarConexion(false);
        if (!alarmasCargadasUnaVez) {
            listaAlarmas.replaceChildren(crearItemVacio('No se pudieron cargar tus alarmas. Reintentando…'));
        }
    } finally {
        clearTimeout(timeoutId);
    }
}

async function desactivarAlarma(id) {
    try {
        const r = await fetch('/api/alarmas/' + id + '/estado', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ activa: false })
        });
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return true;
    } catch (error) {
        mostrarMensajeAlarma('No se pudo quitar la alarma.', true);
        return false;
    }
}

async function registrarSonada(alarma, fechaLocal, horaLocal, aviso, intento = 1) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_ALARMAS_MS * 2);
    try {
        const r = await fetch('/api/alarmas/' + alarma.id + '/sonada', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                fecha_local: fechaLocal,
                hora_local: horaLocal,
                fecha_prevista: alarma.fecha
            }),
            signal: controller.signal
        });
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const datos = await r.json();
        aviso.registroId = datos.registro_id;
        if (aviso.confirmarAlLlegar) confirmarToma(aviso.registroId);
        await cargarAlarmas();
    } catch (error) {
        if (intento < 10) setTimeout(() => registrarSonada(alarma, fechaLocal, horaLocal, aviso, intento + 1), 5000 * intento);
    } finally {
        clearTimeout(timeoutId);
    }
}

async function confirmarToma(registroId) {
    try {
        const r = await fetch('/api/tomas/' + registroId + '/confirmar', { method: 'POST' });
        if (!r.ok) throw new Error('HTTP ' + r.status);
    } catch (error) {}
}

async function cargarTomasPendientes() {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_ALARMAS_MS);
    try {
        const r = await fetch('/api/mis-tomas-pendientes', { signal: controller.signal });
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const tomas = await r.json();
        for (const t of tomas) {
            const cuando = (t.fecha_prevista === fechaActual() ? '' : fechaLegible(t.fecha_prevista) + ' ') + t.hora_prevista;
            mostrarAviso({
                texto: t.titulo + ' (pendiente: era a las ' + cuando + ')',
                registroId: t.toma_id,
                confirmarAlLlegar: false
            });
        }
    } catch (error) {} finally {
        clearTimeout(timeoutId);
    }
}

async function reactivarAlarma(alarma) {
    try {
        const respuesta = await fetch('/api/alarmas/' + alarma.id + '/estado', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ activa: true, fecha: proximaFecha(alarma.hora) })
        });
        if (!respuesta.ok) throw new Error('HTTP ' + respuesta.status);
    } catch (error) {}
    await cargarAlarmas();
}

function mostrarAviso(aviso) {
    avisosEnPantalla.push(aviso);
    textoAlarma.textContent = avisosEnPantalla.map(a => a.texto).join(' · ');
    avisoAlarma.hidden = false;
    sonidoAlarma.play().then(() => { avisoSonidoAlarma.hidden = true; }).catch(() => { avisoSonidoAlarma.hidden = false; });
    if (navigator.vibrate) navigator.vibrate([500, 300, 500]);
}

function detenerAviso() {
    sonidoAlarma.pause();
    sonidoAlarma.currentTime = 0;
    if (navigator.vibrate) navigator.vibrate(0);
    avisoAlarma.hidden = true;
}

function dispararAlarma(alarma, retrasoMin) {
    let texto = alarma.titulo;
    if (retrasoMin >= 2) texto += ' (perdida: era el ' + fechaLegible(alarma.fecha) + ' a las ' + alarma.hora + ')';
    const aviso = { texto: texto, registroId: null, confirmarAlLlegar: false };
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

btnEntendido.addEventListener('click', () => {
    for (const aviso of avisosEnPantalla) {
        if (aviso.registroId) confirmarToma(aviso.registroId);
        else aviso.confirmarAlLlegar = true;   
    }
    avisosEnPantalla = [];
    detenerAviso();
});

btnPosponer.addEventListener('click', () => {
    const pospuestos = avisosEnPantalla;
    avisosEnPantalla = [];
    detenerAviso();
    setTimeout(() => pospuestos.forEach(mostrarAviso), POSPONER_MS);
});

btnSonidoAlarma.addEventListener('click', async () => {
    try {
        await sonidoAlarma.play();     
        if (avisoAlarma.hidden) { sonidoAlarma.pause(); sonidoAlarma.currentTime = 0; }
        avisoSonidoAlarma.hidden = true;
    } catch (error) {}
});

cargarAlarmas();
setInterval(cargarAlarmas, INTERVALO_RECARGA_MS);
cargarTomasPendientes().finally(() => setInterval(comprobarAlarmas, INTERVALO_COMPROBACION_MS));

const formAlarma = document.getElementById('form-alarma');
const inputTitulo = document.getElementById('alarma-titulo');
const inputDosis = document.getElementById('alarma-dosis');   // NUEVO: campo de dosis
const inputFecha = document.getElementById('alarma-fecha');
const inputHora = document.getElementById('alarma-hora');
const inputRepetitiva = document.getElementById('alarma-repetitiva');
const mensajeAlarma = document.getElementById('mensaje-alarma');
const listaAlarmas = document.getElementById('lista-alarmas');
const listaInactivas = document.getElementById('lista-inactivas');

function prepararCampoFecha() { inputFecha.min = fechaActual(); inputFecha.value = fechaActual(); }
prepararCampoFecha();

function mostrarMensajeAlarma(texto, esError) {
    mensajeAlarma.textContent = texto;
    mensajeAlarma.className = 'mensaje-alarma ' + (esError ? 'error' : 'ok');
}

function mostrarListaAlarmas() {
    listaAlarmas.replaceChildren();   
    if (alarmas.length === 0) listaAlarmas.append(crearItemVacio('No tienes alarmas activas.'));
    const ordenadas = [...alarmas].sort((a, b) => ((a.fecha || '') + a.hora).localeCompare((b.fecha || '') + b.hora));
    for (const alarma of ordenadas) {
        const textoAlarma = (alarma.fecha ? fechaLegible(alarma.fecha) + ' ' : '') + alarma.hora + ' · ' + alarma.titulo + (alarma.dosis ? ' (' + alarma.dosis + ')' : '') + (alarma.es_repetitiva ? ' (cada día)' : '');
        const btnQuitar = crearBoton('Quitar', async () => { await desactivarAlarma(alarma.id); await cargarAlarmas(); });
        listaAlarmas.append(crearItemAlarma(textoAlarma, btnQuitar));
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
        const textoAlarma = alarma.hora + ' · ' + alarma.titulo + (alarma.dosis ? ' (' + alarma.dosis + ')' : '') + ' (' + estado + ')';
        const btnReactivar = crearBoton('Reactivar', () => reactivarAlarma(alarma));
        listaInactivas.append(crearItemAlarma(textoAlarma, btnReactivar));
    }
}

function crearItemVacio(mensaje) {
    const vacio = document.createElement('li');
    vacio.className = 'lista-vacia';
    vacio.textContent = mensaje;
    return vacio;
}
function crearItemAlarma(textoAlarma, boton) {
    const li = document.createElement('li');
    const texto = document.createElement('span');
    texto.textContent = textoAlarma;
    li.append(texto, boton);
    return li;
}
function crearBoton(etiqueta, alHacerClic) {
    const boton = document.createElement('button');
    boton.type = 'button';
    boton.className = 'btn-quitar-alarma';   
    boton.textContent = etiqueta;
    boton.addEventListener('click', alHacerClic);
    return boton;
}

formAlarma.addEventListener('submit', async (evento) => {
    evento.preventDefault();   
    const momento = new Date(inputFecha.value + 'T' + inputHora.value + ':00');
    if (isNaN(momento) || momento.getTime() <= Date.now()) {
        mostrarMensajeAlarma('Esa fecha y hora ya han pasado.', true);
        return;
    }
    try {
        const respuesta = await fetch('/api/alarmas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                titulo: inputTitulo.value.trim(),
                dosis: inputDosis.value.trim(),
                fecha: inputFecha.value,               
                hora: inputHora.value,                 
                es_repetitiva: inputRepetitiva.checked
            })
        });
        const datos = await respuesta.json();
        if (!respuesta.ok) {
            mostrarMensajeAlarma(datos.error || 'No se pudo crear la alarma', true);
            return;
        }
        mostrarMensajeAlarma('Alarma creada para el ' + fechaLegible(inputFecha.value) + ' a las ' + inputHora.value, false);
        formAlarma.reset();       
        prepararCampoFecha();     
        await cargarAlarmas();    
    } catch (error) {
        mostrarMensajeAlarma('Error de conexión: no se pudo crear la alarma', true);
    }
});