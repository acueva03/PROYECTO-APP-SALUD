// accesibilidad.js (riesgo 3.25 e historia de usuario 23): pantalla del PACIENTE.
//  - Ajustes de visualización: tamaño de letra, alto contraste y quitar animaciones.
//  - Lectura en voz alta de los avisos (Web Speech API, speechSynthesis).
//  - Anuncios para lectores de pantalla mediante dos regiones aria-live que existen SIEMPRE en el HTML
//    (si la región se crea o se muestra en el mismo momento que el texto, muchos lectores no lo leen).
// Las preferencias se guardan en este móvil (localStorage); no se envían al servidor.
// Uso desde otros archivos: window.AppAccesibilidad.leer(texto) y .anunciar(texto, urgente)
(() => {
    const CLAVE = 'app-salud-accesibilidad';          // sos.js lee la misma clave para la voz
    const POR_DEFECTO = { letra: 'normal', contraste: false, voz: true, sinAnimaciones: false };
    const raiz = document.documentElement;
    const hayVoz = 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;

    // ---------- Preferencias ----------
    function cargar() {
        try {
            return { ...POR_DEFECTO, ...JSON.parse(localStorage.getItem(CLAVE) || '{}') };
        } catch (error) {
            console.error('Accesibilidad: preferencias guardadas ilegibles, se usan las de serie', error);
            return { ...POR_DEFECTO };
        }
    }

    function guardar() {
        try {
            localStorage.setItem(CLAVE, JSON.stringify(ajustes));
        } catch (error) {
            console.error('Accesibilidad: no se pudieron guardar las preferencias', error);
        }
    }

    function aplicar() {
        raiz.dataset.letra = ajustes.letra;
        raiz.classList.toggle('alto-contraste', ajustes.contraste);
        raiz.classList.toggle('sin-animaciones', ajustes.sinAnimaciones);
    }

    const ajustes = cargar();
    aplicar();

    // ---------- Anuncios para lectores de pantalla ----------
    const regionEducada = document.getElementById('anuncio-educado');     // aria-live="polite"
    const regionUrgente = document.getElementById('anuncio-urgente');     // aria-live="assertive"

    function anunciar(texto, urgente = false) {
        const region = urgente ? regionUrgente : regionEducada;
        if (!region) return;
        // Se vacía y se escribe un instante después: así se vuelve a leer aunque el texto se repita
        region.textContent = '';
        setTimeout(() => { region.textContent = texto; }, 100);
    }

    // ---------- Voz ----------
    function vozEspanola() {
        const voces = window.speechSynthesis.getVoices();
        return voces.find(v => v.lang === 'es-ES') || voces.find(v => v.lang && v.lang.startsWith('es')) || null;
    }

    // Devuelve una promesa que se cumple al terminar de hablar (o enseguida si la voz está apagada)
    function leer(texto, { forzar = false } = {}) {
        return new Promise((resolver) => {
            if (!hayVoz || (!ajustes.voz && !forzar) || !texto) { resolver(false); return; }
            try {
                window.speechSynthesis.cancel();
                const frase = new SpeechSynthesisUtterance(texto);
                frase.lang = 'es-ES';
                frase.rate = 0.9;                               // un poco más despacio que lo normal
                const voz = vozEspanola();
                if (voz) frase.voice = voz;
                frase.onend = () => resolver(true);
                frase.onerror = (evento) => {
                    // "interrupted"/"canceled" es normal cuando llega otro aviso; el resto se registra
                    if (evento.error !== 'interrupted' && evento.error !== 'canceled') {
                        console.error('Accesibilidad: error de voz', evento.error);
                    }
                    resolver(false);
                };
                window.speechSynthesis.speak(frase);
            } catch (error) {
                console.error('Accesibilidad: no se pudo leer en voz alta', error);
                resolver(false);
            }
        });
    }

    // Los navegadores no dejan hablar hasta que el usuario toca la página: el primer toque "desbloquea" la voz
    function desbloquearVoz() {
        if (!hayVoz) return;
        try {
            const silencio = new SpeechSynthesisUtterance(' ');
            silencio.volume = 0;
            window.speechSynthesis.speak(silencio);
        } catch (error) {
            console.error('Accesibilidad: no se pudo preparar la voz', error);
        }
    }
    document.addEventListener('pointerdown', desbloquearVoz, { once: true });
    document.addEventListener('keydown', desbloquearVoz, { once: true });

    // ---------- Panel de ajustes ----------
    const panel = document.getElementById('ajustes-visualizacion');
    if (panel) {
        panel.querySelectorAll('input[name="letra"]').forEach((radio) => {
            radio.checked = radio.value === ajustes.letra;
            radio.addEventListener('change', () => {
                ajustes.letra = radio.value;
                aplicar();
                guardar();
            });
        });

        const casillas = { 'ajuste-contraste': 'contraste', 'ajuste-voz': 'voz', 'ajuste-animaciones': 'sinAnimaciones' };
        for (const [id, clave] of Object.entries(casillas)) {
            const casilla = document.getElementById(id);
            if (!casilla) continue;
            casilla.checked = ajustes[clave];
            casilla.addEventListener('change', () => {
                ajustes[clave] = casilla.checked;
                aplicar();
                guardar();
                if (clave === 'voz') {
                    if (casilla.checked) leer('Leeré los avisos en voz alta.');
                    else if (hayVoz) window.speechSynthesis.cancel();
                }
            });
        }

        const probar = document.getElementById('btn-probar-voz');
        const sinVoz = document.getElementById('aviso-sin-voz');
        if (!hayVoz) {
            if (probar) probar.hidden = true;
            if (sinVoz) sinVoz.hidden = false;
            const casillaVoz = document.getElementById('ajuste-voz');
            if (casillaVoz) casillaVoz.disabled = true;
        } else if (probar) {
            probar.addEventListener('click', () =>
                leer('Así sonarán tus avisos. Por ejemplo: es la hora de tu pastilla.', { forzar: true }));
        }
    }

    window.AppAccesibilidad = {
        leer,
        anunciar,
        vozActivada: () => hayVoz && ajustes.voz
    };
})();
