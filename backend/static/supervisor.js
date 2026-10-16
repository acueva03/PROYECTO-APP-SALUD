const SUPERVISOR_ID = 1;  // provisional hasta que haya login
const INTERVALO_MS = 3000;

// Carga el archivo localmente desde tu servidor Flask
const alarmaSonora = new Audio('/static/alarma.mp3'); 
alarmaSonora.loop = true;

const bloque = document.querySelector('.estado-alertas');
const contador = document.querySelector('.contador-alertas');
const htmlTodoBien = bloque.innerHTML;  // guardamos el estado "todo bien" original
let ultimoEstado = '';

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


function mostrarAlertas(alertas) {
    if (alertas.length === 0) {
        bloque.className = 'estado-alertas';
        bloque.innerHTML = htmlTodoBien;
        contador.textContent = '0 alertas';
        contador.classList.remove('con-alertas');
        
        // Apagar el pitido si se han atendido todas
        alarmaSonora.pause();
        alarmaSonora.currentTime = 0;
        return;
    }
    
    bloque.className = 'estado-alertas alerta-activa';
    bloque.replaceChildren(...alertas.map(crearTarjetaAlerta));
    contador.textContent = alertas.length + (alertas.length === 1 ? ' alerta' : ' alertas');
    contador.classList.add('con-alertas');

    // Disparar pitido acústico y capturar posible bloqueo del navegador (autoplay)
    alarmaSonora.play().catch(error => console.warn('El navegador bloqueó el autoplay del sonido', error));
}

async function consultarAlertas() {
    try {
        const respuesta = await fetch('/api/supervisores/' + SUPERVISOR_ID + '/alertas');
        const alertas = await respuesta.json();
        const estadoNuevo = JSON.stringify(alertas);
        if (estadoNuevo !== ultimoEstado) {   // solo repintamos si algo cambió
            ultimoEstado = estadoNuevo;
            mostrarAlertas(alertas);
        }
    } catch (error) {
        console.error('No se pudo consultar las alertas', error);
    }
}

async function atenderAlerta(id) {
    await fetch('/api/alertas/' + id + '/atender', { method: 'POST' });
    consultarAlertas();
}

consultarAlertas();
setInterval(consultarAlertas, INTERVALO_MS);

// Desbloquear el motor de audio con el primer clic en la página
document.body.addEventListener('click', function desbloquearAudio() {
    // Intentamos reproducir y pausar inmediatamente
    alarmaSonora.play().then(() => {
        alarmaSonora.pause();
        alarmaSonora.currentTime = 0;
    }).catch((error) => console.warn('Aún no se puede reproducir', error));
    
    // Eliminamos el listener para que solo se ejecute la primera vez
    document.body.removeEventListener('click', desbloquearAudio);
});