// reloj.js (riesgo 3.13): avisa si el reloj del móvil difiere más de 5 minutos del del servidor.
// Compensa el tiempo de ida y vuelta de la petición para no dar falsos avisos con mala cobertura.
(() => {
    const UMBRAL_MS = 5 * 60 * 1000;
    const REVISAR_CADA_MS = 5 * 60 * 1000;
    const aviso = document.getElementById('aviso-reloj');
    if (!aviso) return;
 
    async function comprobar() {
        const controller = new AbortController();
        const t = setTimeout(() => controller.abort(), 4000);
        try {
            const t0 = Date.now();
            const r = await fetch('/api/hora', { cache: 'no-store', signal: controller.signal });
            const t1 = Date.now();
            if (!r.ok) throw new Error('HTTP ' + r.status);
            const datos = await r.json();
            const servidorMs = new Date(datos.ahora_utc).getTime();
            const diferenciaMs = (t0 + t1) / 2 - servidorMs;          // >0: el móvil va adelantado
            if (Math.abs(diferenciaMs) > UMBRAL_MS) {
                const min = Math.round(Math.abs(diferenciaMs) / 60000);
                aviso.textContent = '⚠ El reloj de tu móvil va ' + min + ' minutos ' +
                    (diferenciaMs > 0 ? 'adelantado' : 'atrasado') +
                    '. Las alarmas pueden sonar a otra hora. Revisa la fecha y la hora en los ajustes del móvil.';
                aviso.hidden = false;
            } else {
                aviso.hidden = true;
            }
        } catch (e) {
            // Sin conexión no se sabe nada: se deja el aviso como estaba (no avisamos en falso)
            console.error('[reloj] no se pudo comparar la hora con el servidor', e);              // 3.18
        } finally {
            clearTimeout(t);
        }
    }
 
    comprobar();
    setInterval(comprobar, REVISAR_CADA_MS);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) comprobar(); });
})();