from datetime import date, timedelta
from base_tests import BaseTest
from app import primera_fecha_valida, siguiente_fecha, tomas_pendientes_de
from models import db, User, Alarm, AlertSOS, RegistroToma, ahora

HOY = lambda: date.today().isoformat()


class TestPermisos(BaseTest):
    def test_atender_alerta_permisos(self):
        otro = User(nombre='Otro', username='otro', rol='supervisor')
        otro.set_password('1234')
        alerta = AlertSOS(user_id=self.maria.id)
        db.session.add_all([otro, alerta])
        db.session.commit()
        url = f'/api/alertas/{alerta.id}/atender'

        self.assertEqual(self.cliente.post(url).status_code, 401)
        self.login('maria')
        self.assertEqual(self.cliente.post(url).status_code, 403)
        self.login('otro')
        self.assertEqual(self.cliente.post(url).status_code, 403)
        db.session.expire_all()
        self.assertEqual(db.session.get(AlertSOS, alerta.id).estado, 'ACTIVA')

        self.login('alberto')
        self.assertEqual(self.cliente.post('/api/alertas/9999/atender').status_code, 404)
        self.assertEqual(self.cliente.post(url).status_code, 200)
        db.session.expire_all()
        self.assertEqual(db.session.get(AlertSOS, alerta.id).estado, 'ATENDIDA')

    def test_alarma_ajena_403(self):
        alarma = Alarm(user_id=self.alberto.id, titulo='X', hora='09:00', fecha=HOY(), activa=True)
        db.session.add(alarma)
        db.session.commit()
        base = f'/api/alarmas/{alarma.id}'

        self.assertEqual(self.cliente.delete(base).status_code, 401)
        self.login('maria')
        self.assertEqual(self.cliente.patch(base + '/estado', json={'activa': False}).status_code, 403)
        self.assertEqual(self.cliente.delete(base).status_code, 403)
        self.assertEqual(self.cliente.post(base + '/sonada', json={}).status_code, 403)
        db.session.expire_all()
        self.assertTrue(db.session.get(Alarm, alarma.id).activa)


class TestSalud(BaseTest):
    def test_mi_salud(self):
        self.assertEqual(self.cliente.get('/api/mi-salud').status_code, 401)
        self.login('alberto')
        self.assertEqual(self.cliente.get('/api/mi-salud').status_code, 403)

        self.maria.peso, self.maria.altura = 60, 160
        db.session.commit()
        self.login('maria')
        datos = self.cliente.get('/api/mi-salud').get_json()
        self.assertEqual(datos['imc'], 23.4)
        self.assertIsNone(datos['grupo_sanguineo'])

        self.maria.altura = 1.6
        db.session.commit()
        self.assertEqual(self.cliente.get('/api/mi-salud').get_json()['imc'], 23.4)

    def test_historial_tomas(self):
        alarma = Alarm(user_id=self.maria.id, titulo='P', hora='08:00', fecha=HOY())
        db.session.add(alarma)
        db.session.commit()
        antigua = (date.today() - timedelta(days=40)).isoformat()
        for f in (HOY(), antigua):
            db.session.add(RegistroToma(alarma_id=alarma.id, user_id=self.maria.id, titulo='P',
                                        fecha_prevista=f, hora_prevista='08:00', estado='CONFIRMADA'))
        db.session.commit()

        self.login('maria')
        self.assertEqual(len(self.cliente.get('/api/mi-historial-tomas?dias=30').get_json()), 1)
        self.assertEqual(len(self.cliente.get('/api/mi-historial-tomas?dias=365').get_json()), 2)
        self.assertEqual(len(self.cliente.get('/api/mi-historial-tomas?dias=-5').get_json()), 1)
        self.assertEqual(self.cliente.get('/api/mi-historial-tomas?dias=abc').status_code, 200)


class TestTomasPendientes(BaseTest):
    def crear_toma(self, horas_atras, estado='PENDIENTE'):
        db.session.add(RegistroToma(alarma_id=1, user_id=self.maria.id, titulo='P',
                                    fecha_prevista=HOY(), hora_prevista='08:00',
                                    estado=estado, creado=ahora() - timedelta(hours=horas_atras)))

    def test_ventanas_de_6_y_24_horas(self):
        self.crear_toma(1)
        self.crear_toma(7)
        self.crear_toma(25)
        self.crear_toma(1, estado='CONFIRMADA')
        db.session.commit()

        self.assertEqual(len(tomas_pendientes_de(self.maria.id, 6)), 1)
        self.assertEqual(len(tomas_pendientes_de(self.maria.id, 24)), 2)

        self.login('maria')
        self.assertEqual(len(self.cliente.get('/api/mis-tomas-pendientes').get_json()), 1)
        self.login('alberto')
        self.assertEqual(len(self.cliente.get('/api/mis-tomas-supervisadas').get_json()), 2)


class TestFechas(BaseTest):
    LUN_A_VIE = [0, 1, 2, 3, 4]

    def test_primera_fecha_valida(self):
        self.assertEqual(primera_fecha_valida('2026-11-07', self.LUN_A_VIE), '2026-11-09')
        self.assertEqual(primera_fecha_valida('2026-11-08', self.LUN_A_VIE), '2026-11-09')
        self.assertEqual(primera_fecha_valida('2026-11-06', self.LUN_A_VIE), '2026-11-06')
        self.assertEqual(primera_fecha_valida('2026-11-07', []), '2026-11-07')

    def test_siguiente_fecha(self):
        self.assertEqual(siguiente_fecha('2026-11-06', '09:00', '09:00', self.LUN_A_VIE), '2026-11-09')
        self.assertEqual(siguiente_fecha('2026-11-08', '10:00', '09:00', self.LUN_A_VIE), '2026-11-09')
        self.assertEqual(siguiente_fecha('2026-11-06', '08:00', '09:00', self.LUN_A_VIE), '2026-11-06')

    def test_cambio_de_hora_octubre(self):
        self.assertEqual(siguiente_fecha('2026-10-24', '10:00', '09:00'), '2026-10-25')
        self.assertEqual(siguiente_fecha('2026-10-25', '10:00', '09:00'), '2026-10-26')


class TestSOSyLimites(BaseTest):
    def test_sos_duplicado_devuelve_200(self):
        self.login('maria')
        self.assertEqual(self.cliente.post('/api/sos', json={}).status_code, 201)
        self.assertEqual(self.cliente.post('/api/sos', json={}).status_code, 200)
        self.assertEqual(AlertSOS.query.count(), 1)

    def test_hora_y_fecha_limite(self):
        self.login('maria')
        manana = (date.today() + timedelta(days=1)).isoformat()

        def crear(**kw):
            d = {'titulo': 'P', 'fecha': manana, 'hora': '10:00'}
            d.update(kw)
            return self.cliente.post('/api/alarmas', json=d).status_code

        self.assertEqual(crear(hora='00:00'), 201)
        self.assertEqual(crear(hora='23:59'), 201)
        self.assertEqual(crear(hora='24:00'), 400)
        self.assertEqual(crear(hora='7:5'), 400)
        self.assertEqual(crear(fecha='2030-02-30'), 400)
        self.assertEqual(crear(titulo='   '), 400)
        ayer = (date.today() - timedelta(days=1)).isoformat()
        anteayer = (date.today() - timedelta(days=2)).isoformat()
        self.assertEqual(crear(fecha=ayer), 201)
        self.assertEqual(crear(fecha=anteayer), 400)

    def test_dos_alarmas_misma_hora(self):
        a1 = Alarm(user_id=self.maria.id, titulo='Pastilla A', hora='08:00', fecha=HOY(), dosis='5 mg')
        a2 = Alarm(user_id=self.maria.id, titulo='Pastilla B', hora='08:00', fecha=HOY(), dosis='10 mg')
        db.session.add_all([a1, a2])
        db.session.commit()
        self.login('maria')
        cuerpo = {'fecha_local': HOY(), 'hora_local': '08:00', 'fecha_prevista': HOY()}
        r1 = self.cliente.post(f'/api/alarmas/{a1.id}/sonada', json=cuerpo).get_json()
        r2 = self.cliente.post(f'/api/alarmas/{a2.id}/sonada', json=cuerpo).get_json()
        self.assertNotEqual(r1['registro_id'], r2['registro_id'])
        self.assertEqual(RegistroToma.query.count(), 2)
        r1b = self.cliente.post(f'/api/alarmas/{a1.id}/sonada', json=cuerpo).get_json()
        self.assertEqual(r1b['registro_id'], r1['registro_id'])
        self.assertEqual(RegistroToma.query.count(), 2)


if __name__ == '__main__':
    import unittest
    unittest.main()