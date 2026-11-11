(() => {
    const TIMEOUT_MS = 6000;
    const btn = document.getElementById('btn-generar-codigo');
    const msg = document.getElementById('mensaje-vinculo');
    const bloque = document.getElementById('bloque-codigo');
    const codigoEl = document.getElementById('codigo-vinculo');
    const qrEl = document.getElementById('qr-vinculo');
    const caducidadEl = document.getElementById('caducidad-vinculo');
    const listaSup = document.getElementById('lista-supervisores');
    const msgSup = document.getElementById('mensaje-supervisores');
    let temporizador = null;
    let cantidadSupervisores = null;    // null = todavía no se ha cargado la lista
    let ultimaLista = '';

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

    // ---- Mis supervisores: el paciente siempre puede ver quién le supervisa y quitarle el acceso ----
    function mostrarMensajeSup(texto, esError) {
        msgSup.textContent = texto;
        msgSup.className = esError ? 'mensaje error' : 'mensaje ok';
    }

    // textContent (no innerHTML): un nombre con símbolos raros nunca se interpreta como HTML
    function pintarSupervisores(supervisores) {
        listaSup.replaceChildren();
        if (supervisores.length === 0) {
            const li = document.createElement('li');
            li.className = 'texto-suave';
            li.textContent = 'Todavía no tienes ningún supervisor vinculado.';
            listaSup.appendChild(li);
            return;
        }
        for (const s of supervisores) {
            const li = document.createElement('li');
            li.className = 'item-vinculo';
            const nombre = document.createElement('span');
            nombre.textContent = s.nombre;
            const boton = document.createElement('button');
            boton.type = 'button';
            boton.className = 'btn btn-secundario btn-desvincular';
            boton.textContent = 'Quitar';
            boton.setAttribute('aria-label', 'Quitar a ' + s.nombre + ' como supervisor');
            boton.addEventListener('click', () => quitarSupervisor(s, boton, supervisores.length === 1));
            li.append(nombre, boton);
            listaSup.appendChild(li);
        }
    }

    // silencioso = true en las comprobaciones automáticas: un fallo de red puntual no molesta con mensajes
    async function cargarSupervisores(silencioso) {
        const controller = new AbortController();
        const t = setTimeout(() => controller.abort(), TIMEOUT_MS);
        try {
            const r = await fetch('/api/vinculos/supervisores', { signal: controller.signal });
            const datos = await r.json();
            if (!r.ok) {
                if (!silencioso) mostrarMensajeSup(datos.error || 'No se pudo cargar la lista', true);
                return;
            }
            const hayNuevo = cantidadSupervisores !== null && datos.length > cantidadSupervisores;
            cantidadSupervisores = datos.length;
            const huella = JSON.stringify(datos);
            if (huella !== ultimaLista) {         // solo se repinta si algo ha cambiado
                ultimaLista = huella;
                pintarSupervisores(datos);
            }
            if (hayNuevo && !bloque.hidden) {     // el código ya se ha usado: se deja de enseñar
                ocultarCodigo();
                mostrarMensaje('Un supervisor se ha vinculado contigo correctamente.', false);
            }
        } catch (e) {
            console.error('[vinculos_paciente]', e);                                               // 3.18
            if (!silencioso) mostrarMensajeSup('No se pudo conectar con el servidor. Comprueba tu conexión e inténtalo de nuevo.', true);
        } finally {
            clearTimeout(t);
        }
    }

    async function quitarSupervisor(supervisor, boton, esElUnico) {
        let aviso = '¿Quitar a ' + supervisor.nombre + ' como supervisor? Dejará de ver tus datos y de recibir tus avisos SOS.';
        if (esElUnico) {
            aviso += ' Es tu único supervisor: nadie recibirá tus avisos SOS hasta que vincules a otro.';
        }
        if (!window.confirm(aviso)) return;
        boton.disabled = true;
        const controller = new AbortController();
        const t = setTimeout(() => controller.abort(), TIMEOUT_MS);
        try {
            const r = await fetch('/api/vinculos/supervisores/' + supervisor.id, { method: 'DELETE', signal: controller.signal });
            const datos = await r.json();
            if (!r.ok) {
                mostrarMensajeSup(datos.error || 'No se pudo quitar al supervisor', true);
                boton.disabled = false;
                return;
            }
            mostrarMensajeSup(datos.mensaje, false);
            await cargarSupervisores(false);
        } catch (e) {
            console.error('[vinculos_paciente]', e);                                               // 3.18
            mostrarMensajeSup('No se pudo conectar con el servidor. Comprueba tu conexión e inténtalo de nuevo.', true);
            boton.disabled = false;
        } finally {
            clearTimeout(t);
        }
    }

    cargarSupervisores(false);
    setInterval(() => cargarSupervisores(true), 10000);   // así ve al instante quién se ha vinculado

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
            console.error('[vinculos_paciente]', e);                                               // 3.18
            ocultarCodigo();
            mostrarMensaje('No se pudo conectar con el servidor. Comprueba tu conexión e inténtalo de nuevo.', true);
        } finally {
            clearTimeout(t);
            btn.disabled = false;
        }
    });
})();