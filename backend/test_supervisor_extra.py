# test_supervisor_extra.py  (ARCHIVO NUEVO)
# Escenarios de "supervisor con varios pacientes" que NO cubren test_supervisor_multi.py ni test_seguridad.py:
#   orden del resumen, ventana de 24 h, límite del historial, flujo real de vincular/desvincular
#   con código, un paciente con dos supervisores y la página del panel.
from datetime import timedelta

from base_tests import BaseTest      # PRIMERO: fija DATABASE_URL en memoria antes de importar app
import unittest
from app import app
from models import db, User, Alarm, AlertSOS, RegistroToma, ahora, hoy_madrid


class BaseExtra(BaseTest):
    """Sobre BaseTest (María paciente de Alberto) añade a Lucía, supervisora sin pacientes."""

    def setUp(self):
        super().setUp()
        self.lucia = self.crear('Lucía', 'lucia', 'supervisor')

    def crear(self, nombre, username, rol):
        u = User(nombre=nombre, username=username, rol=rol)
        u.set_password('1234')
        db.session.add(u)
        db.session.commit()
        return u

    def paciente_de(self, supervisor, nombre, username):
        """Crea un paciente y lo vincula a ese supervisor."""
        p = self.crear(nombre, username, 'dependiente')
        supervisor.dependientes.append(p)
        db.session.commit()
        return p

    def cli(self, username):
        c = app.test_client()
        c.post('/login', data={'username': username, 'password': '1234'})
        return c

    def sos(self, paciente):
        alerta = AlertSOS(user_id=paciente.id)
        db.session.add(alerta)
        db.session.commit()
        return alerta

    def nombres(self, username):
        return [p['nombre'] for p in self.cli(username).get('/api/supervisor/pacientes').get_json()]


# ---------------------------------------------------------------------------
# Orden y tamaño del resumen
# ---------------------------------------------------------------------------
class TestOrdenYTamano(BaseExtra):
    def test_orden_alfabetico_en_espanol(self):
        """Sin SOS, el resumen va por orden alfabético como un diccionario: sin distinguir mayúsculas
        ni tildes, y con la Ñ entre la N y la O (antes 'Álvaro' y 'Óscar' acababan al final)."""
        for nombre, user in [('Óscar', 'oscar'), ('beatriz', 'beatriz'), ('Álvaro', 'alvaro'),
                             ('Ñandú', 'nandu'), ('Carmen', 'carmen'), ('Olga', 'olga'), ('Nuria', 'nuria')]:
            self.paciente_de(self.alberto, nombre, user)
        esperado = ['Álvaro', 'beatriz', 'Carmen', 'María', 'Nuria', 'Ñandú', 'Olga', 'Óscar']
        self.assertEqual(self.nombres('alberto'), esperado)

    def test_las_pestanas_siguen_el_mismo_orden(self):
        a = self.paciente_de(self.alberto, 'Álvaro', 'alvaro')
        z = self.paciente_de(self.alberto, 'Zoe', 'zoe')
        html = self.cli('alberto').get('/supervisor').get_data(as_text=True)
        pos = lambda p: html.index(f'data-vista="paciente-{p.id}"')
        self.assertLess(pos(a), pos(self.maria))
        self.assertLess(pos(self.maria), pos(z))

    def test_veinticinco_pacientes(self):
        ultimo = None
        for i in range(25):
            ultimo = self.paciente_de(self.alberto, 'Paciente%02d' % i, 'pac%02d' % i)
        self.sos(ultimo)
        datos = self.cli('alberto').get('/api/supervisor/pacientes').get_json()
        self.assertEqual(len(datos), 26)                                  # los 25 + María
        self.assertEqual(datos[0]['nombre'], 'Paciente24')                # el del SOS, el primero
        self.assertEqual(sum(1 for p in datos if p['sos_activo']), 1)
        self.assertEqual(len({p['id'] for p in datos}), 26)               # ninguno repetido


# ---------------------------------------------------------------------------
# Ventanas de tiempo y límites
# ---------------------------------------------------------------------------
class TestVentanasYLimites(BaseExtra):
    def test_tomas_pendientes_solo_de_las_ultimas_24_horas(self):
        alarma = Alarm(user_id=self.maria.id, titulo='P', hora='08:00', fecha=hoy_madrid().isoformat())
        db.session.add(alarma)
        db.session.commit()
        for horas in (1, 23, 25, 72):
            db.session.add(RegistroToma(alarma_id=alarma.id, user_id=self.maria.id, titulo='T%d' % horas,
                                        fecha_prevista=hoy_madrid().isoformat(), hora_prevista='08:00',
                                        estado='PENDIENTE', creado=ahora() - timedelta(hours=horas)))
        db.session.commit()
        a = self.cli('alberto')
        resumen = a.get('/api/supervisor/pacientes').get_json()
        self.assertEqual(resumen[0]['tomas_pendientes'], 2)               # solo las de 1 h y 23 h
        medicacion = a.get(f'/api/supervisor/pacientes/{self.maria.id}/medicacion').get_json()
        self.assertEqual(sorted(t['titulo'] for t in medicacion['tomas_pendientes']), ['T1', 'T23'])

    def test_historial_de_alertas_maximo_10_y_las_mas_recientes_primero(self):
        for i in range(12):
            db.session.add(AlertSOS(user_id=self.maria.id, fecha_hora=ahora() - timedelta(minutes=i),
                                    estado='ACTIVA' if i == 0 else 'ATENDIDA'))
        db.session.commit()
        alertas = self.cli('alberto').get(f'/api/supervisor/pacientes/{self.maria.id}/alertas').get_json()
        self.assertEqual(len(alertas), 10)
        self.assertEqual(alertas[0]['estado'], 'ACTIVA')                  # la más reciente, primero
        fechas = [a['fecha_hora'] for a in alertas]
        self.assertEqual(fechas, sorted(fechas, reverse=True))

    def test_atender_devuelve_al_paciente_a_estado_ok(self):
        alerta = self.sos(self.maria)
        a = self.cli('alberto')
        self.assertEqual(a.get('/api/supervisor/pacientes').get_json()[0]['estado'], 'SOS')
        a.post(f'/api/alertas/{alerta.id}/atender')
        resumen = a.get('/api/supervisor/pacientes').get_json()[0]
        self.assertEqual((resumen['estado'], resumen['sos_activo']), ('OK', False))
        historial = a.get(f'/api/supervisor/pacientes/{self.maria.id}/alertas').get_json()
        self.assertEqual([x['estado'] for x in historial], ['ATENDIDA'])

    def test_alarmas_de_cada_paciente_ordenadas_y_sin_mezclar(self):
        pedro = self.paciente_de(self.alberto, 'Pedro', 'pedro')
        hoy = hoy_madrid().isoformat()
        db.session.add_all([
            Alarm(user_id=self.maria.id, titulo='Tarde', hora='09:00', fecha=hoy, es_repetitiva=True,
                  dias_semana='4,0,2', activa=True),
            Alarm(user_id=self.maria.id, titulo='Apagada', hora='07:00', fecha=hoy, activa=False),
            Alarm(user_id=self.maria.id, titulo='Temprano', hora='08:00', fecha=hoy, activa=True),
            Alarm(user_id=pedro.id, titulo='DePedro', hora='06:00', fecha=hoy, activa=True)])
        db.session.commit()
        datos = self.cli('alberto').get(f'/api/supervisor/pacientes/{self.maria.id}/medicacion').get_json()
        self.assertEqual([a['titulo'] for a in datos['alarmas']], ['Temprano', 'Tarde', 'Apagada'])  # activas primero, por hora
        self.assertEqual(datos['alarmas'][1]['dias'], [0, 2, 4])                                    # '4,0,2' -> ordenado
        self.assertNotIn('DePedro', [a['titulo'] for a in datos['alarmas']])


# ---------------------------------------------------------------------------
# Flujo real de vincular y desvincular
# ---------------------------------------------------------------------------
class TestVincularYDesvincular(BaseExtra):
    def test_un_paciente_nuevo_entra_al_panel_al_canjear_su_codigo(self):
        pedro = self.crear('Pedro', 'pedro', 'dependiente')
        self.assertEqual(self.nombres('alberto'), ['María'])
        codigo = self.cli('pedro').post('/api/vinculos/codigo').get_json()['codigo']
        self.assertEqual(self.cli('alberto').post('/api/vinculos/canjear', json={'codigo': codigo}).status_code, 200)
        self.assertEqual(self.nombres('alberto'), ['María', 'Pedro'])
        self.sos(pedro)                                                  # y sus SOS ya le llegan
        self.assertEqual([a['dependiente'] for a in self.cli('alberto').get('/api/mis-alertas').get_json()], ['Pedro'])

    def test_el_paciente_quita_a_su_supervisor_y_el_otro_paciente_sigue(self):
        pedro = self.paciente_de(self.alberto, 'Pedro', 'pedro')
        r = self.cli('maria').delete(f'/api/vinculos/supervisores/{self.alberto.id}')
        self.assertEqual(r.status_code, 200)
        db.session.expire_all()
        a = self.cli('alberto')
        self.assertEqual(self.nombres('alberto'), ['Pedro'])
        self.assertEqual(a.get(f'/api/supervisor/pacientes/{self.maria.id}/alertas').status_code, 403)
        self.assertEqual(a.get(f'/api/supervisor/pacientes/{pedro.id}/alertas').status_code, 200)

    def test_el_supervisor_se_desvincula_de_uno_y_conserva_el_otro(self):
        pedro = self.paciente_de(self.alberto, 'Pedro', 'pedro')
        sos_maria, sos_pedro = self.sos(self.maria), self.sos(pedro)
        a = self.cli('alberto')
        self.assertEqual(a.delete(f'/api/vinculos/pacientes/{self.maria.id}').status_code, 200)
        db.session.expire_all()
        self.assertEqual(self.nombres('alberto'), ['Pedro'])
        self.assertEqual([x['dependiente_id'] for x in a.get('/api/mis-alertas').get_json()], [pedro.id])
        self.assertEqual(a.post(f'/api/alertas/{sos_maria.id}/atender').status_code, 403)   # ya no es suyo
        self.assertEqual(a.post(f'/api/alertas/{sos_pedro.id}/atender').status_code, 200)

    def test_desvincular_a_alguien_que_no_es_tuyo_no_cambia_nada(self):
        pedro = self.paciente_de(self.lucia, 'Pedro', 'pedro')
        r = self.cli('alberto').delete(f'/api/vinculos/pacientes/{pedro.id}')
        self.assertLess(r.status_code, 500)
        self.assertNotEqual(r.status_code, 200)
        db.session.expire_all()
        self.assertEqual(self.nombres('lucia'), ['Pedro'])               # Lucía sigue con su paciente


# ---------------------------------------------------------------------------
# Un paciente con varios supervisores
# ---------------------------------------------------------------------------
class TestVariosSupervisores(BaseExtra):
    def test_el_sos_llega_a_los_dos_y_atenderlo_lo_apaga_para_ambos(self):
        self.lucia.dependientes.append(self.maria)                       # María: supervisada por Alberto y Lucía
        db.session.commit()
        alerta = self.sos(self.maria)
        a, l = self.cli('alberto'), self.cli('lucia')
        self.assertEqual(len(a.get('/api/mis-alertas').get_json()), 1)
        self.assertEqual(len(l.get('/api/mis-alertas').get_json()), 1)
        self.assertEqual(l.post(f'/api/alertas/{alerta.id}/atender').status_code, 200)
        self.assertEqual(a.get('/api/mis-alertas').get_json(), [])       # a Alberto también se le apaga
        self.assertEqual(a.get('/api/supervisor/pacientes').get_json()[0]['estado'], 'OK')


# ---------------------------------------------------------------------------
# Página del panel
# ---------------------------------------------------------------------------
class TestPaginaPanel(BaseExtra):
    def test_una_pestana_y_una_vista_por_paciente_y_ninguna_ajena(self):
        pedro = self.paciente_de(self.alberto, 'Pedro', 'pedro')
        rosa = self.paciente_de(self.lucia, 'Rosa', 'rosa')
        html = self.cli('alberto').get('/supervisor').get_data(as_text=True)
        for p in (self.maria, pedro):
            self.assertIn(f'data-vista="paciente-{p.id}"', html)
            self.assertIn(f'id="vista-paciente-{p.id}"', html)
        self.assertNotIn(f'paciente-{rosa.id}"', html)
        self.assertNotIn('Rosa', html)

    def test_sin_pacientes_el_panel_lo_explica(self):
        r = self.cli('lucia').get('/supervisor')
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        self.assertIn('No tienes ningún paciente vinculado', html)
        self.assertNotIn('id="vista-paciente-', html)


if __name__ == '__main__':
    unittest.main()