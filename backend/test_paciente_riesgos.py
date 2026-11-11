"""Tests de los riesgos de la pantalla del paciente: 3.12.3, 3.14 y 3.16.
Ejecutar: python3 -m unittest test_paciente_riesgos -v"""
from base_tests import BaseTest      # PRIMERO: fija DATABASE_URL en memoria antes de importar app
from datetime import datetime, timedelta
from app import app
from models import db, User, Alarm, RegistroToma, ZONA, ahora


def momento_madrid(minutos):
    """(fecha, hora) en Madrid desplazadas 'minutos' desde ahora (negativo = en el pasado)."""
    m = datetime.now(ZONA) + timedelta(minutes=minutos)
    return m.date().isoformat(), m.strftime('%H:%M')


class BaseRiesgos(BaseTest):
    def crear_alarma(self, usuario, minutos=60, **extra):
        fecha, hora = momento_madrid(minutos)
        alarma = Alarm(user_id=usuario.id, titulo=extra.pop('titulo', 'Paracetamol'),
                       hora=hora, fecha=fecha, activa=True, **extra)
        db.session.add(alarma)
        db.session.commit()
        return alarma

    def cli(self, username):
        """Cliente con la sesión de ese usuario (self.cliente solo guarda una sesión)."""
        c = app.test_client()
        c.post('/login', data={'username': username, 'password': '1234'})
        return c

    def otro_usuario(self, nombre, username, rol):
        u = User(nombre=nombre, username=username, rol=rol)
        u.set_password('1234')
        db.session.add(u)
        db.session.commit()
        return u


# ---------------------------------------------------------------------------
# Riesgo 3.14: borrado accidental de una alarma de medicación
# ---------------------------------------------------------------------------
class TestBorradoLogico(BaseRiesgos):
    def test_eliminar_no_borra_la_fila(self):
        alarma = self.crear_alarma(self.maria, dosis='500 mg')
        c = self.cli('maria')
        self.assertEqual(c.delete(f'/api/alarmas/{alarma.id}').status_code, 200)
        db.session.expire_all()
        guardada = db.session.get(Alarm, alarma.id)
        self.assertIsNotNone(guardada)                 # sigue en la BD
        self.assertTrue(guardada.eliminada)
        self.assertIsNotNone(guardada.eliminada_en)
        # Eliminar dos veces: la segunda ya "no existe" (igual que antes del cambio)
        self.assertEqual(c.delete(f'/api/alarmas/{alarma.id}').status_code, 404)

    def test_eliminada_no_se_lista_ni_suena(self):
        alarma = self.crear_alarma(self.maria)
        c = self.cli('maria')
        c.delete(f'/api/alarmas/{alarma.id}')
        self.assertEqual(c.get('/api/mis-alarmas?todas=1').get_json(), [])
        fecha, hora = momento_madrid(0)
        r = c.post(f'/api/alarmas/{alarma.id}/sonada',
                   json={'fecha_local': fecha, 'hora_local': hora, 'fecha_prevista': alarma.fecha})
        self.assertEqual(r.status_code, 404)
        self.assertEqual(RegistroToma.query.count(), 0)   # no genera tomas
        self.assertEqual(c.patch(f'/api/alarmas/{alarma.id}/estado', json={'activa': True}).status_code, 404)

    def test_papelera_y_recuperar(self):
        alarma = self.crear_alarma(self.maria, dosis='1 comprimido')
        c = self.cli('maria')
        c.delete(f'/api/alarmas/{alarma.id}')
        papelera = c.get('/api/mis-alarmas-eliminadas').get_json()
        self.assertEqual([a['id'] for a in papelera], [alarma.id])
        self.assertEqual(papelera[0]['dosis'], '1 comprimido')
        self.assertIn('eliminada_en', papelera[0])

        r = c.post(f'/api/alarmas/{alarma.id}/restaurar')
        self.assertEqual(r.status_code, 200)
        self.assertEqual([a['id'] for a in c.get('/api/mis-alarmas').get_json()], [alarma.id])
        self.assertEqual(c.get('/api/mis-alarmas-eliminadas').get_json(), [])
        # Recuperar algo que no está eliminado
        self.assertEqual(c.post(f'/api/alarmas/{alarma.id}/restaurar').status_code, 409)

    def test_recuperar_permisos(self):
        alarma = self.crear_alarma(self.maria)
        self.cli('maria').delete(f'/api/alarmas/{alarma.id}')
        self.otro_usuario('Rosa', 'rosa', 'dependiente')
        self.otro_usuario('Lucía', 'lucia', 'supervisor')
        url = f'/api/alarmas/{alarma.id}/restaurar'

        self.assertEqual(app.test_client().post(url).status_code, 401)   # sin sesión
        self.assertEqual(self.cli('rosa').post(url).status_code, 403)    # otro paciente
        self.assertEqual(self.cli('lucia').post(url).status_code, 403)   # supervisor NO vinculado
        self.assertEqual(self.cli('maria').post('/api/alarmas/9999/restaurar').status_code, 404)
        db.session.expire_all()
        self.assertTrue(db.session.get(Alarm, alarma.id).eliminada)
        self.assertEqual(self.cli('alberto').post(url).status_code, 200)  # su supervisor sí (3.14.3)

    def test_recuperar_alarma_pasada_la_reprograma(self):
        # Una alarma activa cuya hora ya pasó no debe sonar como "perdida" nada más recuperarla
        alarma = self.crear_alarma(self.maria, minutos=-120)
        c = self.cli('maria')
        c.delete(f'/api/alarmas/{alarma.id}')
        datos = c.post(f'/api/alarmas/{alarma.id}/restaurar').get_json()['alarma']
        momento = datetime.strptime(datos['fecha'] + ' ' + datos['hora'], '%Y-%m-%d %H:%M').replace(tzinfo=ZONA)
        self.assertGreater(momento, datetime.now(ZONA))

    def test_supervisor_ve_eliminadas_aparte(self):
        alarma = self.crear_alarma(self.maria, titulo='Sintrom')
        self.cli('maria').delete(f'/api/alarmas/{alarma.id}')
        datos = self.cli('alberto').get(f'/api/supervisor/pacientes/{self.maria.id}/medicacion').get_json()
        self.assertEqual(datos['alarmas'], [])                       # ya no sale como programada
        self.assertEqual([a['titulo'] for a in datos['eliminadas']], ['Sintrom'])

    def test_papelera_solo_para_pacientes(self):
        self.assertEqual(app.test_client().get('/api/mis-alarmas-eliminadas').status_code, 401)
        self.assertEqual(self.cli('alberto').get('/api/mis-alarmas-eliminadas').status_code, 403)


# ---------------------------------------------------------------------------
# Riesgo 3.16: confirmación en bloque de tomas
# ---------------------------------------------------------------------------
class TestConfirmacionIndividual(BaseRiesgos):
    def sonar(self, c, alarma):
        fecha, hora = momento_madrid(0)
        r = c.post(f'/api/alarmas/{alarma.id}/sonada',
                   json={'fecha_local': fecha, 'hora_local': hora, 'fecha_prevista': alarma.fecha})
        return r.get_json()['registro_id']

    def test_confirmar_una_no_confirma_la_otra(self):
        a1 = self.crear_alarma(self.maria, titulo='Paracetamol', dosis='500 mg', minutos=0)
        a2 = self.crear_alarma(self.maria, titulo='Omeprazol', dosis='20 mg', minutos=0)
        c = self.cli('maria')
        t1, t2 = self.sonar(c, a1), self.sonar(c, a2)
        self.assertEqual(c.post(f'/api/tomas/{t1}/confirmar').status_code, 200)
        db.session.expire_all()
        self.assertEqual(db.session.get(RegistroToma, t1).estado, 'CONFIRMADA')
        self.assertEqual(db.session.get(RegistroToma, t2).estado, 'PENDIENTE')
        # Y el supervisor sigue viendo la segunda como pendiente
        tomas = self.cli('alberto').get('/api/mis-tomas-supervisadas').get_json()
        self.assertEqual([t['toma_id'] for t in tomas], [t2])

    def test_pendientes_traen_la_dosis(self):
        a = self.crear_alarma(self.maria, dosis='1 comprimido', minutos=0)
        c = self.cli('maria')
        self.sonar(c, a)
        self.assertEqual(c.get('/api/mis-tomas-pendientes').get_json()[0]['dosis'], '1 comprimido')

    def test_deshacer_devuelve_a_pendiente(self):
        a = self.crear_alarma(self.maria, minutos=0)
        c = self.cli('maria')
        t = self.sonar(c, a)
        c.post(f'/api/tomas/{t}/confirmar')
        self.assertEqual(c.post(f'/api/tomas/{t}/deshacer').status_code, 200)
        db.session.expire_all()
        toma = db.session.get(RegistroToma, t)
        self.assertEqual(toma.estado, 'PENDIENTE')
        self.assertIsNone(toma.confirmada_en)
        # Deshacer una toma que ya está pendiente no tiene sentido
        self.assertEqual(c.post(f'/api/tomas/{t}/deshacer').status_code, 409)

    def test_deshacer_caduca(self):
        a = self.crear_alarma(self.maria, minutos=0)
        c = self.cli('maria')
        t = self.sonar(c, a)
        c.post(f'/api/tomas/{t}/confirmar')
        toma = db.session.get(RegistroToma, t)
        toma.confirmada_en = ahora() - timedelta(minutes=5)
        db.session.commit()
        self.assertEqual(c.post(f'/api/tomas/{t}/deshacer').status_code, 409)
        db.session.expire_all()
        self.assertEqual(db.session.get(RegistroToma, t).estado, 'CONFIRMADA')

    def test_deshacer_permisos(self):
        a = self.crear_alarma(self.maria, minutos=0)
        c = self.cli('maria')
        t = self.sonar(c, a)
        c.post(f'/api/tomas/{t}/confirmar')
        self.otro_usuario('Rosa', 'rosa', 'dependiente')
        self.assertEqual(app.test_client().post(f'/api/tomas/{t}/deshacer').status_code, 401)
        self.assertEqual(self.cli('rosa').post(f'/api/tomas/{t}/deshacer').status_code, 403)
        self.assertEqual(c.post('/api/tomas/9999/deshacer').status_code, 404)


# ---------------------------------------------------------------------------
# Riesgo 3.12.3: alarmas que no sonaron porque la pantalla estaba cerrada
# ---------------------------------------------------------------------------
class TestAlarmasSinSonar(BaseRiesgos):
    def sin_sonar(self, username='alberto'):
        tomas = self.cli(username).get('/api/mis-tomas-supervisadas').get_json()
        return [t for t in tomas if t.get('sin_sonar')]

    def test_alarma_pasada_sin_sonar_avisa_al_supervisor(self):
        self.crear_alarma(self.maria, titulo='Insulina', dosis='10 UI', minutos=-20)
        avisos = self.sin_sonar()
        self.assertEqual(len(avisos), 1)
        self.assertIn('Insulina', avisos[0]['titulo'])
        self.assertEqual(avisos[0]['dependiente_id'], self.maria.id)
        self.assertEqual(avisos[0]['dosis'], '10 UI')
        self.assertIsNone(avisos[0]['toma_id'])
        self.assertIn('creado', avisos[0])        # el panel calcula "sin confirmar desde hace X min"

    def test_margen_de_15_minutos(self):
        self.crear_alarma(self.maria, minutos=-5)     # aún puede estar sonando
        self.crear_alarma(self.maria, minutos=30)     # futura
        self.assertEqual(self.sin_sonar(), [])

    def test_no_avisa_si_sono_esta_eliminada_o_desactivada(self):
        sonada = self.crear_alarma(self.maria, titulo='Sonada', minutos=-20)
        db.session.add(RegistroToma(alarma_id=sonada.id, user_id=self.maria.id, titulo='Sonada',
                                    fecha_prevista=sonada.fecha, hora_prevista=sonada.hora))
        self.crear_alarma(self.maria, titulo='Eliminada', minutos=-20, eliminada=True)
        desactivada = self.crear_alarma(self.maria, titulo='Desactivada', minutos=-20)
        desactivada.activa = False
        db.session.commit()
        self.assertEqual(self.sin_sonar(), [])

    def test_solo_la_ve_su_supervisor(self):
        self.crear_alarma(self.maria, minutos=-20)
        self.otro_usuario('Lucía', 'lucia', 'supervisor')
        self.assertEqual(self.sin_sonar('lucia'), [])
        self.assertEqual(len(self.sin_sonar('alberto')), 1)


if __name__ == '__main__':
    import unittest
    unittest.main()
