(() => {
    const TIMEOUT_MS = 6000;
    const form = document.getElementById('form-canjear');
    const input = document.getElementById('codigo');
    const msg = document.getElementById('mensaje-canje');
    const btnEscanear = document.getElementById('btn-escanear');
    const contenedorLector = document.getElementById('lector-qr');
    const TEXTO_ESCANEAR = '📷 Escanear QR con la cámara';
    let lector = null;
    let enviando = false;

    function mostrar(texto, ok) {
        msg.textContent = texto;
        msg.className = 'mensaje ' + (ok ? 'ok' : 'error');
    }

    // El QR contiene una URL como http://.../vincular?c=ABCDEFGH; también se admite el código suelto
    function extraerCodigo(texto) {
        const m = String(texto).match(/[?&]c=([A-Za-z0-9-]+)/);
        return m ? m[1] : String(texto);
    }

    async function canjear() {
        if (enviando) return;
        enviando = true;
        const controller = new AbortController();
        const t = setTimeout(() => controller.abort(), TIMEOUT_MS);
        try {
            const r = await fetch('/api/vinculos/canjear', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ codigo: input.value }),
                signal: controller.signal
            });
            const datos = await r.json();
            if (!r.ok) {
                mostrar(datos.error || 'No se pudo vincular', false);
                return;
            }
            
            // NEW: Lock the UI to show the supervisor is linked
            mostrar('¡Supervisor vinculado correctamente!', true);
            form.hidden = true;               // Hide the input form
            contenedorLector.hidden = true;   // Hide the camera/QR scanner completely
            
            // Redirect after a brief moment
            setTimeout(() => { window.location.href = '/supervisor'; }, 2000);
        } catch (e) {
            mostrar('No se pudo conectar con el servidor. Comprueba tu conexión e inténtalo de nuevo.', false);
        } finally {
            clearTimeout(t);
            enviando = false;
        }
    }

    async function detenerLector() {
        const actual = lector;
        lector = null;
        contenedorLector.hidden = true;
        btnEscanear.textContent = TEXTO_ESCANEAR;
        if (!actual) return;
        try {
            await actual.stop();
            actual.clear();
        } catch (e) {
            console.warn('No se pudo parar la cámara:', e);
        }
    }

    btnEscanear.addEventListener('click', async () => {
        if (lector) {
            await detenerLector();
            return;
        }
        if (typeof Html5Qrcode === 'undefined') {
            mostrar('No se pudo cargar el lector de QR. Escribe el código a mano.', false);
            return;
        }
        contenedorLector.hidden = false;
        btnEscanear.textContent = 'Cerrar cámara';
        lector = new Html5Qrcode('lector-qr');
        try {
            await lector.start(
                { facingMode: 'environment' },
                { fps: 10, qrbox: { width: 220, height: 220 } },
                (texto) => {
                    input.value = extraerCodigo(texto);
                    detenerLector().then(canjear);
                },
                () => { /* fotograma sin QR: se ignora a propósito */ }
            );
        } catch (e) {
            lector = null;
            contenedorLector.hidden = true;
            btnEscanear.textContent = TEXTO_ESCANEAR;
            mostrar('No se pudo abrir la cámara (necesita permiso, y HTTPS o localhost). Escribe el código a mano.', false);
        }
    });

    form.addEventListener('submit', (ev) => {
        ev.preventDefault();
        canjear();
    });
})();