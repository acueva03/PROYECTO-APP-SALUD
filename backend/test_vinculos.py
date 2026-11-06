import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'   # ANTES de importar app: nunca se toca app_salud.db

import unittest
from datetime import timedelta, timezone
from app import app
from models import db, User, CodigoVinculo, IntentoVinculo, ahora
from vinculos import (ALFABETO, LONGITUD, generar_codigo, normalizar_codigo,
                      formato_valido, hash_codigo, formatear_codigo)


class TestVinculosLogica(unittest.TestCase):
    """Caja blanca: funciones puras, sin base de datos."""

    def test_codigo_longitud_y_alfabeto(self):
        for _ in range(200):
            c = generar_codigo()
            self.assertEqual(len(c), LONGITUD)
            self.assertTrue(set(c) <= set(ALFABETO))

    def test_sin_caracteres_ambiguos(self):
        for prohibido in '0O1I':
            self.assertNotIn(prohibido, ALFABETO)
        self.assertEqual(len(ALFABETO), 32)

    def test_codigos_distintos(self):
        self.assertEqual(len({generar_codigo() for _ in range(500)}), 500)

    def test_normalizar_y_formato(self):
        self.assertEqual(normalizar_codigo(' abcd-efgh '), 'ABCDEFGH')
        self.assertEqual(normalizar_codigo(None), '')
        self.assertEqual(normalizar_codigo(12345678), '')
        self.assertTrue(formato_valido('ABCDEFGH'))
        # Pruebas pensadas para que falle: corto, largo, caracteres ambiguos, minúsculas, espacios
        for mal in ['', 'ABCDEFG', 'ABCDEFGHJ', 'ABCDEFG0', 'ABCDEFGI', 'abcdefgh', 'ABCD EFGH']:
            self.assertFalse(formato_valido(mal), mal)

    def test_hash(self):
        h = hash_codigo('ABCDEFGH')
        self.assertEqual(len(h), 64)
        self.assertEqual(h, hash_codigo('ABCDEFGH'))
        self.assertNotEqual(h, hash_codigo('ABCDEFGJ'))
        self.assertNotIn('ABCDEFGH', h)

    def test_formatear(self):
        self.assertEqual(formatear_codigo('ABCDEFGH'), 'ABCD-EFGH')


class BaseConBD(unittest.TestCase):
    """Prepara una BD en memoria con un paciente (María) y dos supervisores (Alberto y Lucía)."""

    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()
        for nombre, username, rol in [('María', 'maria', 'dependiente'),
                                      ('Alberto', 'alberto', 'supervisor'),
                                      ('Lucía', 'lucia', 'supervisor')]:
            u = User(nombre=nombre, username=username, rol=rol)
            u.set_password('clave1234')
            db.session.add(u)
        db.session.commit()
        self.cli_maria = self.cliente('maria')
        self.cli_alberto = self.cliente('alberto')
        self.cli_lucia = self.cliente('lucia')

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def cliente(self, username):
        c = app.test_client()
        c.post('/login', data={'username': username, 'password': 'clave1234'})
        return c

    def dependientes_de(self, username):
        db.session.expire_all()
        return [u.username for u in User.query.filter_by(username=username).one().dependientes]


class TestVinculosApi(BaseConBD):
    """Caja negra: /api/vinculos/codigo y /api/vinculos/canjear."""

    def generar(self):
        r = self.cli_maria.post('/api/vinculos/codigo')
        self.assertEqual(r.status_code, 201)
        return r.get_json()

    def canjear(self, cliente, codigo):
        return cliente.post('/api/vinculos/canjear', json={'codigo': codigo})

    # ---- Generar ----
    def test_generar_codigo(self):
        d = self.generar()
        self.assertRegex(d['codigo'], r'^[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}$')
        self.assertIn('/vincular?c=' + d['codigo'].replace('-', ''), d['url'])
        self.assertEqual(d['minutos'], 10)
        # Si la librería qrcode no está instalada, qr es None y la app sigue funcionando
        self.assertTrue(d['qr'] is None or d['qr'].startswith('data:image/svg+xml;base64,'))

    def test_solo_se_guarda_el_hash(self):
        d = self.generar()
        plano = d['codigo'].replace('-', '')
        fila = CodigoVinculo.query.one()
        self.assertNotEqual(fila.codigo_hash, plano)
        self.assertEqual(fila.codigo_hash, hash_codigo(plano))
        self.assertFalse(fila.usado)
        duracion = fila.expira.replace(tzinfo=timezone.utc) - fila.creado.replace(tzinfo=timezone.utc)
        self.assertAlmostEqual(duracion.total_seconds(), 600, delta=5)

    def test_permisos_generar(self):
        self.assertEqual(app.test_client().post('/api/vinculos/codigo').status_code, 401)
        self.assertEqual(self.cli_alberto.post('/api/vinculos/codigo').status_code, 403)

    def test_nuevo_codigo_invalida_el_anterior(self):
        d1 = self.generar()
        d2 = self.generar()
        self.assertEqual(self.canjear(self.cli_alberto, d1['codigo']).status_code, 400)
        self.assertEqual(self.canjear(self.cli_alberto, d2['codigo']).status_code, 200)

    # ---- Canjear ----
    def test_canjear_correcto(self):
        d = self.generar()
        r = self.canjear(self.cli_alberto, d['codigo'])
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()['paciente']['nombre'], 'María')
        self.assertEqual(self.dependientes_de('alberto'), ['maria'])

    def test_canjear_admite_minusculas_y_espacios(self):
        d = self.generar()
        r = self.canjear(self.cli_alberto, ' ' + d['codigo'].lower() + ' ')
        self.assertEqual(r.status_code, 200)

    def test_supervisor_vinculado_ve_el_sos(self):
        d = self.generar()
        self.canjear(self.cli_alberto, d['codigo'])
        self.assertEqual(self.cli_maria.post('/api/sos', json={}).status_code, 201)
        alertas = self.cli_alberto.get('/api/mis-alertas').get_json()
        self.assertEqual(len(alertas), 1)
        # Lucía NO está vinculada: no ve nada
        self.assertEqual(self.cli_lucia.get('/api/mis-alertas').get_json(), [])

    def test_un_solo_uso(self):
        d = self.generar()
        self.assertEqual(self.canjear(self.cli_alberto, d['codigo']).status_code, 200)
        self.assertEqual(self.canjear(self.cli_lucia, d['codigo']).status_code, 400)
        self.assertEqual(self.dependientes_de('lucia'), [])

    def test_codigo_caducado(self):
        d = self.generar()
        fila = CodigoVinculo.query.one()
        fila.expira = ahora() - timedelta(minutes=1)
        db.session.commit()
        self.assertEqual(self.canjear(self.cli_alberto, d['codigo']).status_code, 400)
        self.assertEqual(self.dependientes_de('alberto'), [])

    def test_mensaje_de_error_generico(self):
        """Código inexistente, ya usado y caducado deben dar el MISMO mensaje."""
        d1 = self.generar()
        self.canjear(self.cli_lucia, d1['codigo'])                       # Lucía lo gasta
        msg_usado = self.canjear(self.cli_alberto, d1['codigo']).get_json()['error']

        d2 = self.generar()
        fila = CodigoVinculo.query.filter_by(codigo_hash=hash_codigo(d2['codigo'].replace('-', ''))).one()
        fila.expira = ahora() - timedelta(minutes=1)
        db.session.commit()
        msg_caducado = self.canjear(self.cli_alberto, d2['codigo']).get_json()['error']

        msg_inexistente = self.canjear(self.cli_alberto, 'ZZZZ-ZZZZ').get_json()['error']
        self.assertEqual(msg_usado, msg_caducado)
        self.assertEqual(msg_caducado, msg_inexistente)

    def test_roles_canjear(self):
        d = self.generar()
        self.assertEqual(app.test_client().post('/api/vinculos/canjear', json={'codigo': d['codigo']}).status_code, 401)
        self.assertEqual(self.canjear(self.cli_maria, d['codigo']).status_code, 403)

    def test_ya_vinculado_no_duplica(self):
        self.canjear(self.cli_alberto, self.generar()['codigo'])
        r = self.canjear(self.cli_alberto, self.generar()['codigo'])
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.dependientes_de('alberto'), ['maria'])

    def test_entrada_rara_no_rompe(self):
        for raro in [None, 123, [], {}, '', 'A' * 5000]:
            r = self.cli_alberto.post('/api/vinculos/canjear', json={'codigo': raro})
            self.assertIn(r.status_code, (400, 429))

    # ---- Fuerza bruta ----
    def test_bloqueo_tras_5_fallos(self):
        d = self.generar()
        for _ in range(5):
            self.assertEqual(self.canjear(self.cli_alberto, 'ZZZZ-ZZZZ').status_code, 400)
        # Con el bloqueo activo, ni el código CORRECTO funciona
        self.assertEqual(self.canjear(self.cli_alberto, d['codigo']).status_code, 429)
        self.assertEqual(self.dependientes_de('alberto'), [])
        # Lucía comparte IP con Alberto (en los tests, 127.0.0.1): también bloqueada
        self.assertEqual(self.canjear(self.cli_lucia, d['codigo']).status_code, 429)

    def test_fallos_antiguos_no_cuentan(self):
        alberto = User.query.filter_by(username='alberto').one()
        for _ in range(5):
            db.session.add(IntentoVinculo(user_id=alberto.id, ip='127.0.0.1',
                                          fecha=ahora() - timedelta(minutes=11)))
        db.session.commit()
        d = self.generar()
        self.assertEqual(self.canjear(self.cli_alberto, d['codigo']).status_code, 200)


class TestVinculosPaginas(BaseConBD):
    """Pantallas. Estas pruebas pasan cuando estén hechos los pasos 6 y 7."""

    def test_pagina_vincular_supervisor(self):
        r = self.cli_alberto.get('/vincular?c=ABCD-EFGH')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'ABCD-EFGH', r.data)           # el código viene rellenado

    def test_pagina_vincular_bloqueada(self):
        self.assertEqual(app.test_client().get('/vincular').status_code, 302)
        self.assertEqual(self.cli_maria.get('/vincular').status_code, 302)

    def test_codigo_en_la_url_no_inyecta_html(self):
        r = self.cli_alberto.get('/vincular?c=<script>alert(1)</script>')
        self.assertNotIn(b'<script>alert', r.data)

    def test_pantalla_paciente_tiene_el_boton(self):
        r = self.cli_maria.get('/')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'btn-generar-codigo', r.data)


if __name__ == '__main__':
    unittest.main()