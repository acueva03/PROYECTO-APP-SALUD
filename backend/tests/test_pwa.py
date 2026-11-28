import json
import os
import re
import tempfile
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'   # PRIMERO: fija DATABASE_URL en memoria antes de importar app

from base_tests import BaseTest
from app import app, _version_cache_estaticos


class TestPWA(BaseTest):
    """Pruebas de la funcionalidad PWA (2.6): manifest, service worker, cabeceras y modo offline."""

    def test_manifest_accesible_y_campos_obligatorios(self):
        """El archivo manifest.webmanifest existe, es JSON válido y contiene campos de PWA instalable."""
        respuesta = self.cliente.get('/static/manifest.webmanifest')
        self.assertEqual(respuesta.status_code, 200)

        datos = json.loads(respuesta.get_data(as_text=True))
        self.assertIn('name', datos)
        self.assertIn('short_name', datos)
        self.assertEqual(datos.get('display'), 'standalone')
        self.assertEqual(datos.get('start_url'), '/')
        self.assertIn('theme_color', datos)
        self.assertIn('background_color', datos)

        # Comprobar iconos obligatorios (192, 512 y maskable)
        iconos = datos.get('icons', [])
        self.assertGreaterEqual(len(iconos), 2)
        sizes = [i.get('sizes') for i in iconos]
        self.assertIn('192x192', sizes)
        self.assertIn('512x512', sizes)

        # Al menos un icono maskable
        purposes = [i.get('purpose') for i in iconos if 'purpose' in i]
        self.assertIn('maskable', purposes)

    def test_service_worker_servido_desde_raiz_con_cabeceras(self):
        """GET /sw.js debe servirse desde la raíz con Service-Worker-Allowed: / y Cache-Control: no-cache."""
        respuesta = self.cliente.get('/sw.js')
        self.assertEqual(respuesta.status_code, 200)

        # Cabeceras requeridas
        self.assertIn('javascript', respuesta.headers.get('Content-Type', ''))
        self.assertEqual(respuesta.headers.get('Service-Worker-Allowed'), '/')
        self.assertIn('no-cache', respuesta.headers.get('Cache-Control', ''))

        # Comprobar que incluye la regla crítica de nunca cachear /api/ y la versión de caché
        cuerpo = respuesta.get_data(as_text=True)
        self.assertIn('/api/', cuerpo)
        self.assertIn('CACHE_VERSION', cuerpo)
        self.assertRegex(cuerpo, r"const\s+CACHE_VERSION\s*=\s*'saludos-[0-9a-f]{12}';")
        self.assertIn('/offline', cuerpo)

    def test_cache_version_cambia_si_cambia_un_estatico(self):
        """El hash de CACHE_VERSION debe ser determinista y cambiar al modificarse un archivo estático."""
        with tempfile.TemporaryDirectory() as tmp:
            archivo = os.path.join(tmp, 'app.css')
            with open(archivo, 'w', encoding='utf-8') as f:
                f.write('body { color: black; }')
            v1 = _version_cache_estaticos(tmp)
            v1_rep = _version_cache_estaticos(tmp)
            self.assertEqual(v1, v1_rep)
            self.assertTrue(re.fullmatch(r'saludos-[0-9a-f]{12}', v1))

            with open(archivo, 'w', encoding='utf-8') as f:
                f.write('body { color: red; }')
            v2 = _version_cache_estaticos(tmp)
            self.assertNotEqual(v1, v2)

    def test_pagina_offline_disponible(self):
        """GET /offline devuelve 200, aviso accesible y botón SOS telefónico al 112."""
        respuesta = self.cliente.get('/offline')
        self.assertEqual(respuesta.status_code, 200)

        html = respuesta.get_data(as_text=True)
        self.assertIn('Sin conexión a internet', html)
        self.assertIn('tel:112', html)
        self.assertIn('Reintentar conexión', html)

    def test_base_html_incluye_metadatos_pwa_y_script(self):
        """Las pantallas que heredan de base.html incluyen meta theme-color, manifest y script pwa.js."""
        respuesta = self.cliente.get('/login')
        self.assertEqual(respuesta.status_code, 200)

        html = respuesta.get_data(as_text=True)
        self.assertIn('manifest.webmanifest', html)
        self.assertIn('name="theme-color"', html)
        self.assertIn('pwa.js', html)
        self.assertIn('apple-touch-icon', html)
