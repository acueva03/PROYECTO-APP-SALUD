# App móvil Android (Capacitor)

La app es un WebView que carga el servidor Flask. No contiene copias de los HTML.
appId: `com.is1.appsalud`

## Requisitos
- Node 22 o superior (Capacitor 8)
- Android Studio (incluye JDK y SDK; aceptar licencias)
- Móvil Android con depuración USB, o un emulador

## Primera vez
```
cd mobile
npm install
```
`android/app/google-services.json` no está en el repositorio: pedírselo a P4 y copiarlo ahí.

## Ejecutar
1. Servidor Flask abierto a la red (desde `backend`):
   `python -m flask --app app run --host 0.0.0.0 --port 5000`
2. Elegir la URL del servidor (PowerShell) y sincronizar:
   - Emulador: no hace falta nada (usa `http://10.0.2.2:5000`)
   - Móvil real o cámara/QR por USB: `adb reverse tcp:5000 tcp:5000` y
     `$env:CAP_SERVER_URL="http://localhost:5000"`
   - Producción: `$env:CAP_SERVER_URL="https://<url-de-P1>"`
   - Después: `npm run sync`
3. `npx cap open android` y pulsar Run en Android Studio.

## Reglas del equipo
- Solo P3 edita `AndroidManifest.xml` y `build.gradle`. Si necesitas un permiso, pídelo en el chat.
- Cada plugin se instala en `mobile/` (`npm i ...`) y se ejecuta `npm run sync`.
- Nunca al repositorio: keystore (`*.jks`), `keystore.properties`, `local.properties`, `google-services.json`, `node_modules`.
- Los plugins se usan desde la web con `window.Capacitor.Plugins.<Nombre>` (la web se carga del servidor, no hay bundler).

## Diferencias con el navegador
(se rellena a medida que se detecten)