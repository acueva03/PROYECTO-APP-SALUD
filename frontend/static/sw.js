/* ==========================================================================
   SERVICE WORKER - SALUDOS PWA
   Estrategia de caché segura para salud:
   1. Nunca cachear /api/* ni llamadas no-GET (salud, SOS, sesión siempre en vivo).
   2. Navegación (HTML): Red primero (Network-First); si falla, página /offline.
   3. Estáticos (/static/*): Caché primero (Cache-First) con fallback a red.
   ========================================================================== */

const CACHE_VERSION = 'saludos-v1';
const OFFLINE_URL = '/offline';

const RECURSOS_ESTATICOS = [
    OFFLINE_URL,
    '/static/manifest.webmanifest',
    '/static/base.css',
    '/static/accesibilidad.css',
    '/static/accesibilidad.js',
    '/static/errores.js',
    '/static/pwa.js',
    '/static/img/logo.svg',
    '/static/img/iconos/icon-192.png',
    '/static/img/iconos/icon-512.png',
    '/static/img/iconos/icon-512-maskable.png'
];

// 1. INSTALACIÓN: Precarga de recursos estáticos críticos y activación inmediata
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_VERSION)
            .then((cache) => {
                return cache.addAll(RECURSOS_ESTATICOS);
            })
            .then(() => {
                return self.skipWaiting();
            })
            .catch((error) => {
                console.error('[ServiceWorker] Error durante la pre-carga en install:', error);
            })
    );
});

// 2. ACTIVACIÓN: Limpieza de versiones obsoletas de la caché
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys()
            .then((claves) => {
                return Promise.all(
                    claves.map((clave) => {
                        if (clave !== CACHE_VERSION) {
                            console.log('[ServiceWorker] Eliminando caché antigua:', clave);
                            return caches.delete(clave);
                        }
                        return Promise.resolve();
                    })
                );
            })
            .then(() => {
                return self.clients.claim();
            })
            .catch((error) => {
                console.error('[ServiceWorker] Error durante activate:', error);
            })
    );
});

// 3. FETCH: Gestión segura de peticiones
self.addEventListener('fetch', (event) => {
    const request = event.request;
    const url = new URL(request.url);

    // Solo gestionamos peticiones del mismo origen
    if (url.origin !== self.location.origin) {
        return;
    }

    // REGLA CRÍTICA DE SALUD: Nunca cachear peticiones a la API ni peticiones que no sean GET
    // Datos de salud, tomas, métricas, vinculación y botón SOS deben comunicarse en vivo siempre.
    if (request.method !== 'GET' || url.pathname.startsWith('/api/')) {
        return;
    }

    // NAVEGACIÓN (Páginas HTML): Network-First con fallback a la pantalla sin conexión
    if (request.mode === 'navigate') {
        event.respondWith(
            fetch(request)
                .catch((error) => {
                    console.warn('[ServiceWorker] Fallo de red en navegación hacia', url.pathname, error);
                    return caches.match(OFFLINE_URL).then((offlineResponse) => {
                        if (offlineResponse) {
                            return offlineResponse;
                        }
                        return new Response('Sin conexión a internet', {
                            status: 503,
                            statusText: 'Service Unavailable',
                            headers: { 'Content-Type': 'text/plain; charset=utf-8' }
                        });
                    });
                })
        );
        return;
    }

    // ARCHIVOS ESTÁTICOS (/static/*): Cache-First con fallback a la red
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(request).then((cachedResponse) => {
                if (cachedResponse) {
                    return cachedResponse;
                }
                return fetch(request).then((networkResponse) => {
                    if (networkResponse && networkResponse.status === 200) {
                        const responseToCache = networkResponse.clone();
                        caches.open(CACHE_VERSION).then((cache) => {
                            cache.put(request, responseToCache);
                        }).catch((err) => {
                            console.error('[ServiceWorker] Error al guardar estático en caché:', err);
                        });
                    }
                    return networkResponse;
                }).catch((error) => {
                    console.warn('[ServiceWorker] Fallo al obtener estático desde la red:', url.pathname, error);
                    throw error;
                });
            })
        );
    }
});
