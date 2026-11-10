from base_tests import BaseTest      # primero: fija DATABASE_URL en memoria antes de importar app
import unittest
from app import app
from models import db, User, MedicalProfile
from ficha import validar_ficha

DATOS_OK = {
    'edad': 78, 'altura': 160.5, 'telefono': '600 000 000', 'grupo_sanguineo': 'a+',
    'alergias': ' Penicilina ', 'enfermedades_cronicas': 'Hipertensión', 'medicacion': 'Enalapril 5 mg',
    'contacto_emergencia_nombre': 'Alberto', 'contacto_emergencia_telefono': '+34 600 000 001',
}


class TestValidarFicha(unittest.TestCase):
    """Caja blanca: función pura, sin base de datos."""

    def test_normaliza(self):
        limpio, error = validar_ficha({'edad': '', 'altura': '170,5', 'grupo_sanguineo': 'o-', 'alergias': '  Nueces '})
        self.assertIsNone(error)
        self.assertIsNone(limpio['edad'])                 # vacío = sin rellenar
        self.assertEqual(limpio['altura'], 170.5)         # admite coma decimal
        self.assertEqual(limpio['grupo_sanguineo'], 'O-')
        self.assertEqual(limpio['alergias'], 'Nueces')
        self.assertIsNone(limpio['medicacion'])           # lo que no llega queda a None

    def test_rechaza_valores_malos(self):
        # Pruebas pensadas para que falle: límites, tipos raros, texto demasiado largo...
        malos = [
            {'edad': 121}, {'edad': -1}, {'edad': 'abc'}, {'edad': True}, {'edad': 12.5}, {'edad': [1]},
            {'altura': 49}, {'altura': 251}, {'altura': 'nan'}, {'altura': 'inf'},
            {'grupo_sanguineo': 'Z+'}, {'grupo_sanguineo': 5},
            {'telefono': 'abc'}, {'telefono': '1' * 21}, {'contacto_emergencia_telefono': '12'},
            {'alergias': 'a' * 501}, {'alergias': 123}, {'contacto_emergencia_nombre': 'a' * 121},
        ]
        for datos in malos:
            limpio, error = validar_ficha(datos)
            self.assertIsNone(limpio, datos)
            self.assertIsNotNone(error, datos)

    def test_no_es_un_diccionario(self):
        for raro in (None, [], 'texto', 5):
            self.assertIsNotNone(validar_ficha(raro)[1], repr(raro))

    def test_limites_exactos_validos(self):
        for datos in ({'edad': 0}, {'edad': 120}, {'altura': 50}, {'altura': 250}, {'alergias': 'a' * 500}):
            self.assertIsNone(validar_ficha(datos)[1], datos)


class TestFichaApi(BaseTest):
    """Caja negra: /api/mi-ficha."""

    def setUp(self):
        super().setUp()
        self.login('maria')

    def recargar_maria(self):
        db.session.expire_all()
        return db.session.get(User, self.maria.id)

    def test_guardar_y_leer(self):
        self.assertEqual(self.cliente.put('/api/mi-ficha', json=DATOS_OK).status_code, 200)
        f = self.cliente.get('/api/mi-ficha').get_json()
        self.assertEqual(f['edad'], 78)
        self.assertEqual(f['altura'], 160.5)
        self.assertEqual(f['grupo_sanguineo'], 'A+')          # en mayúsculas
        self.assertEqual(f['alergias'], 'Penicilina')         # sin espacios sobrantes
        # Lo guardado aparece en "Mis datos" y en la vista del supervisor
        s = self.cliente.get('/api/mi-salud').get_json()
        self.assertEqual(s['edad'], 78)
        self.assertEqual(s['contacto_emergencia'], 'Alberto (+34 600 000 001)')
        self.assertEqual(self.recargar_maria().telefono, '600 000 000')

    def test_actualizar_no_duplica_la_ficha(self):
        self.cliente.put('/api/mi-ficha', json=DATOS_OK)
        self.cliente.put('/api/mi-ficha', json={**DATOS_OK, 'alergias': 'Ninguna'})
        self.assertEqual(MedicalProfile.query.filter_by(user_id=self.maria.id).count(), 1)
        self.assertEqual(self.cliente.get('/api/mi-ficha').get_json()['alergias'], 'Ninguna')

    def test_vaciar_un_campo_lo_borra(self):
        self.cliente.put('/api/mi-ficha', json=DATOS_OK)
        self.cliente.put('/api/mi-ficha', json={**DATOS_OK, 'alergias': '', 'edad': ''})
        f = self.cliente.get('/api/mi-ficha').get_json()
        self.assertIsNone(f['alergias'])
        self.assertIsNone(f['edad'])

    def test_datos_malos_dan_400_y_no_cambian_nada(self):
        self.cliente.put('/api/mi-ficha', json=DATOS_OK)
        for malo in ({**DATOS_OK, 'edad': 200}, {**DATOS_OK, 'grupo_sanguineo': 'Z+'},
                     {**DATOS_OK, 'telefono': 'abc'}, {**DATOS_OK, 'alergias': 'a' * 501}):
            self.assertEqual(self.cliente.put('/api/mi-ficha', json=malo).status_code, 400, malo)
        self.assertEqual(self.recargar_maria().edad, 78)      # sigue lo que se guardó antes
        # Un cuerpo que no es un objeto JSON tampoco debe borrar la ficha
        self.assertEqual(self.cliente.put('/api/mi-ficha', json=[]).status_code, 400)
        self.assertEqual(self.cliente.put('/api/mi-ficha', data='no es json', content_type='text/plain').status_code, 400)
        self.assertEqual(self.cliente.get('/api/mi-ficha').get_json()['alergias'], 'Penicilina')

    def test_permisos(self):
        anonimo = app.test_client()
        self.assertEqual(anonimo.get('/api/mi-ficha').status_code, 401)
        self.assertEqual(anonimo.put('/api/mi-ficha', json=DATOS_OK).status_code, 401)
        sup = app.test_client()
        sup.post('/login', data={'username': 'alberto', 'password': '1234'})
        self.assertEqual(sup.get('/api/mi-ficha').status_code, 403)
        self.assertEqual(sup.put('/api/mi-ficha', json=DATOS_OK).status_code, 403)
        self.assertIsNone(self.recargar_maria().edad)          # el supervisor no pudo tocar nada

    def test_pantalla_del_paciente_tiene_el_formulario(self):
        r = self.cliente.get('/')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'form-ficha', r.data)


if __name__ == '__main__':
    unittest.main()
