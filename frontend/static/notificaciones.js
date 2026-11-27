// Integración de Notificaciones Push con Capacitor (P4 - Andrés)
// Solo se ejecuta en dispositivos móviles reales (plataforma nativa de Capacitor).
(() => {
    const capacitor = window.Capacitor;
    if (!capacitor || !capacitor.isNativePlatform || !capacitor.isNativePlatform()) {
        return; // En navegador web estándar no hace nada
    }

    const plugins = capacitor.Plugins || {};
    const push = plugins.PushNotifications;

    if (!push) {
        console.warn('[Push] Plugin PushNotifications no disponible en Plugins.');
        return;
    }

    // Guardar el token actual para poder desregistrarlo al cerrar sesión
    let tokenRegistrado = null;

    async function crearCanalesAndroid() {
        try {
            if (push.createChannel) {
                // Canal SOS de máxima prioridad (importancia 5, sonido y vibración fuerte)
                await push.createChannel({
                    id: 'sos',
                    name: 'Alertas de emergencia SOS',
                    description: 'Alertas críticas cuando un paciente solicita ayuda urgente',
                    importance: 5,
                    sound: 'alarma.mp3',
                    visibility: 1,
                    vibration: true
                });

                // Canal para avisos generales (importancia 3)
                await push.createChannel({
                    id: 'avisos',
                    name: 'Avisos y recordatorios',
                    description: 'Avisos de tomas pendientes y check-in diario',
                    importance: 3,
                    sound: 'default',
                    visibility: 1,
                    vibration: true
                });
                console.log('[Push] Canales Android creados correctamente.');
            }
        } catch (err) {
            console.error('[Push] Error al crear canales de notificación:', err);
        }
    }

    async function enviarTokenAlServidor(token) {
        try {
            const resp = await fetch('/api/dispositivos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: token, plataforma: 'android' })
            });
            if (resp.ok) {
                tokenRegistrado = token;
                console.log('[Push] Dispositivo registrado con éxito en el servidor.');
            } else {
                console.warn('[Push] Error al registrar dispositivo:', resp.status);
            }
        } catch (err) {
            console.error('[Push] Fallo de red al enviar token push:', err);
        }
    }

    async function desregistrarDispositivo() {
        if (!tokenRegistrado) return;
        try {
            await fetch('/api/dispositivos', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: tokenRegistrado })
            });
            console.log('[Push] Dispositivo desregistrado del servidor.');
        } catch (err) {
            console.error('[Push] Error al desregistrar token en logout:', err);
        }
    }

    async function inicializarPush() {
        try {
            await crearCanalesAndroid();

            // Comprobar y pedir permisos (Android 13+ exige POST_NOTIFICATIONS)
            let estadoPermiso = await push.checkPermissions();
            if (estadoPermiso.receive !== 'granted') {
                estadoPermiso = await push.requestPermissions();
            }

            if (estadoPermiso.receive === 'granted') {
                await push.register();
            } else {
                console.warn('[Push] Permiso de notificaciones denegado por el usuario.');
            }
        } catch (err) {
            console.error('[Push] Error en la inicialización de notificaciones:', err);
        }
    }

    // Listener cuando se obtiene el token FCM
    push.addListener('registration', (token) => {
        if (token && token.value) {
            enviarTokenAlServidor(token.value);
        }
    });

    push.addListener('registrationError', (error) => {
        console.error('[Push] Error al registrar con FCM:', error);
    });

    // Listener cuando llega una notificación con la app en primer plano
    push.addListener('pushNotificationReceived', (notification) => {
        console.log('[Push] Notificación recibida en primer plano:', notification);
        const titulo = notification.title || 'Aviso';
        const cuerpo = notification.body || '';

        // Si existe errores.js o accesibilidad, mostrar mensaje accesible
        if (window.mostrarMensaje) {
            window.mostrarMensaje(`${titulo}: ${cuerpo}`, 'info');
        } else if (window.AppAccesibilidad && window.AppAccesibilidad.leer) {
            window.AppAccesibilidad.leer(`${titulo}. ${cuerpo}`);
        }
    });

    // Listener cuando el usuario toca la notificación
    push.addListener('pushNotificationActionPerformed', (action) => {
        const data = (action.notification && action.notification.data) || {};
        console.log('[Push] Notificación pulsada por el usuario. Datos:', data);

        const tipo = data.tipo;
        if (tipo === 'SOS' || tipo === 'TOMA_SIN_CONFIRMAR' || tipo === 'CHECKIN_PERDIDO' || tipo === 'ALARMA_NO_SONO') {
            window.location.assign('/supervisor');
        } else if (tipo === 'SOS_ATENDIDO') {
            window.location.assign('/paciente');
        }
    });

    // Desregistrar al pulsar cerrar sesión
    document.addEventListener('DOMContentLoaded', () => {
        const enlacesLogout = document.querySelectorAll('a[href*="/logout"], .enlace-salir');
        enlacesLogout.forEach((enlace) => {
            enlace.addEventListener('click', (e) => {
                desregistrarDispositivo();
            });
        });
    });

    // Arrancar el flujo
    inicializarPush();
})();
