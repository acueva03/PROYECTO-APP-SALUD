import type { CapacitorConfig } from '@capacitor/cli';

// URL del servidor Flask. Por defecto, el PC visto desde el emulador de Android.
// Para un móvil real o la URL de producción: $env:CAP_SERVER_URL="https://..." antes de "npx cap sync".
const url = process.env.CAP_SERVER_URL || 'http://10.0.2.2:5000';

const config: CapacitorConfig = {
  appId: 'com.is1.appsalud',
  appName: 'App Salud',
  webDir: 'www',
  server: {
    url,
    cleartext: url.startsWith('http://'),        // solo se permite HTTP sin cifrar en desarrollo
    allowNavigation: [new URL(url).hostname],
  },
};

export default config;