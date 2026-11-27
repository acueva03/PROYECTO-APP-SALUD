// Integración opcional con Capacitor. En navegador no hace nada.
(() => {
    const capacitor = window.Capacitor;
    const plugins = capacitor && capacitor.Plugins ? capacitor.Plugins : {};
    const app = plugins.App;
    const keepAwake = plugins.KeepAwake;

    if (!capacitor || !capacitor.isNativePlatform || !capacitor.isNativePlatform()) return;

    function aplicarRuta(url) {
        if (!url) return;
        try {
            const destino = new URL(url);
            const prefijo = destino.protocol === 'saludos:' && destino.hostname === 'vincular'
                ? '/vincular' : destino.pathname;
            const ruta = prefijo + destino.search + destino.hash;
            if (ruta.startsWith('/')) window.location.assign(ruta);
        } catch (e) {
            console.warn('[mobile] enlace nativo inválido');
        }
    }

    if (app && app.addListener) {
        app.addListener('appUrlOpen', ({ url }) => aplicarRuta(url));
        if (app.getLaunchUrl) app.getLaunchUrl().then(({ url }) => aplicarRuta(url));
        app.addListener('backButton', ({ canGoBack }) => {
            if (canGoBack) window.history.back();
            else if (app.minimizeApp) app.minimizeApp();
        });
    }

    const esPaciente = document.getElementById('boton-sos') || document.getElementById('form-alarma');
    if (esPaciente && keepAwake && keepAwake.keepAwake) {
        keepAwake.keepAwake().catch(() => {});
        window.addEventListener('pagehide', () => {
            if (keepAwake.allowSleep) keepAwake.allowSleep().catch(() => {});
        }, { once: true });
    }
})();
