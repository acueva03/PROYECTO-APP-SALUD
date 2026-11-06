(() => {
    const TIMEOUT_MS = 6000;
    const btn = document.getElementById('btn-generar-codigo');
    const msg = document.getElementById('mensaje-vinculo');
    const bloque = document.getElementById('bloque-codigo');
    const codigoEl = document.getElementById('codigo-vinculo');
    const qrEl = document.getElementById('qr-vinculo');
    const caducidadEl = document.getElementById('caducidad-vinculo');
    let temporizador = null;

    function mostrarMensaje(texto, esError) {
        msg.textContent = texto;
        msg.className = esError ? 'mensaje error' : 'mensaje';
    }

    function ocultarCodigo() {
        clearInterval(temporizador);
        bloque.hidden = true;
        codigoEl.textContent = '';
        qrEl.removeAttribute('src');
        qrEl.hidden = true;
    }

    // La cuenta atrás usa el reloj del móvil desde que llega el código (no la hora absoluta del servidor),
    // así un móvil con la hora mal puesta no muestra una caducidad falsa (riesgo 3.13)
    function iniciarCuentaAtras(minutos) {
        clearInterval(temporizador);
        const fin = Date.now() + minutos * 60000;
        const pintar = () => {
            const seg = Math.max(0, Math.round((fin - Date.now()) / 1000));
            if (seg === 0) {
                ocultarCodigo();
                mostrarMensaje('El código ha caducado. Genera uno nuevo.', false);
                return;
            }
            caducidadEl.textContent = 'Caduca en ' + Math.floor(seg / 60) + ':' + String(seg % 60).padStart(2, '0');
        };
        pintar();
        temporizador = setInterval(pintar, 1000);
    }

    btn.addEventListener('click', async () => {
        btn.disabled = true;
        mostrarMensaje('Generando código…', false);
        const controller = new AbortController();
        const t = setTimeout(() => controller.abort(), TIMEOUT_MS);
        try {
            const r = await fetch('/api/vinculos/codigo', { method: 'POST', signal: controller.signal });
            const datos = await r.json();
            if (!r.ok) {
                ocultarCodigo();
                mostrarMensaje(datos.error || 'No se pudo generar el código', true);
                return;
            }
            codigoEl.textContent = datos.codigo;
            if (datos.qr) {
                qrEl.src = datos.qr;
                qrEl.hidden = false;
            } else {
                qrEl.hidden = true;     // sin librería qrcode: se ve solo el código escrito
            }
            bloque.hidden = false;
            mostrarMensaje('Dale este código a tu supervisor, o enséñale el QR. Solo sirve una vez.', false);
            iniciarCuentaAtras(datos.minutos);
        } catch (e) {
            ocultarCodigo();
            mostrarMensaje('No se pudo conectar con el servidor. Comprueba tu conexión e inténtalo de nuevo.', true);
        } finally {
            clearTimeout(t);
            btn.disabled = false;
        }
    });
})();