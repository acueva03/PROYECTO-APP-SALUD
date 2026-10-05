// 1. LOCALIZAR EL BOTÓN
// Le decimos a la página web que busque el elemento con el ID 'boton-sos' y lo guarde en la variable 'botonAlerta'
const botonAlerta = document.getElementById('boton-sos');

// 2. ESCUCHAR EL CLIC
// Ponemos al botón en modo vigilancia. Cuando detecte un evento 'click', ejecutará las instrucciones que hay dentro.
botonAlerta.addEventListener('click', function() {
    console.log("¡Clic detectado! Preparando el envío...");

    // 3. ENVIAR EL MENSAJE AL SERVIDOR
    // fetch es el mensajero de internet. Le damos la dirección a la que debe ir (el servidor local de Alberto).
    fetch('http://127.0.0.1:5000/alerta', {
        method: 'POST', // POST significa que vamos a "enviar" o publicar información nueva.
        headers: {
            'Content-Type': 'application/json' // Le decimos al servidor que el paquete de texto va en formato JSON.
        },
        body: JSON.stringify({ mensaje: "¡Emergencia! El usuario necesita ayuda inmediata." }) // El contenido del paquete.
    })
    .then(respuesta => {
        // Si el servidor de Python recibe el paquete correctamente, se ejecuta esto:
        console.log("El servidor ha recibido la alerta con éxito.");
    })
    .catch(error => {
        // Si el servidor está apagado o falla la conexión, se captura el error aquí:
        console.error("El mensajero no pudo entregar el paquete. El servidor no responde:", error);
    });
});