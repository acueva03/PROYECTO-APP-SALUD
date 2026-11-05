import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'   # ANTES de importar app: así nunca se toca app_salud.db

import unittest
from app import app, rellenar_usernames
from models import db, User
from validaciones import (validar_username, validar_password,
                          username_desde_nombre, normalizar_username)


class TestValidaciones(unittest.TestCase):
    """Caja blanca: funciones puras, sin base de datos."""

    def test_username_valido(self):
        for ok in ['ana', 'juan.perez', 'maria_97', 'a-b-c', 'a' * 30]:
            self.assertIsNone(validar_username(ok), ok)

    def test_username_invalido(self):
        # Pruebas pensadas para que el código falle: límites, mayúsculas, espacios, salto de línea...
        for mal in ['', 'ab', 'a' * 31, 'Ana', 'ana perez', 'ana\n', 'ñandú', 'ana@x.com', None]:
            self.assertIsNotNone(validar_username(mal), repr(mal))

    def test_password_valida(self):
        for ok in ['abcdefg1', 'Clave1234', 'a1' * 64]:
            self.assertIsNone(validar_password(ok), ok)

    def test_password_invalida(self):
        for mal in ['', 'abc1', 'abcdefgh', '12345678', None, 'a1' * 65]:
            self.assertIsNotNone(validar_password(mal), repr(mal))

    def test_normalizar_y_username_desde_nombre(self):
        self.assertEqual(normalizar_username('  PeDrO '), 'pedro')
        self.assertEqual(username_desde_nombre('María'), 'maria')
        self.assertEqual(username_desde_nombre('José Luis'), 'joseluis')
        self.assertEqual(username_desde_nombre('!!!'), 'usuario')


class TestRegistro(unittest.TestCase):
    """Caja negra: rutas /registro y /login."""

    def setUp(self):
        app.config['TESTING'] = True
        self.cliente = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def datos(self, **cambios):
        d = {'nombre': 'Pedro', 'apellidos': 'Gil', 'username': 'pedro',
             'password': 'clave1234', 'password2': 'clave1234', 'rol': 'dependiente'}
        d.update(cambios)
        return d

    def test_registro_correcto(self):
        r = self.cliente.post('/registro', data=self.datos())
        self.assertEqual(r.status_code, 302)
        u = User.query.filter_by(username='pedro').first()
        self.assertIsNotNone(u)
        self.assertEqual(u.rol, 'dependiente')
        self.assertNotEqual(u.password_hash, 'clave1234')      # nunca en texto plano
        self.assertTrue(u.check_password('clave1234'))

    def test_dos_pedros_no_se_mezclan(self):
        self.cliente.post('/registro', data=self.datos())
        otro = app.test_client()
        r = otro.post('/registro', data=self.datos(username='pedro2', password='otraClave99', password2='otraClave99'))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(User.query.filter_by(nombre='Pedro').count(), 2)

        tercero = app.test_client()
        tercero.post('/login', data={'username': 'pedro2', 'password': 'otraClave99'})
        with tercero.session_transaction() as s:
            self.assertEqual(s['user_id'], User.query.filter_by(username='pedro2').first().id)

    def test_username_duplicado_incluso_con_mayusculas(self):
        self.cliente.post('/registro', data=self.datos())
        r = app.test_client().post('/registro', data=self.datos(username='PEDRO'))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(User.query.count(), 1)

    def test_registro_rechazos(self):
        casos = [
            self.datos(password2='distinta1234'),                 # contraseñas distintas
            self.datos(password='corta1', password2='corta1'),    # contraseña débil
            self.datos(username='ab'),                            # usuario demasiado corto
            self.datos(nombre='   '),                             # nombre vacío
            self.datos(rol='admin'),                              # rol inventado
        ]
        for datos in casos:
            r = app.test_client().post('/registro', data=datos)
            self.assertEqual(r.status_code, 400, datos)
        self.assertEqual(User.query.count(), 0)

    def test_supervisor_nuevo_no_ve_ningun_dato(self):
        """Principio del PDF: crear una cuenta de supervisor no da acceso a ningún dato."""
        self.cliente.post('/registro', data=self.datos(username='sup1', rol='supervisor'))
        self.assertEqual(self.cliente.get('/api/mis-alertas').get_json(), [])
        self.assertEqual(self.cliente.get('/api/mis-tomas-supervisadas').get_json(), [])

    def test_login_por_username(self):
        self.cliente.post('/registro', data=self.datos())
        c = app.test_client()
        self.assertEqual(c.post('/login', data={'username': 'PEDRO', 'password': 'clave1234'}).status_code, 302)
        self.assertEqual(app.test_client().post('/login', data={'username': 'pedro', 'password': 'mala'}).status_code, 401)
        self.assertEqual(app.test_client().post('/login', data={'username': 'nadie', 'password': 'clave1234'}).status_code, 401)

    def test_migracion_usernames_antiguos(self):
        db.session.add_all([User(nombre='Pedro', rol='dependiente'),
                            User(nombre='Pedro', rol='supervisor'),
                            User(nombre='Al', rol='dependiente')])
        db.session.commit()
        rellenar_usernames()
        nombres = [u.username for u in User.query.all()]
        self.assertEqual(len(set(nombres)), 3)               # ninguno repetido
        self.assertTrue(all(len(n) >= 3 for n in nombres))


if __name__ == '__main__':
    unittest.main()