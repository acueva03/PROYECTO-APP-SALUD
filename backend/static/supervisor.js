const SUPERVISOR_ID = 1;  // provisional hasta que haya login
const INTERVALO_MS = 3000;
const TIMEOUT_MS = 2500;
const FALLOS_PARA_AVISAR = 2;

const alarmaSonora = new Audio('/static/alarma.mp3');
alarmaSonora.loop = true;

const bloque = document.querySelector('.estado-alertas');
const contador = document.querySelector('.contador-alertas');
const avisoSonido = document.getElementById('aviso-sonido');
const btnSonido = document.getElementById('btn-activar-sonido');
const avisoConexion = document.getElementById('aviso-conexion');
const htmlTodoBien = bloque.innerHTML;

const estadoSistema = document.getElementById('estado-sistema');
const puntoSistema = document.getElementById('punto-sistema');
const textoSistema = document.getElementById('texto-sistema');
const ultimaComprobacion = document.getElementById('ultima-comprobacion');
const estadoPaciente = document.getElementById('estado-paciente');
const iconoEstado = document.getElementById('icono-estado');

function horaAhora() {
    return new Date().toLocaleTimeString('es-ES',
        { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function marcarConexion(ok) {
    estadoSistema.classList.toggle('sin-conexion', !ok);
    puntoSistema.classList.toggle('rojo', !ok);
    textoSistema.textContent = ok ? 'Conectado al servidor' : 'Sin conexión con el servidor';
}

function actualizarEstado(numAlertas) {
    if (numAlertas > 0) {
        estadoPaciente.textContent = '¡Alerta SOS activa!';
        iconoEstado.textContent = '⚠';
    } else {
        estadoPaciente.textContent = 'Sin alertas activas';
        iconoEstado.textContent = '✓';
    }
}

// Saludo según la hora del día
const hora = new Date().getHours();
document.getElementById('saludo').textContent =
    hora < 13 ? 'Buenos días' : (hora < 21 ? 'Buenas tardes' : 'Buenas noches');

let ultimoEstado = '';
let hayAlertas = false;
let fallosSeguidos = 0;

function crearTarjetaAlerta(alerta) {
    const div = document.createElement('div');

    const titulo = document.createElement('h3');
    titulo.textContent = '¡SOS de ' + alerta.dependiente + '!';

    const hora = document.createElement('p');
    hora.textContent = 'Enviada a las ' + new Date(alerta.fecha_hora)
        .toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });

    const boton = document.createElement('button');
    boton.textContent = 'Marcar como atendida';
    boton.className = 'btn-atender';
    boton.addEventListener('click', () => atenderAlerta(alerta.alerta_id));

    div.append(titulo, hora, boton);
    return div;
}

// Solo pinta; el sonido se gestiona aparte en sincronizarSonido()
function mostrarAlertas(alertas) {
    if (alertas.length === 0) {
        bloque.className = 'estado-alertas';
        bloque.innerHTML = htmlTodoBien;
        contador.textContent = '0 alertas';
        contador.classList.remove('con-alertas');
        return;
    }
    bloque.className = 'estado-alertas alerta-activa';
    bloque.replaceChildren(...alertas.map(crearTarjetaAlerta));
    contador.textContent = alertas.length + (alertas.length === 1 ? ' alerta' : ' alertas');
    contador.classList.add('con-alertas');
}

// Se ejecuta en CADA consulta: si hay alertas y no suena, lo reintenta
function sincronizarSonido() {
    if (hayAlertas) {
        if (alarmaSonora.paused) {
            alarmaSonora.play()
                .then(() => { avisoSonido.hidden = true; })
                .catch(() => { avisoSonido.hidden = false; });
        }
    } else {
        alarmaSonora.pause();
        alarmaSonora.currentTime = 0;
    }
}

btnSonido.addEventListener('click', async () => {
    try {
        await alarmaSonora.play();      // el clic desbloquea el audio
        alarmaSonora.pause();
        alarmaSonora.currentTime = 0;
        avisoSonido.hidden = true;
    } catch (error) {
        console.warn('No se pudo activar el sonido', error);
    }
    sincronizarSonido();                // si ya había alerta, vuelve a sonar
});

async function consultarAlertas() {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);
    try {
        const respuesta = await fetch('/api/supervisores/' + SUPERVISOR_ID + '/alertas',
                                      { signal: controller.signal });
        if (!respuesta.ok) throw new Error('HTTP ' + respuesta.status);
        const alertas = await respuesta.json();

        fallosSeguidos = 0;
        avisoConexion.hidden = true;

        const estadoNuevo = JSON.stringify(alertas);
        if (estadoNuevo !== ultimoEstado) {
            ultimoEstado = estadoNuevo;
            mostrarAlertas(alertas);
        }

        // Indicadores reales (después de mostrarAlertas, que puede recrear el bloque)
        marcarConexion(true);
        actualizarEstado(alertas.length);
        ultimaComprobacion.textContent = horaAhora();
        const revision = document.getElementById('ultima-revision');
        if (revision) revision.textContent = 'Última revisión: ' + horaAhora();

        hayAlertas = alertas.length > 0;
        sincronizarSonido();
    } catch (error) {
        fallosSeguidos++;
        console.error('No se pudo consultar las alertas', error);
        if (fallosSeguidos >= FALLOS_PARA_AVISAR) {
            avisoConexion.hidden = false;
            marcarConexion(false);
            estadoPaciente.textContent = 'Desconocido (sin conexión)';
            iconoEstado.textContent = '?';
        }
    } finally {
        clearTimeout(timeoutId);
    }
}

async function atenderAlerta(id) {
    try {
        const respuesta = await fetch('/api/alertas/' + id + '/atender', { method: 'POST' });
        if (!respuesta.ok) throw new Error('HTTP ' + respuesta.status);
    } catch (error) {
        alert('No se pudo marcar la alerta como atendida. Inténtalo de nuevo.');
        return;
    }
    consultarAlertas();
}

consultarAlertas();
setInterval(consultarAlertas, INTERVALO_MS);

window.addEventListener('beforeunload', (evento) => {
    evento.preventDefault();
    evento.returnValue = '';   // necesario para que Chrome muestre el diálogo
});

// RESUMEN REAL DEL DEPENDIENTE (sustituye al texto estático)
const nombrePaciente = document.getElementById('nombre-paciente');
const ultimaConexionPaciente = document.getElementById('ultima-conexion-paciente');
const listaActividad = document.getElementById('lista-actividad');

async function cargarResumen() {
    try {
        const r = await fetch('/api/supervisores/' + SUPERVISOR_ID + '/resumen');
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const datos = await r.json();

        if (nombrePaciente) {
            nombrePaciente.textContent = datos.dependiente.nombre +
                (datos.dependiente.apellidos ? ' ' + datos.dependiente.apellidos : '');
        }
        if (ultimaConexionPaciente) {
            ultimaConexionPaciente.textContent = datos.ultima_conexion
                ? new Date(datos.ultima_conexion).toLocaleString('es-ES',
                    { dateStyle: 'short', timeStyle: 'short' })
                : 'Sin datos todavía';
        }
        if (listaActividad) {
            if (datos.actividad.length === 0) {
                const p = document.createElement('p');
                p.textContent = 'Todavía no hay actividad registrada.';
                listaActividad.replaceChildren(p);
            } else {
                listaActividad.replaceChildren(...datos.actividad.map(crearItemActividad));
            }
        }
    } catch (error) {
        console.error('No se pudo cargar el resumen', error);   // el resto del panel sigue funcionando
    }
}

function crearItemActividad(ev) {
    const item = document.createElement('div');
    item.className = 'actividad-item';

    const icono = document.createElement('div');
    icono.className = 'actividad-icono ' + (ev.tipo === 'sos' ? 'sistema' : 'conectado');
    icono.textContent = ev.tipo === 'sos' ? '!' : '⏰';

    const texto = document.createElement('div');
    texto.className = 'actividad-texto';
    const fuerte = document.createElement('strong');
    fuerte.textContent = ev.texto;
    texto.append(fuerte);

    const tiempo = document.createElement('time');
    tiempo.textContent = new Date(ev.fecha_hora).toLocaleString('es-ES',
        { dateStyle: 'short', timeStyle: 'short' });

    item.append(icono, texto, tiempo);
    return item;
}

cargarResumen();
setInterval(cargarResumen, 15000);