(() => {
    const TIMEOUT_MS = 6000;
    const form = document.getElementById('form-canjear');
    const input = document.getElementById('codigo');
    const msg = document.getElementById('mensaje-canje');
    const btnEscanear = document.getElementById('btn-escanear');
    const contenedorLector = document.getElementById('lector-qr');
    const TEXTO_ESCANEAR = '📷 Escanear QR con la cámara';
    const lista = document.getElementById('lista-pacientes');
    const msgPacientes = document.getElementById('mensaje-pacientes');
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

    // ---- Pacientes vinculados y desvinculación ----
    function mostrarPacientes(texto, ok) {
        msgPacientes.textContent = texto;
        msgPacientes.className = 'mensaje ' + (ok ? 'ok' : 'error');
    }

    // textContent (no innerHTML): un nombre con símbolos raros nunca se interpreta como HTML
    function pintarPacientes(pacientes) {
        lista.replaceChildren();
        if (pacientes.length === 0) {
            const li = document.createElement('li');
            li.className = 'texto-suave';
            li.textContent = 'Todavía no tienes pacientes vinculados.';
            lista.appendChild(li);
            return;
        }
        for (const p of pacientes) {
            const li = document.createElement('li');
            li.className = 'item-vinculo';
            const nombre = document.createElement('span');
            nombre.textContent = p.nombre;
            const boton = document.createElement('button');
            boton.type = 'button';
            boton.className = 'btn btn-secundario btn-desvincular';
            boton.textContent = 'Desvincular';
            boton.setAttribute('aria-label', 'Desvincular a ' + p.nombre);
            boton.addEventListener('click', () => desvincular(p, boton));
            li.append(nombre, boton);
            lista.appendChild(li);
        }
    }

    async function cargarPacientes() {
        const controller = new AbortController();
        const t = setTimeout(() => controller.abort(), TIMEOUT_MS);
        try {
            const r = await fetch('/api/vinculos/pacientes', { signal: controller.signal });
            const datos = await r.json();
            if (!r.ok) {
                mostrarPacientes(datos.error || 'No se pudo cargar la lista', false);
                return;
            }
            pintarPacientes(datos);
        } catch (e) {
            mostrarPacientes('No se pudo conectar con el servidor. Comprueba tu conexión e inténtalo de nuevo.', false);
        } finally {
            clearTimeout(t);
        }
    }

    async function desvincular(paciente, boton) {
        const aviso = '¿Dejar de supervisar a ' + paciente.nombre + '? Dejarás de recibir sus avisos y de ver sus datos. '
                    + 'Para volver a vincularte, el paciente tendrá que generar un código nuevo.';
        if (!window.confirm(aviso)) return;
        boton.disabled = true;
        const controller = new AbortController();
        const t = setTimeout(() => controller.abort(), TIMEOUT_MS);
        try {
            const r = await fetch('/api/vinculos/pacientes/' + paciente.id, { method: 'DELETE', signal: controller.signal });
            const datos = await r.json();
            if (!r.ok) {
                mostrarPacientes(datos.error || 'No se pudo desvincular', false);
                boton.disabled = false;
                return;
            }
            mostrarPacientes(datos.mensaje, true);
            await cargarPacientes();
        } catch (e) {
            mostrarPacientes('No se pudo conectar con el servidor. Comprueba tu conexión e inténtalo de nuevo.', false);
            boton.disabled = false;
        } finally {
            clearTimeout(t);
        }
    }

    cargarPacientes();

    form.addEventListener('submit', (ev) => {
        ev.preventDefault();
        canjear();
    });
})();