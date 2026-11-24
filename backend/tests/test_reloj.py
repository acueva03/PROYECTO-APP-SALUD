import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'   # ANTES de importar app: nunca se toca app_salud.db
 
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo
 
from app import app
from models import db, User, Alarm, hoy_madrid
 
 
class TestRelojRiesgo313(unittest.TestCase):
    """Riesgo 3.13: el servidor manda con la hora de Madrid y no se fía del reloj del móvil."""
 
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()
        maria = User(nombre='María', username='maria', rol='dependiente')
        maria.set_password('clave1234')
        db.session.add(maria)
        db.session.commit()
        self.maria = maria
        self.cliente = app.test_client()
        self.cliente.post('/login', data={'username': 'maria', 'password': 'clave1234'})
 
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
 
    # ---- Caja blanca ----
    def test_hoy_madrid_usa_la_zona_de_madrid(self):
        self.assertEqual(hoy_madrid(), datetime.now(ZoneInfo('Europe/Madrid')).date())
 
    # ---- /api/hora ----
    def test_api_hora(self):
        r = app.test_client().get('/api/hora')      # no necesita sesión
        self.assertEqual(r.status_code, 200)
        datos = r.get_json()
        momento = datetime.fromisoformat(datos['ahora_utc'])
        self.assertIsNotNone(momento.tzinfo)         # con zona horaria, no "ingenua"
        self.assertAlmostEqual(momento.timestamp(), datetime.now().timestamp(), delta=5)
        self.assertEqual(datos['zona'], 'Europe/Madrid')
        self.assertEqual(datos['fecha'], hoy_madrid().isoformat())
        self.assertRegex(datos['hora'], r'^\d\d:\d\d$')
 
    # ---- /api/alarmas/<id>/sonada: fecha_local absurda ----
    def sonar(self, alarma, fecha_local):
        return self.cliente.post(f'/api/alarmas/{alarma.id}/sonada', json={
            'fecha_local': fecha_local, 'hora_local': '08:00', 'fecha_prevista': alarma.fecha})
 
    def test_sonada_rechaza_fecha_local_con_mas_de_un_dia_de_diferencia(self):
        alarma = Alarm(user_id=self.maria.id, titulo='Pastilla', hora='08:00',
                       fecha=hoy_madrid().isoformat(), activa=True)
        db.session.add(alarma)
        db.session.commit()
        hoy = hoy_madrid()
        # Pruebas pensadas para que falle: móvil con la fecha muy adelantada o muy atrasada
        for dias in (5, -2, 400):
            r = self.sonar(alarma, (hoy + timedelta(days=dias)).isoformat())
            self.assertEqual(r.status_code, 400, dias)
        # Hasta un día de diferencia se tolera (cambio de día entre móvil y servidor)
        for dias in (0, -1, 1):
            self.assertEqual(self.sonar(alarma, (hoy + timedelta(days=dias)).isoformat()).status_code, 200, dias)
 
    # ---- Las validaciones de fecha usan el día de Madrid, no el del sistema ----
    def test_peso_no_admite_fecha_futura_segun_madrid(self):
        with patch('app.hoy_madrid', return_value=date(2026, 10, 25)):
            r = self.cliente.post('/api/mi-peso', json={'kg': 65, 'fecha': '2026-10-26'})
            self.assertEqual(r.status_code, 400)
            r = self.cliente.post('/api/mi-peso', json={'kg': 65, 'fecha': '2026-10-25'})
            self.assertEqual(r.status_code, 201)
 
    def test_alarma_en_el_pasado_segun_madrid(self):
        with patch('app.hoy_madrid', return_value=date(2026, 10, 25)):
            r = self.cliente.post('/api/alarmas', json={'titulo': 'Pastilla', 'fecha': '2026-10-22', 'hora': '10:00'})
            self.assertEqual(r.status_code, 400)
            r = self.cliente.post('/api/alarmas', json={'titulo': 'Pastilla', 'fecha': '2026-10-24', 'hora': '10:00'})
            self.assertEqual(r.status_code, 201)
 
 
if __name__ == '__main__':
    unittest.main()
 