from base_tests import BaseTest      # PRIMERO: fija DATABASE_URL en memoria antes de importar app
from app import app
from models import db, User, Alarm, AlertSOS, RegistroToma, ahora, hoy_madrid


class BaseMulti(BaseTest):
    """Sobre BaseTest (María paciente de Alberto) añade:
    Pedro (segundo paciente de Alberto), Rosa (paciente de nadie) y Lucía (supervisora sin pacientes)."""

    def setUp(self):
        super().setUp()
        self.pedro = self.crear('Pedro', 'pedro', 'dependiente')
        self.rosa = self.crear('Rosa', 'rosa', 'dependiente')
        self.lucia = self.crear('Lucía', 'lucia', 'supervisor')
        self.alberto.dependientes.append(self.pedro)
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

    def sos(self, paciente):
        alerta = AlertSOS(user_id=paciente.id)
        db.session.add(alerta)
        db.session.commit()
        return alerta


class TestListaPacientes(BaseMulti):
    def test_lista_varios_pacientes(self):
        datos = self.cli('alberto').get('/api/supervisor/pacientes').get_json()
        self.assertEqual(sorted(p['nombre'] for p in datos), ['María', 'Pedro'])
        for p in datos:
            self.assertEqual(p['estado'], 'OK')
            self.assertFalse(p['sos_activo'])
            self.assertEqual(p['tomas_pendientes'], 0)
            self.assertIsNone(p['ultima_toma'])

    def test_paciente_con_sos_sale_primero(self):
        self.sos(self.pedro)
        datos = self.cli('alberto').get('/api/supervisor/pacientes').get_json()
        self.assertEqual(datos[0]['nombre'], 'Pedro')
        self.assertTrue(datos[0]['sos_activo'])
        self.assertEqual(datos[0]['estado'], 'SOS')
        self.assertFalse(datos[1]['sos_activo'])

    def test_tomas_pendientes_y_ultima_toma_por_paciente(self):
        alarma = Alarm(user_id=self.maria.id, titulo='P', hora='08:00', fecha=hoy_madrid().isoformat())
        db.session.add(alarma)
        db.session.commit()
        comunes = dict(alarma_id=alarma.id, user_id=self.maria.id, titulo='P',
                       fecha_prevista=hoy_madrid().isoformat(), hora_prevista='08:00')
        db.session.add_all([RegistroToma(estado='PENDIENTE', **comunes),
                            RegistroToma(estado='PENDIENTE', **comunes),
                            RegistroToma(estado='CONFIRMADA', confirmada_en=ahora(), **comunes)])
        db.session.commit()
        datos = {p['nombre']: p for p in self.cli('alberto').get('/api/supervisor/pacientes').get_json()}
        self.assertEqual(datos['María']['tomas_pendientes'], 2)
        self.assertIsNotNone(datos['María']['ultima_toma'])
        self.assertEqual(datos['Pedro']['tomas_pendientes'], 0)    # las tomas de María no se mezclan


class TestPermisos(BaseMulti):
    def test_no_ve_pacientes_ajenos(self):
        self.assertEqual(self.cli('lucia').get('/api/supervisor/pacientes').get_json(), [])
        nombres = [p['nombre'] for p in self.cli('alberto').get('/api/supervisor/pacientes').get_json()]
        self.assertNotIn('Rosa', nombres)

    def test_listado_exige_sesion_de_supervisor(self):
        self.assertEqual(app.test_client().get('/api/supervisor/pacientes').status_code, 401)
        self.assertEqual(self.cli('maria').get('/api/supervisor/pacientes').status_code, 403)

    def test_endpoints_por_paciente(self):
        for parte in ('alertas', 'medicacion'):
            url = '/api/supervisor/pacientes/{}/' + parte
            # propios: los dos pacientes de Alberto
            self.assertEqual(self.cli('alberto').get(url.format(self.maria.id)).status_code, 200, parte)
            self.assertEqual(self.cli('alberto').get(url.format(self.pedro.id)).status_code, 200, parte)
            # ajenos o inexistentes: siempre 403
            self.assertEqual(self.cli('alberto').get(url.format(self.rosa.id)).status_code, 403, parte)
            self.assertEqual(self.cli('lucia').get(url.format(self.maria.id)).status_code, 403, parte)
            self.assertEqual(self.cli('alberto').get(url.format(99999)).status_code, 403, parte)
            # sin sesión y con rol incorrecto
            self.assertEqual(app.test_client().get(url.format(self.maria.id)).status_code, 401, parte)
            self.assertEqual(self.cli('maria').get(url.format(self.maria.id)).status_code, 403, parte)

    def test_no_atiende_alertas_ajenas(self):
        alerta = self.sos(self.maria)
        url = f'/api/alertas/{alerta.id}/atender'
        self.assertEqual(self.cli('lucia').post(url).status_code, 403)
        db.session.expire_all()
        self.assertEqual(db.session.get(AlertSOS, alerta.id).estado, 'ACTIVA')
        self.assertEqual(self.cli('alberto').post(url).status_code, 200)


class TestAlertasVariosPacientes(BaseMulti):
    def test_mis_alertas_trae_los_dos_sos_con_dependiente_id(self):
        self.sos(self.maria)
        self.sos(self.pedro)
        alertas = self.cli('alberto').get('/api/mis-alertas').get_json()
        self.assertEqual(sorted(a['dependiente_id'] for a in alertas),
                         sorted([self.maria.id, self.pedro.id]))

    def test_atender_uno_no_apaga_el_otro(self):
        a_maria = self.sos(self.maria)
        self.sos(self.pedro)
        c = self.cli('alberto')
        self.assertEqual(c.post(f'/api/alertas/{a_maria.id}/atender').status_code, 200)
        restantes = c.get('/api/mis-alertas').get_json()
        self.assertEqual([a['dependiente_id'] for a in restantes], [self.pedro.id])

    def test_tomas_supervisadas_trae_dependiente_id(self):
        alarma = Alarm(user_id=self.pedro.id, titulo='P', hora='08:00', fecha=hoy_madrid().isoformat())
        db.session.add(alarma)
        db.session.commit()
        db.session.add(RegistroToma(alarma_id=alarma.id, user_id=self.pedro.id, titulo='P',
                                    fecha_prevista=hoy_madrid().isoformat(), hora_prevista='08:00'))
        db.session.commit()
        tomas = self.cli('alberto').get('/api/mis-tomas-supervisadas').get_json()
        self.assertEqual([t['dependiente_id'] for t in tomas], [self.pedro.id])


if __name__ == '__main__':
    import unittest
    unittest.main()