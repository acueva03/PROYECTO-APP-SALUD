// sos.js: SOLO el botón SOS de la pantalla del paciente (riesgo 3.18.1).
// Está separado de conexion.js (alarmas) a propósito: si algo falla en las alarmas, el SOS sigue
// funcionando. Por eso NO usa nada de otros archivos (ni errores.js ni accesibilidad.js) y se carga el primero.
(() => {
    const TIMEOUT_MS = 5000;
    const boton = document.getElementById('boton-sos');
    const resultado = document.getElementById('resultado-sos');
    const textoResultado = document.getElementById('texto-resultado-sos');
    const enlace112 = document.getElementById('llamar-112');
    if (!boton) return;

    // Lee en voz alta si el paciente no lo ha desactivado en "Ajustes de letra, contraste y voz".
    // Lee la preferencia directamente de localStorage para no depender de accesibilidad.js.
    function leerEnVozAlta(texto) {
        try {
            const ajustes = JSON.parse(localStorage.getItem('app-salud-accesibilidad') || '{}');
            if (ajustes.voz === false || !('speechSynthesis' in window)) return;
            window.speechSynthesis.cancel();
            const frase = new SpeechSynthesisUtterance(texto);
            frase.lang = 'es-ES';
            frase.rate = 0.9;
            window.speechSynthesis.speak(frase);
        } catch (error) {
            console.error('SOS: no se pudo leer el mensaje en voz alta', error);
        }
    }

    // Muestra el resultado junto al botón. Si es un error, enseña también el botón para llamar al 112.
    function mostrar(texto, esError) {
        if (!resultado) { window.alert(texto); return; }      // por si alguien borra el bloque del HTML
        textoResultado.textContent = texto;
        resultado.className = 'resultado-sos ' + (esError ? 'error' : 'ok');
        resultado.hidden = false;
        if (enlace112) enlace112.hidden = !esError;
        leerEnVozAlta(texto);
    }

    boton.addEventListener('click', async () => {
        boton.disabled = true;
        mostrar('Enviando aviso a tu supervisor…', false);
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);
        let respuesta;
        try {
            respuesta = await fetch('/api/sos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: '{}',
                signal: controller.signal
            });
        } catch (error) {
            // Aquí solo puede fallar la red: sin conexión o el servidor tarda más de 5 s
            console.error('SOS: fallo de red', error);
            mostrar('Error de conexión: tu supervisor NO ha recibido el aviso. LLAME AL 112.', true);
            return;
        } finally {
            clearTimeout(timeoutId);
            boton.disabled = false;
        }

        if (respuesta.ok) {
            mostrar('Aviso enviado. Tu supervisor ha sido notificado.', false);
        } else if (respuesta.status === 401) {
            console.error('SOS: sesión caducada (401)');
            mostrar('Tu sesión ha caducado: tu supervisor NO ha recibido el aviso. LLAME AL 112 y después vuelve a entrar.', true);
        } else {
            console.error('SOS: el servidor respondió', respuesta.status);
            mostrar('El servidor no ha podido registrar el aviso (error ' + respuesta.status + '). LLAME AL 112.', true);
        }
    });
})();
