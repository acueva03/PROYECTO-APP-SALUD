/* ==========================================================================
   REGISTRO DEL SERVICE WORKER (PWA)
   Cumple la regla 3.18: sin catch vacíos, captura y registra errores adecuadamente.
   ========================================================================== */

(function registrarPwa() {
    'use strict';

    if (!('serviceWorker' in navigator)) {
        console.info('[PWA] Service Worker no soportado en este navegador.');
        return;
    }

    window.addEventListener('load', () => {
        try {
            navigator.serviceWorker.register('/sw.js', { scope: '/' })
                .then((registration) => {
                    console.log('[PWA] Service Worker registrado con éxito en ámbito:', registration.scope);
                })
                .catch((error) => {
                    console.error('[PWA] Error en el registro del Service Worker:', error);
                });
        } catch (error) {
            console.error('[PWA] Excepción no controlada al intentar registrar Service Worker:', error);
        }
    });
})();
