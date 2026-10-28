const USER_ID = 2;  // provisional hasta que haya login
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
            body: JSON.stringify({ user_id: USER_ID }),
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
const INTERVALO_COMPROBACION_MS = 1000;   // mirar el reloj cada segundo => error máximo ~1 s
const INTERVALO_RECARGA_MS = 30000;       // volver a pedir las alarmas al servidor cada 30 s
const TIMEOUT_ALARMAS_MS = 2500;          // si el servidor no responde, no esperamos indefinidamente

const sonidoAlarma = new Audio('/static/alarma.mp3');
sonidoAlarma.loop = true;                 // suena en bucle hasta que el paciente pulse "Entendido"

const avisoAlarma = document.getElementById('aviso-alarma');
const textoAlarma = document.getElementById('texto-alarma');
const btnEntendido = document.getElementById('btn-alarma-entendida');
const btnPosponer = document.getElementById('btn-alarma-posponer');
const avisoSonidoAlarma = document.getElementById('aviso-sonido-alarma');
const btnSonidoAlarma = document.getElementById('btn-activar-sonido-alarma');
const estadoSistema = document.querySelector('.estado-sistema');
const puntoEstado = document.getElementById('punto-estado');
const textoEstado = document.getElementById('texto-estado');

// Pinta el indicador de conexión según el resultado de hablar con el servidor
function marcarConexion(ok) {
    estadoSistema.classList.toggle('sin-conexion', !ok);
    puntoEstado.classList.remove('gris');
    puntoEstado.classList.toggle('verde', ok);
    puntoEstado.classList.toggle('rojo', !ok);
    textoEstado.textContent = ok ? 'Sistema activo' : 'Sin conexión con el servidor';
}

let alarmas = [];                          // alarmas ACTIVAS: última lista conocida (si falla la red, seguimos con ella)
let alarmasInactivas = [];                 // desactivadas o de un solo uso que ya sonaron (solo para enseñarlas en la lista)
let alarmasCargadasUnaVez = false;         // para distinguir "no tengo alarmas" de "no pude cargarlas"
// Claves "id|fecha|hora" que ya han sonado en ESTA sesión. Es solo un freno de seguridad para no repetir el aviso
// mientras el servidor confirma; lo que de verdad recuerda "ya sonó" (aunque cierres la app) es la base de datos.
const yaDisparadas = new Set();
let avisosEnPantalla = [];                 // avisos que suenan ahora: { texto, registroId, confirmarAlLlegar }
const POSPONER_MS = 10 * 60 * 1000;        // 10 minutos

// --- Utilidades de tiempo --------------------------------------------------

// Devuelve la hora local actual con el MISMO formato que guarda la BD ("08:05")
function horaActual() {
    const ahora = new Date();
    const hh = String(ahora.getHours()).padStart(2, '0'); // padStart/(2,'0') añade el cero inicial si falta
    const mm = String(ahora.getMinutes()).padStart(2, '0');
    return hh + ':' + mm;
}

// Convierte un Date en texto "2026-10-17" usando la fecha LOCAL (toISOString daría la UTC y podría salir otro día)
function formatearFecha(d) {
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' +
           String(d.getDate()).padStart(2, '0');
}

// Fecha local de hoy en formato "2026-10-17"
function fechaActual() {
    return formatearFecha(new Date());
}

// "2026-10-17" -> "17/10/2026" (para enseñarla al paciente)
function fechaLegible(fecha) {
    return fecha.split('-').reverse().join('/');
}

// Momento exacto (objeto Date) en que debe sonar una alarma.
// Un texto "2026-10-17T08:30:00" SIN zona horaria el navegador lo interpreta como hora local.
function momentoAlarma(alarma) {
    return new Date(alarma.fecha + 'T' + alarma.hora + ':00');
}

// Próxima fecha en la que llegará una hora "HH:MM": hoy si todavía no ha llegado, si no mañana.
function proximaFecha(hora) {
    const d = new Date();
    if (hora <= horaActual()) d.setDate(d.getDate() + 1);
    return formatearFecha(d);
}

// --- Comunicación con el servidor -----------------------------------------

// Descarga las alarmas activas. Si falla (sin red, servidor caído), NO vaciamos la lista:
// así una alarma ya cargada sigue sonando aunque se pierda la conexión.
async function cargarAlarmas() {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_ALARMAS_MS);
    try {
        const respuesta = await fetch('/api/usuarios/' + USER_ID + '/alarmas?todas=1',
                                      { signal: controller.signal });
        if (!respuesta.ok) throw new Error('HTTP ' + respuesta.status);
        const todas = await respuesta.json();
        alarmas = todas.filter(a => a.activa);
        alarmasInactivas = todas.filter(a => !a.activa);
        alarmasCargadasUnaVez = true;
        marcarConexion(true);
        mostrarListaAlarmas();
    } catch (error) {
        console.error('No se pudieron cargar las alarmas (se usa la última lista)', error);
        marcarConexion(false);
        // Si nunca se cargaron, las listas saldrían vacías y parecería que no hay alarmas
        if (!alarmasCargadasUnaVez) {
            listaAlarmas.replaceChildren(crearItemVacio('No se pudieron cargar tus alarmas. Reintentando…'));
        }
    } finally {
        clearTimeout(timeoutId);
    }
}

// Desactiva en el servidor una alarma no repetitiva ya disparada.
// Reutiliza la ruta PATCH /api/alarmas/<id>/estado que ya existía.
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
        console.error('No se pudo desactivar la alarma', id, error);
        mostrarMensajeAlarma('No se pudo quitar la alarma. Inténtalo de nuevo.', true);
        return false;
    }
}

// Avisa al servidor de que una alarma acaba de sonar, para que lo GUARDE en la base de datos.
// El servidor decide qué pasa después: si es repetitiva pasa a la fecha siguiente; si no, se desactiva.
// Avisa al servidor de que la alarma sonó. Él crea el registro de toma y nos devuelve su id.
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
                fecha_prevista: alarma.fecha      // la fecha que tenía la alarma al sonar
            }),
            signal: controller.signal
        });
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const datos = await r.json();

        aviso.registroId = datos.registro_id;
        // Si la paciente ya pulsó "Ya lo hice" antes de que llegara la respuesta, confirmamos ahora
        if (aviso.confirmarAlLlegar) confirmarToma(aviso.registroId);
        await cargarAlarmas();
        cargarAgenda();   // la alarma sonó, así que la agenda de hoy puede cambiar (riesgo 3.3.3)
    } catch (error) {
        if (intento < 10) {
            setTimeout(() => registrarSonada(alarma, fechaLocal, horaLocal, aviso, intento + 1),
                       5000 * intento);
        }
    } finally {
        clearTimeout(timeoutId);
    }
}

// Marca la toma como confirmada en el servidor
async function confirmarToma(registroId) {
    try {
        const r = await fetch('/api/tomas/' + registroId + '/confirmar', { method: 'POST' });
        if (!r.ok) throw new Error('HTTP ' + r.status);
        cargarAgenda();
    } catch (error) {
        console.error('No se pudo confirmar la toma', registroId, error);
    }
}

// Al abrir la página: recupera las tomas que quedaron sin confirmar (por ejemplo, tras recargar)
async function cargarTomasPendientes() {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_ALARMAS_MS);
    try {
        const r = await fetch('/api/usuarios/' + USER_ID + '/tomas-pendientes',
                              { signal: controller.signal });
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
    } catch (error) {
        console.error('No se pudieron cargar las tomas pendientes', error);
    } finally {
        clearTimeout(timeoutId);
    }
}

// Vuelve a activar una alarma desactivada (o de un solo uso que ya sonó) para su próxima ocasión.
async function reactivarAlarma(alarma) {
    try {
        const respuesta = await fetch('/api/alarmas/' + alarma.id + '/estado', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ activa: true, fecha: proximaFecha(alarma.hora) })
        });
        if (!respuesta.ok) throw new Error('HTTP ' + respuesta.status);
    } catch (error) {
        console.error('No se pudo reactivar la alarma', alarma.id, error);
    }
    await cargarAlarmas();
}

// --- Aviso al paciente ------------------------------------------------------

// Muestra el aviso y hace sonar la alarma.
// retrasoMin = minutos que han pasado desde su hora. Si es 2 o más, la app estaba cerrada y la alarma se perdió.
// Pinta el aviso (puede haber varios a la vez) y hace sonar la alarma
function mostrarAviso(aviso) {
    avisosEnPantalla.push(aviso);
    textoAlarma.textContent = avisosEnPantalla.map(a => a.texto).join(' · ');
    avisoAlarma.hidden = false;

    sonidoAlarma.play()
        .then(() => { avisoSonidoAlarma.hidden = true; })
        .catch(() => { avisoSonidoAlarma.hidden = false; });

    if (navigator.vibrate) navigator.vibrate([500, 300, 500]);
}

// Oculta el aviso y para el sonido
function detenerAviso() {
    sonidoAlarma.pause();
    sonidoAlarma.currentTime = 0;
    if (navigator.vibrate) navigator.vibrate(0);
    avisoAlarma.hidden = true;
}

// retrasoMin = minutos desde su hora. Si es 2 o más, la alarma se perdió. Devuelve el aviso creado.
function dispararAlarma(alarma, retrasoMin) {
    let texto = alarma.titulo;
    if (retrasoMin >= 2) {
        texto += ' (perdida: era el ' + fechaLegible(alarma.fecha) + ' a las ' + alarma.hora + ')';
    }
    const aviso = { texto: texto, registroId: null, confirmarAlLlegar: false };
    mostrarAviso(aviso);
    return aviso;
}

// Comprueba si alguna alarma toca AHORA. Se ejecuta cada segundo.
function comprobarAlarmas() {
    const ahoraMs = Date.now();

    for (const alarma of alarmas) {
        if (!alarma.fecha) continue;                    // alarma antigua sin fecha (la migración se la pone)

        const momento = momentoAlarma(alarma);          // fecha + hora exactas en que debe sonar
        if (isNaN(momento)) continue;                   // fecha/hora con formato raro: la ignoramos
        if (momento.getTime() > ahoraMs) continue;      // todavía no toca

        // Suena TODA alarma cuyo momento ya ha llegado y que el servidor aún no ha marcado como sonada.
        // La clave lleva la fecha guardada: una repetitiva vuelve a sonar mañana, pero no 60 veces en el mismo minuto.
        const clave = alarma.id + '|' + alarma.fecha + '|' + alarma.hora;
        if (yaDisparadas.has(clave)) continue;
        yaDisparadas.add(clave);

        const retrasoMin = Math.floor((ahoraMs - momento.getTime()) / 60000);

        // Lo guardamos en la base de datos. El servidor mueve la repetitiva a su siguiente fecha o
        // desactiva la de un solo uso, y al recargar la lista desaparece de las pendientes.
        const aviso = dispararAlarma(alarma, retrasoMin);
        registrarSonada(alarma, fechaActual(), horaActual(), aviso);
    }
}

// --- Botones ------------------------------------------------------------

// "Entendido": el paciente confirma que ha visto el aviso y paramos el sonido.
// "Ya lo hice": confirma las tomas y para el sonido
btnEntendido.addEventListener('click', () => {
    for (const aviso of avisosEnPantalla) {
        if (aviso.registroId) confirmarToma(aviso.registroId);
        else aviso.confirmarAlLlegar = true;   // el servidor aún no ha respondido: se confirma al llegar
    }
    avisosEnPantalla = [];
    detenerAviso();
});

// "Posponer": para el sonido y vuelve a avisar en 10 minutos con los mismos avisos
btnPosponer.addEventListener('click', () => {
    const pospuestos = avisosEnPantalla;
    avisosEnPantalla = [];
    detenerAviso();
    setTimeout(() => pospuestos.forEach(mostrarAviso), POSPONER_MS);
});

// El clic en este botón es la "interacción del usuario" que desbloquea el audio del navegador.
btnSonidoAlarma.addEventListener('click', async () => {
    try {
        await sonidoAlarma.play();     // primera reproducción permitida por el clic
        // Si no hay ningún aviso en pantalla, paramos: solo queríamos desbloquear el audio.
        if (avisoAlarma.hidden) {
            sonidoAlarma.pause();
            sonidoAlarma.currentTime = 0;
        }
        avisoSonidoAlarma.hidden = true;
    } catch (error) {
        console.warn('No se pudo activar el sonido', error);
    }
});

// --- Arranque ------------------------------------------------------------

cargarAlarmas();
setInterval(cargarAlarmas, INTERVALO_RECARGA_MS);
// Primero mostramos las tomas pendientes y luego empezamos a vigilar la hora (evita avisos duplicados)
cargarTomasPendientes().finally(() => setInterval(comprobarAlarmas, INTERVALO_COMPROBACION_MS));

// PARTE 3: PANTALLA PARA CREAR Y VER ALARMAS
const formAlarma = document.getElementById('form-alarma');
const inputTitulo = document.getElementById('alarma-titulo');
const inputFecha = document.getElementById('alarma-fecha');
const inputHora = document.getElementById('alarma-hora');
const inputRepetitiva = document.getElementById('alarma-repetitiva');
const mensajeAlarma = document.getElementById('mensaje-alarma');
const listaAlarmas = document.getElementById('lista-alarmas');
const listaInactivas = document.getElementById('lista-inactivas');

// El campo de fecha empieza en hoy y no deja elegir días anteriores.
function prepararCampoFecha() {
    inputFecha.min = fechaActual();
    inputFecha.value = fechaActual();
}
prepararCampoFecha();
// Muestra un mensaje bajo el formulario. esError cambia el color (rojo/verde) con una clase CSS.
function mostrarMensajeAlarma(texto, esError) {
    mensajeAlarma.textContent = texto;
    mensajeAlarma.className = 'mensaje-alarma ' + (esError ? 'error' : 'ok');
}

// Dibuja la lista de alarmas activas a partir de la variable global "alarmas" (PARTE 2).
// Se usa createElement + textContent (y no innerHTML) para que un título con
// caracteres raros no pueda inyectar HTML en la página.
function mostrarListaAlarmas() {
    // --- Alarmas activas (las que todavía van a sonar) ---
    listaAlarmas.replaceChildren();   // vaciamos la lista antes de redibujarla

    if (alarmas.length === 0) {
        listaAlarmas.append(crearItemVacio('No tienes alarmas activas.'));
    }

    // Ordenadas por fecha y hora
    const ordenadas = [...alarmas].sort((a, b) =>
        ((a.fecha || '') + a.hora).localeCompare((b.fecha || '') + b.hora));

    for (const alarma of ordenadas) {
        const textoAlarma = (alarma.fecha ? fechaLegible(alarma.fecha) + ' ' : '') +
                            alarma.hora + ' · ' + alarma.titulo +
                            (alarma.es_repetitiva ? ' (cada día)' : '');

        const btnQuitar = crearBoton('Quitar', async () => {
            await desactivarAlarma(alarma.id);   // PATCH activa=false
            await cargarAlarmas();               // recargamos para que pase a la otra lista
        });
        listaAlarmas.append(crearItemAlarma(textoAlarma, btnQuitar));
    }

    // --- Alarmas que ya sonaron o están desactivadas (se guardan en la BD) ---
    listaInactivas.replaceChildren();

    if (alarmasInactivas.length === 0) {
        listaInactivas.append(crearItemVacio('Todavía no hay alarmas desactivadas ni que hayan sonado.'));
        return;
    }

    // Las más recientes primero, y solo las 10 últimas para que la lista no crezca sin límite
    const recientes = [...alarmasInactivas].sort((a, b) =>
        ((b.fecha || '') + b.hora).localeCompare((a.fecha || '') + a.hora)).slice(0, 10);

    for (const alarma of recientes) {
        let estado = 'desactivada';
        if (alarma.ultima_vez_sono) {
            estado = 'sonó el ' + new Date(alarma.ultima_vez_sono)
                .toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' });
        }
        const textoAlarma = alarma.hora + ' · ' + alarma.titulo + ' (' + estado + ')';

        const btnReactivar = crearBoton('Reactivar', () => reactivarAlarma(alarma));
        listaInactivas.append(crearItemAlarma(textoAlarma, btnReactivar));
    }
}

// --- Pequeñas ayudas para dibujar las listas (siempre textContent, nunca innerHTML) ---

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
    boton.className = 'btn-quitar-alarma';   // reutiliza el estilo de "Quitar"
    boton.textContent = etiqueta;
    boton.addEventListener('click', alHacerClic);
    return boton;
}

// Envío del formulario: crea la alarma en el servidor.
// Envío del formulario: crea la alarma en el servidor.
formAlarma.addEventListener('submit', async (evento) => {
    evento.preventDefault();   // evita que el navegador recargue la página al enviar

    // Comprobamos aquí que no sea un momento ya pasado.
    const momento = new Date(inputFecha.value + 'T' + inputHora.value + ':00');
    if (isNaN(momento) || momento.getTime() <= Date.now()) {
        mostrarMensajeAlarma('Esa fecha y hora ya han pasado. Elige un momento futuro.', true);
        return;
    }

       try {
        const respuesta = await fetch('/api/alarmas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: USER_ID,
                titulo: inputTitulo.value.trim(),
                fecha: inputFecha.value,               // "AAAA-MM-DD" gracias a type="date"
                hora: inputHora.value,                 // "HH:MM" gracias a type="time"
                es_repetitiva: inputRepetitiva.checked
            })
        });

        if (!respuesta.ok) {
            let cuerpoError = {};
            try { cuerpoError = await respuesta.json(); } catch (e) {}
            if (respuesta.status >= 500) {
                // Riesgo 3.11.3: fallo del servidor al guardar
                mostrarMensajeAlarma('Tu alarma NO se ha guardado. Vuelve a configurarla.', true);
            } else {
                mostrarMensajeAlarma(cuerpoError.error || 'No se pudo crear la alarma', true);
            }
            return;
        }

        mostrarMensajeAlarma('Alarma creada para el ' + fechaLegible(inputFecha.value) +
                             ' a las ' + inputHora.value, false);
        formAlarma.reset();       // vaciamos el formulario para poder crear otra
        prepararCampoFecha();     // reset() deja la fecha vacía: volvemos a poner hoy
        await cargarAlarmas();    // actualiza la lista y la comprobación de horas
    } catch (error) {
        console.error('No se pudo reactivar la alarma', alarma.id, error);
        mostrarMensajeAlarma('Error de conexión: tu alarma NO se ha guardado. Vuelve a configurarla.', true);
    }
});

// PARTE 4: LATIDO DE CONEXIÓN + MÉTRICAS DIARIAS
async function enviarLatido() {
    try {
        await fetch('/api/usuarios/' + USER_ID + '/latido', { method: 'POST' });
    } catch (error) {
        console.warn('No se pudo enviar el latido', error);
    }
}
enviarLatido();
setInterval(enviarLatido, 30000);

// Solo se activa si existe el formulario en paciente.html (ver abajo)
const formMetrica = document.getElementById('form-metrica');
if (formMetrica) {
    const inputSueno = document.getElementById('metrica-sueno');
    const selectAnimo = document.getElementById('metrica-animo');
    const mensajeMetrica = document.getElementById('mensaje-metrica');

    formMetrica.addEventListener('submit', async (evento) => {
        evento.preventDefault();
        const cuerpo = { user_id: USER_ID };
        if (inputSueno.value !== '') cuerpo.horas_sueno = inputSueno.value;
        if (selectAnimo.value) cuerpo.estado_animo = selectAnimo.value;
        try {
            const r = await fetch('/api/metricas', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(cuerpo)
            });
            const datos = await r.json();
            mensajeMetrica.textContent = r.ok ? 'Guardado. ¡Gracias!' : (datos.error || 'No se pudo guardar');
            mensajeMetrica.className = 'mensaje-alarma ' + (r.ok ? 'ok' : 'error');
        } catch (error) {
            mensajeMetrica.textContent = 'Error de conexión';
            mensajeMetrica.className = 'mensaje-alarma error';
        }
    });
}

// PARTE 4: LISTA DE HOY (riesgo 3.3.3)
// Si el cronómetro de alarmas fallara, la paciente puede consultar aquí qué le toca hoy.
// Se guarda la última lista en el navegador para que se vea aunque se pierda la conexión.
const listaHoy = document.getElementById('lista-hoy');
const CLAVE_AGENDA = 'agenda-hoy-' + USER_ID;
const INTERVALO_AGENDA_MS = 30000;
const ETIQUETAS_AGENDA = { PROGRAMADA: 'por llegar', PENDIENTE: 'sin confirmar', CONFIRMADA: 'hecho ✓' };

function pintarAgenda(agenda, desactualizada) {
    if (!listaHoy) return;
    listaHoy.replaceChildren();
    if (agenda.length === 0) {
        listaHoy.append(crearItemVacio('Hoy no tienes recordatorios.'));
    }
    for (const e of agenda) {
        const li = document.createElement('li');
        li.className = 'agenda-' + e.estado.toLowerCase();
        li.textContent = e.hora + ' · ' + e.titulo + ' (' + (ETIQUETAS_AGENDA[e.estado] || e.estado) + ')';
        listaHoy.append(li);
    }
    if (desactualizada) {
        listaHoy.append(crearItemVacio('Sin conexión: se muestra la última lista guardada.'));
    }
}

async function cargarAgenda() {
    if (!listaHoy) return;
    const hoy = fechaActual();
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_ALARMAS_MS);
    try {
        const r = await fetch('/api/usuarios/' + USER_ID + '/agenda-hoy?fecha=' + hoy,
                              { signal: controller.signal });
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const agenda = await r.json();
        try { localStorage.setItem(CLAVE_AGENDA, JSON.stringify({ fecha: hoy, agenda: agenda })); } catch (e) {}
        pintarAgenda(agenda, false);
    } catch (error) {
        console.error('No se pudo cargar la lista de hoy', error);
        let guardada = null;
        try { guardada = JSON.parse(localStorage.getItem(CLAVE_AGENDA)); } catch (e) {}
        if (guardada && guardada.fecha === hoy) {
            pintarAgenda(guardada.agenda, true);
        } else {
            listaHoy.replaceChildren(crearItemVacio('No se pudo cargar tu lista de hoy. Reintentando…'));
        }
    } finally {
        clearTimeout(timeoutId);
    }
}

cargarAgenda();
setInterval(cargarAgenda, INTERVALO_AGENDA_MS);