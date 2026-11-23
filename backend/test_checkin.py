"""Tests del check-in diario «Estoy bien» (P5 - Laura).
Ejecutar desde backend/:  python3 -m unittest test_checkin -v"""
from base_tests import BaseTest      # PRIMERO: fija DATABASE_URL en memoria antes de importar app
import os
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch

from sqlalchemy.exc import IntegrityError

from app import app
from models import db, User, CheckIn, CheckinConfig, AvisoEnviado, hoy_madrid
from checkin_bp import (procesar_checkins_perdidos, hora_valida, hora_local_de, ESTADOS_ANIMO,
                        HORA_LIMITE_MINIMA, HORA_LIMITE_MAXIMA, HORA_LIMITE_POR_DEFECTO)


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
        manana = hoy_madrid() + timedelta(days=1)
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

# ---------------------------------------------------------------------------
# Funciones internas (caja blanca: no necesitan base de datos)
# ---------------------------------------------------------------------------
class TestFuncionesInternas(unittest.TestCase):
    def test_hora_valida_acepta_horas_reales(self):
        for ok in ('00:00', '08:00', '12:30', '23:59'):
            self.assertTrue(hora_valida(ok), ok)

    def test_hora_valida_rechaza_formatos_raros(self):
        # Pruebas pensadas para que falle: sin cero, fuera de rango, con segundos, espacios, tipos raros...
        for mal in ('', '9:00', '09:0', '24:00', '12:60', '09:00:00', 'ab:cd', ' 09:00', '09:00\n', None, 900, ['09:00']):
            self.assertFalse(hora_valida(mal), repr(mal))

    def test_hora_local_pasa_de_utc_a_madrid(self):
        # En verano Madrid va +2 h respecto a UTC; en invierno, +1 h (cambio de hora incluido)
        self.assertEqual(hora_local_de(datetime(2026, 7, 1, 8, 30)), '10:30')
        self.assertEqual(hora_local_de(datetime(2026, 1, 15, 8, 30)), '09:30')
        self.assertIsNone(hora_local_de(None))

    def test_constantes_coherentes(self):
        self.assertLessEqual(HORA_LIMITE_MINIMA, HORA_LIMITE_POR_DEFECTO)
        self.assertLessEqual(HORA_LIMITE_POR_DEFECTO, HORA_LIMITE_MAXIMA)
        self.assertTrue(hora_valida(HORA_LIMITE_MINIMA) and hora_valida(HORA_LIMITE_MAXIMA))

    def test_opciones_de_animo_caben_en_la_columna(self):
        self.assertGreater(len(ESTADOS_ANIMO), 0)
        self.assertEqual(len(ESTADOS_ANIMO), len(set(ESTADOS_ANIMO)))     # sin repetidas
        for e in ESTADOS_ANIMO:
            self.assertLessEqual(len(e), 50, e)                           # la columna es String(50)


# ---------------------------------------------------------------------------
# Casos límite de la API
# ---------------------------------------------------------------------------
class TestCasosLimite(BaseCheckin):
    def ayer(self):
        return (hoy_madrid() - timedelta(days=1)).isoformat()

    def test_el_checkin_de_ayer_no_cuenta_para_hoy(self):
        db.session.add(CheckIn(user_id=self.maria.id, fecha=self.ayer()))
        db.session.commit()
        self.assertFalse(self.cli('maria').get('/api/mi-checkin').get_json()['hecho'])
        self.assertEqual(self.cli('maria').post('/api/checkin', json={}).status_code, 201)
        self.assertEqual(CheckIn.query.count(), 2)

    def test_ventana_de_14_dias_del_supervisor(self):
        hoy = hoy_madrid()
        db.session.add_all([
            CheckIn(user_id=self.maria.id, fecha=(hoy - timedelta(days=13)).isoformat()),   # el más antiguo que se ve
            CheckIn(user_id=self.maria.id, fecha=(hoy - timedelta(days=14)).isoformat()),   # ya fuera de la ventana
        ])
        db.session.commit()
        dias = self.cli('alberto').get(f'/api/supervisor/pacientes/{self.maria.id}/checkin').get_json()['dias']
        self.assertEqual(len(dias), 14)
        self.assertTrue(dias[0]['hecho'])                       # hace 13 días: entra
        self.assertEqual(sum(1 for d in dias if d['hecho']), 1)  # hace 14 días: no aparece

    def test_la_base_de_datos_impide_dos_checkins_el_mismo_dia(self):
        hoy = hoy_madrid().isoformat()
        db.session.add(CheckIn(user_id=self.maria.id, fecha=hoy))
        db.session.commit()
        db.session.add(CheckIn(user_id=self.maria.id, fecha=hoy))
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        self.assertEqual(CheckIn.query.count(), 1)

    def test_desactivado_permite_hacer_el_checkin_igualmente(self):
        db.session.add(CheckinConfig(user_id=self.maria.id, hora_limite='11:00', activo=False))
        db.session.commit()
        self.assertEqual(self.cli('maria').post('/api/checkin', json={}).status_code, 201)

    def test_animo_vacio_se_guarda_como_sin_rellenar(self):
        self.assertEqual(self.cli('maria').post('/api/checkin', json={'estado_animo': ''}).status_code, 201)
        self.assertIsNone(CheckIn.query.one().estado_animo)

    def test_cuerpo_que_no_es_json_cuenta_como_sin_animo(self):
        r = self.cli('maria').post('/api/checkin', data='no es json', content_type='text/plain')
        self.assertEqual(r.status_code, 201)
        self.assertIsNone(CheckIn.query.one().estado_animo)

    def test_el_checkin_de_otro_paciente_no_se_mezcla(self):
        self.alberto.dependientes.append(self.rosa)
        db.session.commit()
        self.cli('rosa').post('/api/checkin', json={})
        datos = self.cli('alberto').get(f'/api/supervisor/pacientes/{self.maria.id}/checkin').get_json()
        self.assertFalse(datos['dias'][-1]['hecho'])            # lo de Rosa no aparece en María
        datos_rosa = self.cli('alberto').get(f'/api/supervisor/pacientes/{self.rosa.id}/checkin').get_json()
        self.assertTrue(datos_rosa['dias'][-1]['hecho'])

    def test_la_hora_del_checkin_es_la_de_madrid(self):
        r = self.cli('maria').post('/api/checkin', json={}).get_json()
        db.session.expire_all()
        esperada = hora_local_de(CheckIn.query.one().hecho_en)
        self.assertEqual(r['hora'], esperada)


# ---------------------------------------------------------------------------
# Más casos del aviso al supervisor
# ---------------------------------------------------------------------------
class TestAvisoCasosExtra(BaseCheckin):
    def avisar(self, hora):
        with patch('checkin_bp.hora_madrid', return_value=hora), \
             patch('checkin_bp.enviar_a_supervisores_de') as envio:
            return procesar_checkins_perdidos(), envio

    def test_el_checkin_de_ayer_no_evita_el_aviso_de_hoy(self):
        ayer = (hoy_madrid() - timedelta(days=1)).isoformat()
        db.session.add(CheckIn(user_id=self.maria.id, fecha=ayer))
        db.session.commit()
        self.assertEqual(self.avisar('12:00')[0], 1)

    def test_dos_pacientes_sin_checkin_dan_dos_avisos(self):
        self.alberto.dependientes.append(self.rosa)
        db.session.commit()
        avisos, envio = self.avisar('12:00')
        self.assertEqual(avisos, 2)
        pacientes = sorted(c.kwargs['paciente_id'] for c in envio.call_args_list)
        self.assertEqual(pacientes, sorted([self.maria.id, self.rosa.id]))
        self.assertEqual(AvisoEnviado.query.filter_by(tipo='CHECKIN_PERDIDO').count(), 2)

    def test_solo_avisa_por_los_que_no_lo_hicieron(self):
        self.alberto.dependientes.append(self.rosa)
        db.session.commit()
        self.cli('maria').post('/api/checkin', json={})
        avisos, envio = self.avisar('12:00')
        self.assertEqual(avisos, 1)
        self.assertEqual(envio.call_args.kwargs['paciente_id'], self.rosa.id)

    def test_con_dos_supervisores_es_un_solo_aviso_del_paciente(self):
        # enviar_a_supervisores_de ya reparte el push entre todos los supervisores: no se llama dos veces
        self.lucia.dependientes.append(self.maria)
        db.session.commit()
        avisos, envio = self.avisar('12:00')
        self.assertEqual(avisos, 1)
        self.assertEqual(envio.call_count, 1)

    def test_los_supervisores_no_generan_avisos(self):
        # Alberto y Lucía son supervisores: nunca se les pide el check-in
        avisos, envio = self.avisar('23:30')
        self.assertEqual(avisos, 1)                              # solo María (Rosa no tiene supervisor)
        self.assertEqual(envio.call_args.kwargs['paciente_id'], self.maria.id)

    def test_contenido_del_aviso(self):
        _, envio = self.avisar('12:00')
        k = envio.call_args.kwargs
        self.assertEqual(k['tipo'], 'CHECKIN_PERDIDO')
        self.assertIn('María', k['titulo'])
        self.assertIn('María', k['cuerpo'])
        self.assertIn('11:00', k['cuerpo'])                      # la hora límite aparece en el mensaje
        self.assertEqual(k['datos']['paciente_id'], str(self.maria.id))
        self.assertEqual(k['datos']['fecha'], hoy_madrid().isoformat())

    def test_si_hace_el_checkin_tarde_no_hay_mas_avisos(self):
        self.avisar('12:00')                                     # primer aviso
        self.cli('maria').post('/api/checkin', json={})          # lo hace a las 12:xx
        avisos, envio = self.avisar('12:05')
        self.assertEqual(avisos, 0)
        self.assertFalse(envio.called)

    def test_cambiar_la_hora_limite_a_mas_tarde_retrasa_el_aviso(self):
        self.cli('maria').put('/api/mi-checkin/config', json={'hora_limite': '20:00'})
        self.assertEqual(self.avisar('12:00')[0], 0)
        self.assertEqual(self.avisar('20:00')[0], 1)


# ---------------------------------------------------------------------------
# Resumen del supervisor: el check-in de cada paciente en GET /api/supervisor/pacientes (tarea 5.7)
# ---------------------------------------------------------------------------
class TestResumenCheckinSupervisor(BaseCheckin):
    def setUp(self):
        super().setUp()
        self.alberto.dependientes.append(self.rosa)          # Alberto supervisa a María y a Rosa
        db.session.commit()

    def resumen(self, hora='09:00'):
        """{nombre: checkin_hoy} de los pacientes de Alberto, como si fuera esa hora de Madrid."""
        with patch('checkin_bp.hora_madrid', return_value=hora):
            datos = self.cli('alberto').get('/api/supervisor/pacientes').get_json()
        return {p['nombre']: p['checkin_hoy'] for p in datos}

    def test_cada_paciente_trae_su_checkin_con_14_dias(self):
        r = self.resumen()
        self.assertEqual(sorted(r), ['María', 'Rosa'])
        for c in r.values():
            self.assertEqual(len(c['dias']), 14)
            self.assertEqual(c['dias'][-1]['fecha'], hoy_madrid().isoformat())   # el último día es hoy
            self.assertEqual(c['hora_limite'], '11:00')

    def test_pendiente_y_no_realizado_segun_la_hora(self):
        self.assertEqual(self.resumen('10:59')['María']['estado_hoy'], 'PENDIENTE')
        self.assertEqual(self.resumen('11:00')['María']['estado_hoy'], 'NO_REALIZADO')

    def test_hecho_no_se_mezcla_entre_pacientes(self):
        self.cli('maria').post('/api/checkin', json={'estado_animo': 'Contento'})
        r = self.resumen('12:00')
        self.assertEqual(r['María']['estado_hoy'], 'HECHO')
        self.assertTrue(r['María']['dias'][-1]['hecho'])
        self.assertEqual(r['Rosa']['estado_hoy'], 'NO_REALIZADO')     # lo de María no cuenta para Rosa
        self.assertFalse(r['Rosa']['dias'][-1]['hecho'])

    def test_desactivado_se_ve_como_desactivado(self):
        db.session.add(CheckinConfig(user_id=self.rosa.id, hora_limite='11:00', activo=False))
        db.session.commit()
        r = self.resumen('12:00')
        self.assertEqual(r['Rosa']['estado_hoy'], 'DESACTIVADO')
        self.assertEqual(r['María']['estado_hoy'], 'NO_REALIZADO')

    def test_el_resumen_coincide_con_el_endpoint_de_un_paciente(self):
        # La lista y el endpoint individual deben dar exactamente la misma información
        with patch('checkin_bp.hora_madrid', return_value='12:00'):
            c = self.cli('alberto')
            lista = {p['id']: p['checkin_hoy'] for p in c.get('/api/supervisor/pacientes').get_json()}
            individual = c.get(f'/api/supervisor/pacientes/{self.maria.id}/checkin').get_json()
        self.assertEqual(lista[self.maria.id], individual)

    def test_un_supervisor_sin_pacientes_no_recibe_nada(self):
        self.assertEqual(self.cli('lucia').get('/api/supervisor/pacientes').get_json(), [])


# ---------------------------------------------------------------------------
# Pantallas
# ---------------------------------------------------------------------------
class TestPantallas(BaseCheckin):
    def test_la_pantalla_del_paciente_tiene_la_tarjeta_y_el_script(self):
        r = self.cli('maria').get('/')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'id="btn-checkin"', r.data)
        self.assertIn(b'checkin.js', r.data)
        self.assertIn(b'form-checkin-config', r.data)

    def test_el_boton_sos_sigue_en_su_sitio(self):
        # El check-in no debe romper el SOS (riesgo 3.18): sos.js y su botón siguen presentes y sos.js va el primero
        r = self.cli('maria').get('/')
        self.assertIn(b'id="boton-sos"', r.data)
        self.assertLess(r.data.index(b'sos.js'), r.data.index(b'checkin.js'))

    def test_el_panel_del_supervisor_no_lleva_la_tarjeta_del_paciente(self):
        r = self.cli('alberto').get('/supervisor')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b'btn-checkin', r.data)

    def test_sin_sesion_la_pantalla_redirige_al_login(self):
        self.assertEqual(app.test_client().get('/').status_code, 302)


if __name__ == '__main__':
    unittest.main()