"""Tests del check-in diario «Estoy bien» (P5 - Laura).
Ejecutar desde backend/:  python3 -m unittest test_checkin -v"""
from base_tests import BaseTest      # PRIMERO: fija DATABASE_URL en memoria antes de importar app
import os
from datetime import date, timedelta
from unittest.mock import patch

from app import app
from models import db, User, CheckIn, CheckinConfig, AvisoEnviado, hoy_madrid
from checkin_bp import procesar_checkins_perdidos


class BaseCheckin(BaseTest):
    """Sobre BaseTest (María paciente de Alberto) añade a Rosa (paciente de nadie)
    y a Lucía (supervisora sin pacientes)."""

    def setUp(self):
        super().setUp()
        self.rosa = self.crear('Rosa', 'rosa', 'dependiente')
        self.lucia = self.crear('Lucía', 'lucia', 'supervisor')

    def crear(self, nombre, username, rol):
        u = User(nombre=nombre, username=username, rol=rol)
        u.set_password('1234')
        db.session.add(u)
        db.session.commit()
        return u

    def cli(self, username):
        """Un cliente nuevo con la sesión de ese usuario (self.cliente solo guarda una sesión)."""
        c = app.test_client()
        c.post('/login', data={'username': username, 'password': '1234'})
        return c


# ---------------------------------------------------------------------------
# Hacer el check-in
# ---------------------------------------------------------------------------
class TestHacerCheckin(BaseCheckin):
    def test_hacer_checkin(self):
        r = self.cli('maria').post('/api/checkin', json={'estado_animo': 'Contento'})
        self.assertEqual(r.status_code, 201)
        self.assertFalse(r.get_json()['ya_hecho'])
        c = CheckIn.query.filter_by(user_id=self.maria.id).one()
        self.assertEqual(c.fecha, hoy_madrid().isoformat())     # fecha de Madrid, no la del sistema
        self.assertEqual(c.estado_animo, 'Contento')

    def test_sin_animo_tambien_vale(self):
        self.assertEqual(self.cli('maria').post('/api/checkin', json={}).status_code, 201)
        self.assertIsNone(CheckIn.query.one().estado_animo)

    def test_idempotente_no_duplica(self):
        c = self.cli('maria')
        self.assertEqual(c.post('/api/checkin', json={}).status_code, 201)
        r2 = c.post('/api/checkin', json={'estado_animo': 'Triste'})
        self.assertEqual(r2.status_code, 200)                   # ya lo había hecho hoy
        self.assertTrue(r2.get_json()['ya_hecho'])
        self.assertEqual(CheckIn.query.count(), 1)
        self.assertIsNone(CheckIn.query.one().estado_animo)     # el segundo intento no cambia nada

    def test_datos_malos_dan_400(self):
        c = self.cli('maria')
        for malo in ({'estado_animo': 'Eufórico'}, {'estado_animo': 5}, {'estado_animo': ['Contento']}):
            self.assertEqual(c.post('/api/checkin', json=malo).status_code, 400, malo)
        self.assertEqual(c.post('/api/checkin', json=[]).status_code, 400)
        self.assertEqual(CheckIn.query.count(), 0)

    def test_permisos(self):
        self.assertEqual(app.test_client().post('/api/checkin', json={}).status_code, 401)   # sin sesión
        self.assertEqual(self.cli('alberto').post('/api/checkin', json={}).status_code, 403)  # un supervisor no hace check-in
        self.assertEqual(CheckIn.query.count(), 0)

    def test_cada_paciente_tiene_el_suyo(self):
        self.cli('maria').post('/api/checkin', json={})
        r = self.cli('rosa').post('/api/checkin', json={})
        self.assertEqual(r.status_code, 201)                    # el de María no cuenta para Rosa
        self.assertEqual(CheckIn.query.count(), 2)


# ---------------------------------------------------------------------------
# Estado de hoy y configuración
# ---------------------------------------------------------------------------
class TestEstadoYConfig(BaseCheckin):
    def test_mi_checkin_antes_y_despues(self):
        c = self.cli('maria')
        antes = c.get('/api/mi-checkin').get_json()
        self.assertFalse(antes['hecho'])
        self.assertTrue(antes['activo'])
        self.assertEqual(antes['hora_limite'], '11:00')         # valor por defecto
        c.post('/api/checkin', json={'estado_animo': 'Tranquilo'})
        despues = c.get('/api/mi-checkin').get_json()
        self.assertTrue(despues['hecho'])
        self.assertEqual(despues['estado_animo'], 'Tranquilo')
        self.assertRegex(despues['hora'], r'^\d\d:\d\d$')

    def test_mi_checkin_permisos(self):
        self.assertEqual(app.test_client().get('/api/mi-checkin').status_code, 401)
        self.assertEqual(self.cli('alberto').get('/api/mi-checkin').status_code, 403)

    def test_guardar_config(self):
        c = self.cli('maria')
        r = c.put('/api/mi-checkin/config', json={'hora_limite': '10:30', 'activo': False})
        self.assertEqual(r.status_code, 200)
        datos = c.get('/api/mi-checkin').get_json()
        self.assertEqual(datos['hora_limite'], '10:30')
        self.assertFalse(datos['activo'])
        # Cambiar solo una cosa deja la otra como estaba, y no duplica la fila
        c.put('/api/mi-checkin/config', json={'activo': True})
        self.assertEqual(c.get('/api/mi-checkin').get_json()['hora_limite'], '10:30')
        self.assertEqual(CheckinConfig.query.filter_by(user_id=self.maria.id).count(), 1)

    def test_config_limites_exactos(self):
        c = self.cli('maria')
        for hora in ('08:00', '23:00'):
            self.assertEqual(c.put('/api/mi-checkin/config', json={'hora_limite': hora}).status_code, 200, hora)

    def test_config_valores_malos(self):
        c = self.cli('maria')
        malos = [{'hora_limite': '07:59'}, {'hora_limite': '23:01'}, {'hora_limite': '9:00'},
                 {'hora_limite': 'abc'}, {'hora_limite': '25:00'}, {'hora_limite': 1100},
                 {'activo': 'si'}, {'activo': 1}]
        for malo in malos:
            self.assertEqual(c.put('/api/mi-checkin/config', json=malo).status_code, 400, malo)
        self.assertEqual(c.put('/api/mi-checkin/config', json=[]).status_code, 400)
        self.assertEqual(c.get('/api/mi-checkin').get_json()['hora_limite'], '11:00')   # nada cambió

    def test_config_permisos(self):
        self.assertEqual(app.test_client().put('/api/mi-checkin/config', json={'activo': False}).status_code, 401)
        self.assertEqual(self.cli('alberto').put('/api/mi-checkin/config', json={'activo': False}).status_code, 403)


# ---------------------------------------------------------------------------
# Lo que ve el supervisor
# ---------------------------------------------------------------------------
class TestSupervisorCheckin(BaseCheckin):
    def url(self, paciente):
        return f'/api/supervisor/pacientes/{paciente.id}/checkin'

    def test_supervisor_ve_los_ultimos_14_dias(self):
        self.cli('maria').post('/api/checkin', json={'estado_animo': 'Cansado'})
        datos = self.cli('alberto').get(self.url(self.maria)).get_json()
        self.assertEqual(len(datos['dias']), 14)
        self.assertEqual(datos['dias'][-1]['fecha'], hoy_madrid().isoformat())   # el último día es hoy
        self.assertTrue(datos['dias'][-1]['hecho'])
        self.assertEqual(datos['dias'][-1]['estado_animo'], 'Cansado')
        self.assertFalse(datos['dias'][0]['hecho'])
        self.assertEqual(datos['estado_hoy'], 'HECHO')

    def test_estado_hoy_pendiente_y_no_realizado(self):
        c = self.cli('alberto')
        with patch('checkin_bp.hora_madrid', return_value='09:00'):
            self.assertEqual(c.get(self.url(self.maria)).get_json()['estado_hoy'], 'PENDIENTE')
        with patch('checkin_bp.hora_madrid', return_value='12:00'):
            self.assertEqual(c.get(self.url(self.maria)).get_json()['estado_hoy'], 'NO_REALIZADO')
        db.session.add(CheckinConfig(user_id=self.maria.id, hora_limite='11:00', activo=False))
        db.session.commit()
        with patch('checkin_bp.hora_madrid', return_value='12:00'):
            self.assertEqual(c.get(self.url(self.maria)).get_json()['estado_hoy'], 'DESACTIVADO')

    def test_no_ve_pacientes_ajenos(self):
        # Rosa no es paciente de Alberto; Lucía no supervisa a María; un id inexistente da lo mismo: 403
        self.assertEqual(self.cli('alberto').get(self.url(self.rosa)).status_code, 403)
        self.assertEqual(self.cli('lucia').get(self.url(self.maria)).status_code, 403)
        self.assertEqual(self.cli('alberto').get('/api/supervisor/pacientes/99999/checkin').status_code, 403)

    def test_sin_sesion_y_rol_incorrecto(self):
        self.assertEqual(app.test_client().get(self.url(self.maria)).status_code, 401)
        self.assertEqual(self.cli('maria').get(self.url(self.maria)).status_code, 403)

    def test_el_supervisor_no_puede_modificar(self):
        c = self.cli('alberto')
        for metodo in (c.post, c.put, c.patch, c.delete):
            self.assertEqual(metodo(self.url(self.maria), json={}).status_code, 405, metodo.__name__)
        self.assertEqual(CheckIn.query.count(), 0)


# ---------------------------------------------------------------------------
# Aviso al supervisor cuando no se hace el check-in
# ---------------------------------------------------------------------------
class TestAvisoCheckinPerdido(BaseCheckin):
    def avisar(self, hora):
        """Ejecuta el proceso como si fuera esa hora de Madrid. Devuelve (avisos, mock_de_envio)."""
        with patch('checkin_bp.hora_madrid', return_value=hora), \
             patch('checkin_bp.enviar_a_supervisores_de') as envio:
            return procesar_checkins_perdidos(), envio

    def test_no_avisa_antes_de_la_hora_limite(self):
        avisos, envio = self.avisar('10:59')
        self.assertEqual(avisos, 0)
        self.assertFalse(envio.called)

    def test_avisa_a_la_hora_limite_y_solo_una_vez(self):
        avisos, envio = self.avisar('11:00')
        self.assertEqual(avisos, 1)
        args, kwargs = envio.call_args
        self.assertEqual(kwargs['paciente_id'], self.maria.id)
        self.assertEqual(kwargs['tipo'], 'CHECKIN_PERDIDO')
        # El siguiente tick (un minuto después) NO vuelve a avisar
        avisos2, envio2 = self.avisar('11:01')
        self.assertEqual(avisos2, 0)
        self.assertFalse(envio2.called)
        self.assertEqual(AvisoEnviado.query.filter_by(tipo='CHECKIN_PERDIDO').count(), 1)

    def test_al_dia_siguiente_vuelve_a_avisar(self):
        self.avisar('12:00')
        manana = date.today() + timedelta(days=1)
        with patch('checkin_bp.hoy_madrid', return_value=manana):
            avisos, _ = self.avisar('12:00')
        self.assertEqual(avisos, 1)

    def test_sin_aviso_si_ya_hizo_el_checkin(self):
        self.cli('maria').post('/api/checkin', json={})
        avisos, envio = self.avisar('15:00')
        self.assertEqual(avisos, 0)
        self.assertFalse(envio.called)

    def test_sin_aviso_si_esta_desactivado(self):
        db.session.add(CheckinConfig(user_id=self.maria.id, hora_limite='11:00', activo=False))
        db.session.commit()
        avisos, envio = self.avisar('15:00')
        self.assertEqual(avisos, 0)
        self.assertFalse(envio.called)

    def test_respeta_la_hora_limite_personal(self):
        db.session.add(CheckinConfig(user_id=self.maria.id, hora_limite='09:00', activo=True))
        db.session.commit()
        self.assertEqual(self.avisar('08:59')[0], 0)
        self.assertEqual(self.avisar('09:00')[0], 1)

    def test_paciente_sin_supervisor_no_avisa(self):
        # Rosa no tiene supervisores: solo se avisa por María
        avisos, envio = self.avisar('15:00')
        self.assertEqual(avisos, 1)
        self.assertEqual(envio.call_args.kwargs['paciente_id'], self.maria.id)

    def test_el_tick_de_p4_incluye_los_avisos_de_checkin(self):
        os.environ['CRON_TOKEN'] = 'secreto-test-checkin'
        try:
            with patch('checkin_bp.hora_madrid', return_value='12:00'), \
                 patch('checkin_bp.enviar_a_supervisores_de'):
                r = self.cliente.post('/interno/tick', headers={'X-Cron-Token': 'secreto-test-checkin'})
        finally:
            os.environ.pop('CRON_TOKEN', None)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()['checkins_avisados'], 1)


if __name__ == '__main__':
    import unittest
    unittest.main()