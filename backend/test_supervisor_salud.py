from base_tests import BaseTest      # primero: fija DATABASE_URL en memoria antes de importar app
from app import app
from models import db, User, MedicalProfile, PesoRegistro, RegistroToma, Alarm, hoy_madrid


class BaseSalud(BaseTest):
    """Sobre BaseTest (María paciente, Alberto su supervisor) añade a Pedro (paciente sin supervisor),
    a Lucía (supervisora sin pacientes) y datos de salud de María y de Pedro."""

    def setUp(self):
        super().setUp()
        self.pedro = self.crear('Pedro', 'pedro', 'dependiente')
        self.lucia = self.crear('Lucía', 'lucia', 'supervisor')

        self.maria.edad = 78
        self.maria.altura = 160.0
        for fecha, kg in [('2026-09-01', 64.0), ('2026-10-20', 62.0)]:
            db.session.add(PesoRegistro(user_id=self.maria.id, fecha=fecha, kg=kg))
        db.session.add(PesoRegistro(user_id=self.pedro.id, fecha='2026-10-01', kg=80.0))
        db.session.add(MedicalProfile(user_id=self.maria.id, alergias='Penicilina'))
        alarma = Alarm(user_id=self.maria.id, titulo='Pastilla', hora='08:00', fecha=hoy_madrid().isoformat())
        db.session.add(alarma)
        db.session.commit()
        for estado in ('CONFIRMADA', 'PENDIENTE'):
            db.session.add(RegistroToma(alarma_id=alarma.id, user_id=self.maria.id, titulo='Pastilla',
                                        fecha_prevista=hoy_madrid().isoformat(), hora_prevista='08:00',
                                        estado=estado, dosis='500 mg'))
        db.session.commit()

    def crear(self, nombre, username, rol):
        u = User(nombre=nombre, username=username, rol=rol)
        u.set_password('1234')
        db.session.add(u)
        db.session.commit()
        return u

    def cli(self, username):
        """Un cliente nuevo con la sesión de ese usuario (self.cliente solo sirve para uno)."""
        c = app.test_client()
        c.post('/login', data={'username': username, 'password': '1234'})
        return c


class TestEndpointsSupervisor(BaseSalud):
    def test_supervisor_vinculado_ve_los_datos_de_su_paciente(self):
        base = f'/api/supervisor/pacientes/{self.maria.id}'
        c = self.cli('alberto')
        pesos = c.get(base + '/peso').get_json()
        self.assertEqual([p['kg'] for p in pesos], [64.0, 62.0])          # solo los de María, en orden
        tomas = c.get(base + '/tomas?dias=30').get_json()
        self.assertEqual(sorted(t['estado'] for t in tomas), ['CONFIRMADA', 'PENDIENTE'])
        salud = c.get(base + '/salud').get_json()
        self.assertEqual(salud['edad'], 78)
        self.assertEqual(salud['alergias'], 'Penicilina')

    def test_no_ve_pacientes_ajenos(self):
        for parte in ('peso', 'tomas', 'salud'):
            # Alberto no supervisa a Pedro; Lucía no supervisa a María; un id inexistente da lo mismo
            self.assertEqual(self.cli('alberto').get(f'/api/supervisor/pacientes/{self.pedro.id}/{parte}').status_code, 403, parte)
            self.assertEqual(self.cli('lucia').get(f'/api/supervisor/pacientes/{self.maria.id}/{parte}').status_code, 403, parte)
            self.assertEqual(self.cli('alberto').get(f'/api/supervisor/pacientes/99999/{parte}').status_code, 403, parte)

    def test_sin_sesion_y_rol_incorrecto(self):
        url = f'/api/supervisor/pacientes/{self.maria.id}/salud'
        self.assertEqual(app.test_client().get(url).status_code, 401)
        self.assertEqual(self.cli('maria').get(url).status_code, 403)       # un paciente no es supervisor

    def test_el_supervisor_no_puede_modificar(self):
        c = self.cli('alberto')
        for parte in ('peso', 'tomas', 'salud'):
            url = f'/api/supervisor/pacientes/{self.maria.id}/{parte}'
            for metodo in (c.post, c.put, c.patch, c.delete):
                self.assertEqual(metodo(url, json={'kg': 50}).status_code, 405, (parte, metodo.__name__))
        self.assertEqual(PesoRegistro.query.filter_by(user_id=self.maria.id).count(), 2)

    def test_dias_raros_no_rompen(self):
        c = self.cli('alberto')
        for dias in ('abc', '0', '-5', '99999'):
            r = c.get(f'/api/supervisor/pacientes/{self.maria.id}/tomas?dias={dias}')
            self.assertEqual(r.status_code, 200, dias)


class TestPantallas(BaseSalud):
    def test_pagina_de_salud_del_supervisor(self):
        r = self.cli('alberto').get(f'/supervisor/salud/{self.maria.id}')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'seccion-salud-supervisor', r.data)
        self.assertIn(f'data-paciente-id="{self.maria.id}"'.encode(), r.data)

    def test_pagina_bloqueada_para_otros(self):
        url = f'/supervisor/salud/{self.maria.id}'
        self.assertEqual(app.test_client().get(url).status_code, 302)                 # sin sesión
        self.assertEqual(self.cli('maria').get(url).status_code, 302)                 # un paciente
        self.assertEqual(self.cli('lucia').get(url).status_code, 302)                 # supervisora no vinculada
        self.assertEqual(self.cli('alberto').get('/supervisor/salud/99999').status_code, 302)

    def test_pantalla_del_paciente_ya_no_tiene_graficos(self):
        r = self.cli('maria').get('/')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b'grafico-peso', r.data)
        self.assertNotIn(b'grafico-tomas', r.data)
        self.assertNotIn(b'lista-historial', r.data)
        self.assertIn(b'data-campo="peso"', r.data)       # los datos de arriba siguen
        self.assertIn(b'form-peso', r.data)               # y se puede registrar el peso

    def test_panel_del_supervisor_tiene_el_enlace(self):
        r = self.cli('alberto').get('/supervisor')
        self.assertIn(f'/supervisor/salud/{self.maria.id}'.encode(), r.data)

    def test_mi_salud_sigue_igual_tras_refactorizar(self):
        s = self.cli('maria').get('/api/mi-salud').get_json()
        self.assertEqual(s['edad'], 78)
        self.assertEqual(s['alergias'], 'Penicilina')


if __name__ == '__main__':
    import unittest
    unittest.main()
