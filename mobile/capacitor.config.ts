import type { CapacitorConfig } from '@capacitor/cli';

// URL del servidor Flask. Por defecto, el servidor de producción en Render.
// Para desarrollo local (emulador o móvil por USB): define CAP_SERVER_URL="http://10.0.2.2:5000" antes de "npm run sync".
const url = process.env.CAP_SERVER_URL || 'https://app-salud.onrender.com';

const config: CapacitorConfig = {
  appId: 'com.is1.appsalud',
  appName: 'SaludOS',
  webDir: 'www',
  server: {
    url,
    cleartext: url.startsWith('http://'),        // solo se permite HTTP sin cifrar en desarrollo
    allowNavigation: [new URL(url).hostname],
    errorPath: '/offline',                        // si el WebView no puede cargar, muestra la pantalla offline
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 1500,
      launchAutoHide: true,
      launchFadeOutDuration: 300,
      backgroundColor: '#F4F6F9',
      androidScaleType: 'CENTER_CROP',
      showSpinner: false,
    },
    StatusBar: {
      style: 'DARK',                             // texto oscuro sobre fondo claro
      backgroundColor: '#0F2C59',                 // color primario de la app
    },
  },
};

export default config;
