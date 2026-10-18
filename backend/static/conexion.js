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
const avisoSonidoAlarma = document.getElementById('aviso-sonido-alarma');
const btnSonidoAlarma = document.getElementById('btn-activar-sonido-alarma');

let alarmas = [];                          // alarmas ACTIVAS: última lista conocida (si falla la red, seguimos con ella)
let alarmasInactivas = [];                 // desactivadas o de un solo uso que ya sonaron (solo para enseñarlas en la lista)
// Claves "id|fecha|hora" que ya han sonado en ESTA sesión. Es solo un freno de seguridad para no repetir el aviso
// mientras el servidor confirma; lo que de verdad recuerda "ya sonó" (aunque cierres la app) es la base de datos.
const yaDisparadas = new Set();
let titulosEnPantalla = [];                // alarmas que están sonando ahora mismo (puede haber varias a la vez)

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
        // ?todas=1: el servidor devuelve también las desactivadas, para poder verlas y reactivarlas
        const respuesta = await fetch('/api/usuarios/' + USER_ID + '/alarmas?todas=1',
                                      { signal: controller.signal });
        if (!respuesta.ok) throw new Error('HTTP ' + respuesta.status);
        const todas = await respuesta.json();
        alarmas = todas.filter(a => a.activa);              // solo estas pueden sonar
        alarmasInactivas = todas.filter(a => !a.activa);
        mostrarListaAlarmas();   // refresca las listas visibles
    } catch (error) {
        console.error('No se pudieron cargar las alarmas (se usa la última lista)', error);
    } finally {
        clearTimeout(timeoutId);
    }
}

// Desactiva en el servidor una alarma no repetitiva ya disparada.
// Reutiliza la ruta PATCH /api/alarmas/<id>/estado que ya existía.
async function desactivarAlarma(id) {
    try {
        await fetch('/api/alarmas/' + id + '/estado', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ activa: false })
        });
    } catch (error) {
        console.error('No se pudo desactivar la alarma', id, error);
    }
}

// Avisa al servidor de que una alarma acaba de sonar, para que lo GUARDE en la base de datos.
// El servidor decide qué pasa después: si es repetitiva pasa a la fecha siguiente; si no, se desactiva.
async function registrarSonada(alarma) {
    try {
        const respuesta = await fetch('/api/alarmas/' + alarma.id + '/sonada', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fecha_local: fechaActual(), hora_local: horaActual() })
        });
        if (!respuesta.ok) throw new Error('HTTP ' + respuesta.status);
        await cargarAlarmas();   // recargamos para tener la nueva fecha / el nuevo estado
    } catch (error) {
        // Si falla, la alarma sigue "pendiente" en la BD: al reabrir la app volverá a avisar.
        console.error('No se pudo registrar que la alarma sonó', alarma.id, error);
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
function dispararAlarma(alarma, retrasoMin) {
    let texto = alarma.titulo;
    if (retrasoMin >= 2) {
        texto += ' (perdida: era el ' + fechaLegible(alarma.fecha) + ' a las ' + alarma.hora + ')';
    }
    titulosEnPantalla.push(texto);
    // textContent (y no innerHTML) para que un título con caracteres raros no inyecte HTML.
    textoAlarma.textContent = titulosEnPantalla.join(' · ');
    avisoAlarma.hidden = false;

    // Los navegadores bloquean el audio hasta que el usuario interactúa con la página.
    // Si falla, mostramos el botón de "activar sonido"; el aviso visual se ve igualmente.
    sonidoAlarma.play()
        .then(() => { avisoSonidoAlarma.hidden = true; })
        .catch(() => { avisoSonidoAlarma.hidden = false; });

    // Vibración en móviles compatibles (ignorada si no existe).
    if (navigator.vibrate) navigator.vibrate([500, 300, 500]);
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
        dispararAlarma(alarma, retrasoMin);

        // Lo guardamos en la base de datos. El servidor mueve la repetitiva a su siguiente fecha o
        // desactiva la de un solo uso, y al recargar la lista desaparece de las pendientes.
        registrarSonada(alarma);
    }
}

// --- Botones ------------------------------------------------------------

// "Entendido": el paciente confirma que ha visto el aviso y paramos el sonido.
btnEntendido.addEventListener('click', () => {
    sonidoAlarma.pause();
    sonidoAlarma.currentTime = 0;
    if (navigator.vibrate) navigator.vibrate(0);
    titulosEnPantalla = [];
    avisoAlarma.hidden = true;
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
setInterval(comprobarAlarmas, INTERVALO_COMPROBACION_MS);

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
        const datos = await respuesta.json();

        // Si el servidor rechaza la alarma (p. ej. hora inválida), mostramos su motivo
        if (!respuesta.ok) {
            mostrarMensajeAlarma(datos.error || 'No se pudo crear la alarma', true);
            return;
        }

        mostrarMensajeAlarma('Alarma creada para el ' + fechaLegible(inputFecha.value) +
                             ' a las ' + inputHora.value, false);
        formAlarma.reset();       // vaciamos el formulario para poder crear otra
        prepararCampoFecha();     // reset() deja la fecha vacía: volvemos a poner hoy
        await cargarAlarmas();    // actualiza la lista y la comprobación de horas
    } catch (error) {
        mostrarMensajeAlarma('Error de conexión: no se pudo crear la alarma', true);
    }
});