// errores.js (riesgo 3.18): que ningún error quede oculto.
// - Distingue un fallo de RED (sin conexión, tiempo agotado) de un error del SERVIDOR (4xx/5xx)
//   y de un error de PROGRAMACIÓN (p. ej. una variable que no existe, como pasó con inputTitulo).
// - Cualquier error de JavaScript no capturado muestra un aviso visible en lugar de fallar en silencio.
// Lo usan conexion.js y el resto de scripts de la pantalla del paciente con window.AppErrores.
(() => {
    const aviso = document.getElementById('aviso-error-js');
    const textoAviso = document.getElementById('texto-aviso-error-js');

    // Error lanzado a propósito cuando el servidor responde con un código de error
    class ErrorServidor extends Error {
        constructor(status, mensaje) {
            super(mensaje || 'El servidor respondió con el error ' + status);
            this.name = 'ErrorServidor';
            this.status = status;
        }
    }

    // fetch lanza TypeError solo cuando no llega a hablar con el servidor. Los mensajes cambian
    // según el navegador: Chrome "Failed to fetch", Firefox "NetworkError…", Safari "Load failed".
    function esFalloDeRed(error) {
        if (!error) return false;
        if (error.name === 'AbortError' || error.name === 'TimeoutError') return true;
        return error instanceof TypeError && /fetch|network|load failed/i.test(error.message);
    }

    // 'red' | 'servidor' | 'codigo'
    function tipo(error) {
        if (esFalloDeRed(error)) return 'red';
        if (error && error.name === 'ErrorServidor') return 'servidor';
        return 'codigo';
    }

    // Deja siempre rastro en la consola y, si es un fallo de programación, avisa en pantalla.
    // Devuelve el tipo para que quien llama elija el mensaje para el paciente.
    function registrar(contexto, error) {
        const t = tipo(error);
        console.error('[' + contexto + '] (' + t + ')', error);
        if (t === 'codigo') mostrarAviso(contexto);
        return t;
    }

    function mostrarAviso(detalle) {
        if (!aviso) return;
        textoAviso.textContent = 'Algo ha fallado en esta pantalla' + (detalle ? ' (' + detalle + ')' : '') +
            '. El botón SOS sigue funcionando. Si algo no responde, recarga la página.';
        aviso.hidden = false;
    }

    // Errores que nadie capturó. Solo los de nuestros archivos: los de extensiones del navegador no.
    window.addEventListener('error', (evento) => {
        if (evento.filename && !evento.filename.includes('/static/')) return;
        console.error('Error no capturado:', evento.error || evento.message);
        mostrarAviso(evento.message);
    });
    window.addEventListener('unhandledrejection', (evento) => {
        console.error('Promesa rechazada sin capturar:', evento.reason);
        if (!esFalloDeRed(evento.reason)) mostrarAviso(evento.reason && evento.reason.message);
    });

    const cerrar = document.getElementById('btn-cerrar-aviso-error');
    if (cerrar) cerrar.addEventListener('click', () => { aviso.hidden = true; });

    window.AppErrores = { ErrorServidor, esFalloDeRed, tipo, registrar, mostrarAviso };
})();
