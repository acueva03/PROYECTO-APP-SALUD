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

let alarmas = [];                          // última lista conocida (si falla la red, seguimos con ella)
const yaDisparadas = new Set();            // claves "id|fecha|hora" para no repetir el aviso en el mismo minuto
let titulosEnPantalla = [];                // alarmas que están sonando ahora mismo (puede haber varias a la vez)

// --- Utilidades de tiempo --------------------------------------------------

// Devuelve la hora local actual con el MISMO formato que guarda la BD ("08:05")
function horaActual() {
    const ahora = new Date();
    const hh = String(ahora.getHours()).padStart(2, '0'); // padStart/(2,'0') añade el cero inicial si falta
    const mm = String(ahora.getMinutes()).padStart(2, '0');
    return hh + ':' + mm;
}

// Fecha local en formato "2026-10-17"
function fechaActual() {
    const d = new Date();
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' +
           String(d.getDate()).padStart(2, '0');
}

// --- Comunicación con el servidor -----------------------------------------

// Descarga las alarmas activas. Si falla (sin red, servidor caído), NO vaciamos la lista:
// así una alarma ya cargada sigue sonando aunque se pierda la conexión.
async function cargarAlarmas() {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_ALARMAS_MS);
    try {
        const respuesta = await fetch('/api/usuarios/' + USER_ID + '/alarmas',
                                      { signal: controller.signal });
        if (!respuesta.ok) throw new Error('HTTP ' + respuesta.status);
        alarmas = await respuesta.json();
        mostrarListaAlarmas();   // <-- LÍNEA NUEVA: refresca la lista visible
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

// --- Aviso al paciente ------------------------------------------------------

// Muestra el aviso y hace sonar la alarma.
function dispararAlarma(alarma) {
    titulosEnPantalla.push(alarma.titulo);
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
    const hora = horaActual();
    const fecha = fechaActual();

    for (const alarma of alarmas) {
        if (alarma.hora !== hora) continue;

        // La clave incluye la fecha: una repetitiva vuelve a sonar mañana,
        // pero no 60 veces dentro del mismo minuto (el intervalo corre cada segundo).
        const clave = alarma.id + '|' + fecha + '|' + alarma.hora;
        if (yaDisparadas.has(clave)) continue;
        yaDisparadas.add(clave);

        dispararAlarma(alarma);

        // Una alarma de un solo uso se apaga para no volver a sonar mañana.
        if (!alarma.es_repetitiva) {
            desactivarAlarma(alarma.id);
            // La quitamos también de la lista local; si no, seguiría ahí hasta la próxima recarga.
            alarmas = alarmas.filter(a => a.id !== alarma.id);
        }
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
const inputHora = document.getElementById('alarma-hora');
const inputRepetitiva = document.getElementById('alarma-repetitiva');
const mensajeAlarma = document.getElementById('mensaje-alarma');
const listaAlarmas = document.getElementById('lista-alarmas');

// Muestra un mensaje bajo el formulario. esError cambia el color (rojo/verde) con una clase CSS.
function mostrarMensajeAlarma(texto, esError) {
    mensajeAlarma.textContent = texto;
    mensajeAlarma.className = 'mensaje-alarma ' + (esError ? 'error' : 'ok');
}

// Dibuja la lista de alarmas activas a partir de la variable global "alarmas" (PARTE 2).
// Se usa createElement + textContent (y no innerHTML) para que un título con
// caracteres raros no pueda inyectar HTML en la página.
function mostrarListaAlarmas() {
    listaAlarmas.replaceChildren();   // vaciamos la lista antes de redibujarla

    if (alarmas.length === 0) {
        const vacio = document.createElement('li');
        vacio.className = 'lista-vacia';
        vacio.textContent = 'No tienes alarmas activas.';
        listaAlarmas.append(vacio);
        return;
    }

    // Ordenadas por hora: como el formato es "HH:MM", ordenar el texto equivale a ordenar la hora
    const ordenadas = [...alarmas].sort((a, b) => a.hora.localeCompare(b.hora));

    for (const alarma of ordenadas) {
        const li = document.createElement('li');

        const texto = document.createElement('span');
        texto.textContent = alarma.hora + ' · ' + alarma.titulo +
                            (alarma.es_repetitiva ? ' (cada día)' : '');

        const btnQuitar = document.createElement('button');
        btnQuitar.type = 'button';
        btnQuitar.className = 'btn-quitar-alarma';
        btnQuitar.textContent = 'Quitar';
        btnQuitar.addEventListener('click', async () => {
            await desactivarAlarma(alarma.id);   // función de la PARTE 2 (PATCH activa=false)
            await cargarAlarmas();               // recargamos para que desaparezca de la lista
        });

        li.append(texto, btnQuitar);
        listaAlarmas.append(li);
    }
}

// Envío del formulario: crea la alarma en el servidor.
formAlarma.addEventListener('submit', async (evento) => {
    evento.preventDefault();   // evita que el navegador recargue la página al enviar

    try {
        const respuesta = await fetch('/api/alarmas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: USER_ID,
                titulo: inputTitulo.value.trim(),
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

        mostrarMensajeAlarma('Alarma creada para las ' + inputHora.value, false);
        formAlarma.reset();       // vaciamos el formulario para poder crear otra
        await cargarAlarmas();    // actualiza la lista y la comprobación de horas
    } catch (error) {
        mostrarMensajeAlarma('Error de conexión: no se pudo crear la alarma', true);
    }
});