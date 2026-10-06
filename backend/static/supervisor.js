const SUPERVISOR_ID = 1;  // provisional hasta que haya login
const INTERVALO_MS = 3000;

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
        return;
    }
    bloque.className = 'estado-alertas alerta-activa';
    bloque.replaceChildren(...alertas.map(crearTarjetaAlerta));
    contador.textContent = alertas.length + (alertas.length === 1 ? ' alerta' : ' alertas');
    contador.classList.add('con-alertas');
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