import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'   # ANTES de importar app: nunca se toca app_salud.db

import unittest
from datetime import timedelta
from app import app
from models import db, User, IntentoLogin, ahora


class BaseSesion(unittest.TestCase):
    """BD en memoria con dos usuarios: pedro y ana (contraseña clave1234)."""

    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()
        for nombre, username in [('Pedro', 'pedro'), ('Ana', 'ana')]:
            u = User(nombre=nombre, username=username, rol='dependiente')
            u.set_password('clave1234')
            db.session.add(u)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self, cliente, username='pedro', password='clave1234'):
        return cliente.post('/login', data={'username': username, 'password': password})

    def fallar(self, cliente, veces, username='pedro'):
        for _ in range(veces):
            self.assertEqual(self.login(cliente, username, 'mala1234').status_code, 401)

    def cookie(self, respuesta):
        return ' '.join(respuesta.headers.getlist('Set-Cookie'))


class TestRiesgo315(BaseSesion):
    """Riesgo 3.15: clave secreta, cookie segura y bloqueo de fuerza bruta en el login."""

    def test_secret_key_no_esta_en_el_codigo(self):
        clave = app.config['SECRET_KEY']
        self.assertNotEqual(clave, 'clave_super_secreta_cambiar_en_produccion')
        self.assertGreaterEqual(len(clave), 32)

    def test_cookie_httponly_y_samesite(self):
        c = app.test_client()
        cookie = self.cookie(self.login(c))
        self.assertIn('HttpOnly', cookie)
        self.assertIn('SameSite=Lax', cookie)

    def test_bloqueo_tras_5_fallos_de_login(self):
        c = app.test_client()
        self.fallar(c, 5)
        # Con el bloqueo activo, ni la contraseña CORRECTA entra
        r = self.login(c)
        self.assertEqual(r.status_code, 429)
        self.assertIn(b'Demasiados intentos', r.data)
        with c.session_transaction() as s:
            self.assertNotIn('user_id', s)

    def test_bloqueo_afecta_solo_al_usuario_que_falla(self):
        c = app.test_client()
        self.fallar(c, 5, 'pedro')
        # Ana, desde la misma IP, entra sin problema
        self.assertEqual(self.login(app.test_client(), 'ana').status_code, 302)

    def test_usuario_inexistente_tambien_se_bloquea(self):
        """Mismo comportamiento que con un usuario real: no se revela quién tiene cuenta."""
        c = app.test_client()
        self.fallar(c, 5, 'nadie')
        self.assertEqual(self.login(c, 'nadie', 'clave1234').status_code, 429)

    def test_fallos_antiguos_no_cuentan(self):
        for _ in range(5):
            db.session.add(IntentoLogin(username='pedro', ip='127.0.0.1', fecha=ahora() - timedelta(minutes=11)))
        db.session.commit()
        self.assertEqual(self.login(app.test_client()).status_code, 302)

    def test_login_correcto_pone_el_contador_a_cero(self):
        c = app.test_client()
        self.fallar(c, 3)
        self.assertEqual(self.login(c).status_code, 302)
        self.assertEqual(IntentoLogin.query.count(), 0)


class TestRiesgo317(BaseSesion):
    """Riesgo 3.17: la sesión dura 30 días (que no se cierre sola en el móvil de un mayor)."""

    def test_duracion_configurada_30_dias(self):
        self.assertEqual(app.config['PERMANENT_SESSION_LIFETIME'], timedelta(days=30))

    def test_login_crea_sesion_permanente(self):
        c = app.test_client()
        self.assertIn('Expires=', self.cookie(self.login(c)))     # sin Expires, la cookie muere al cerrar el navegador
        with c.session_transaction() as s:
            self.assertTrue(s.permanent)

    def test_registro_tambien_crea_sesion_permanente(self):
        r = app.test_client().post('/registro', data={
            'nombre': 'Luis', 'username': 'luis', 'password': 'clave1234',
            'password2': 'clave1234', 'rol': 'dependiente'})
        self.assertEqual(r.status_code, 302)
        self.assertIn('Expires=', self.cookie(r))


if __name__ == '__main__':
    unittest.main()