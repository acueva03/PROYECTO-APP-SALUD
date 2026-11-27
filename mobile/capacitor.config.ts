import type { CapacitorConfig } from '@capacitor/cli';

// URL del servidor Flask. Por defecto, el PC visto desde el emulador de Android.
// Para un móvil real o la URL de producción: $env:CAP_SERVER_URL="https://..." antes de "npx cap sync".
const url = process.env.CAP_SERVER_URL || 'http://10.0.2.2:5000';

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
