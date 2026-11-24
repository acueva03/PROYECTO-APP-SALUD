# Tests para el módulo de notificaciones y endpoints de push (P4 - Andrés)
# Cobertura completa: registro de tokens, envío FCM simulado, SOS, idempotencia y tick.

import os
import unittest
from datetime import timedelta, timezone
from unittest.mock import patch, MagicMock

from base_tests import BaseTest
from models import db, User, DispositivoPush, AlertSOS, RegistroToma, Alarm, ahora
from notificaciones import (
    enviar_a_usuario,
    enviar_a_supervisores_de,
    ya_avisado,
    marcar_avisado,
    _enviar_a_tokens
)
from notificaciones_bp import procesar_tomas_sin_confirmar


class TestDispositivosPush(BaseTest):

    def test_registro_dispositivo_sin_sesion_da_401(self):
        resp = self.cliente.post('/api/dispositivos', json={'token': 'tok-123'})
        self.assertEqual(resp.status_code, 401)

    def test_registro_dispositivo_token_invalido_da_400(self):
        self.login('maria')
        resp_vacio = self.cliente.post('/api/dispositivos', json={'token': ''})
        self.assertEqual(resp_vacio.status_code, 400)

        resp_sin_token = self.cliente.post('/api/dispositivos', json={})
        self.assertEqual(resp_sin_token.status_code, 400)

        resp_tipo_erroneo = self.cliente.post('/api/dispositivos', json={'token': 12345})
        self.assertEqual(resp_tipo_erroneo.status_code, 400)

    def test_registro_dispositivo_exitoso(self):
        self.login('maria')
        resp = self.cliente.post('/api/dispositivos', json={
            'token': 'token-fcm-maria-android',
            'plataforma': 'android'
        })
        self.assertEqual(resp.status_code, 200)

        disp = DispositivoPush.query.filter_by(token='token-fcm-maria-android').first()
        self.assertIsNotNone(disp)
        self.assertEqual(disp.user_id, self.maria.id)
        self.assertEqual(disp.plataforma, 'android')

    def test_registro_dispositivo_reasigna_token_existente(self):
        # Primero registrado por María
        self.login('maria')
        self.cliente.post('/api/dispositivos', json={'token': 'mismo-token-movil'})

        # Luego el móvil cambia de usuario (login Alberto)
        self.login('alberto')
        resp = self.cliente.post('/api/dispositivos', json={'token': 'mismo-token-movil'})
        self.assertEqual(resp.status_code, 200)

        # Debe pertenecer ahora a Alberto
        disp = DispositivoPush.query.filter_by(token='mismo-token-movil').first()
        self.assertEqual(disp.user_id, self.alberto.id)

    def test_desregistro_dispositivo_por_token(self):
        self.login('alberto')
        self.cliente.post('/api/dispositivos', json={'token': 'token-a-borrar'})
        self.assertIsNotNone(DispositivoPush.query.filter_by(token='token-a-borrar').first())

        resp = self.cliente.delete('/api/dispositivos', json={'token': 'token-a-borrar'})
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(DispositivoPush.query.filter_by(token='token-a-borrar').first())

    def test_desregistro_todos_dispositivos_usuario(self):
        self.login('maria')
        self.cliente.post('/api/dispositivos', json={'token': 'tok-maria-1'})
        self.cliente.post('/api/dispositivos', json={'token': 'tok-maria-2'})
        self.assertEqual(DispositivoPush.query.filter_by(user_id=self.maria.id).count(), 2)

        resp = self.cliente.delete('/api/dispositivos', json={})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(DispositivoPush.query.filter_by(user_id=self.maria.id).count(), 0)


class TestEnvioNotificaciones(BaseTest):

    def setUp(self):
        super().setUp()
        os.environ['TESTING'] = '1'

    def tearDown(self):
        os.environ.pop('TESTING', None)
        super().tearDown()

    def test_enviar_a_usuario_sin_dispositivos_devuelve_cero(self):
        total = enviar_a_usuario(self.alberto.id, 'SOS', 'Alerta', 'Mensaje de prueba')
        self.assertEqual(total, 0)

    def test_enviar_a_usuario_con_dispositivo_registrado(self):
        disp = DispositivoPush(user_id=self.alberto.id, token='tok-alb-test', plataforma='android')
        db.session.add(disp)
        db.session.commit()

        total = enviar_a_usuario(self.alberto.id, 'SOS', 'Alerta', 'Mensaje de prueba', en_segundo_plano=False)
        self.assertEqual(total, 1)

    def test_enviar_a_supervisores_de_paciente_vinculado(self):
        # Alberto es supervisor de María en BaseTest
        disp = DispositivoPush(user_id=self.alberto.id, token='tok-supervisor-alb', plataforma='android')
        db.session.add(disp)
        db.session.commit()

        total = enviar_a_supervisores_de(self.maria.id, 'SOS', 'Alerta SOS', 'Ayuda', en_segundo_plano=False)
        self.assertEqual(total, 1)

    def test_enviar_a_supervisores_paciente_sin_supervisores(self):
        paciente_solo = User(nombre='Solitario', username='solitario', rol='dependiente')
        paciente_solo.set_password('1234')
        db.session.add(paciente_solo)
        db.session.commit()

        total = enviar_a_supervisores_de(paciente_solo.id, 'SOS', 'Alerta', 'Cuerpo', en_segundo_plano=False)
        self.assertEqual(total, 0)

    @patch('notificaciones.inicializar_firebase')
    def test_limpieza_token_invalido_fcm(self, mock_init_fb):
        mock_app = MagicMock()
        mock_init_fb.return_value = mock_app

        disp = DispositivoPush(user_id=self.alberto.id, token='tok-invalido-fcm', plataforma='android')
        db.session.add(disp)
        db.session.commit()

        mock_messaging = MagicMock()
        mock_messaging.send.side_effect = Exception("The registration token is not a valid FCM registration token (unregistered)")
        mock_fb_module = MagicMock()
        mock_fb_module.messaging = mock_messaging

        with patch.dict('sys.modules', {
            'firebase_admin': mock_fb_module,
            'firebase_admin.messaging': mock_messaging
        }):
            _enviar_a_tokens(['tok-invalido-fcm'], 'SOS', 'Titulo', 'Cuerpo')

        # El token inválido debe haber sido borrado de la base de datos
        disp_en_bd = DispositivoPush.query.filter_by(token='tok-invalido-fcm').first()
        self.assertIsNone(disp_en_bd)


class TestPushSOS(BaseTest):

    def setUp(self):
        super().setUp()
        os.environ['TESTING'] = '1'

    def tearDown(self):
        os.environ.pop('TESTING', None)
        super().tearDown()

    @patch('app.enviar_a_supervisores_de')
    def test_sos_dispara_push_a_supervisores(self, mock_envio):
        self.login('maria')
        resp = self.cliente.post('/api/sos')
        self.assertEqual(resp.status_code, 201)

        self.assertTrue(mock_envio.called)
        args, kwargs = mock_envio.call_args
        self.assertEqual(args[0], self.maria.id)
        self.assertEqual(args[1], 'SOS')
        self.assertIn('María', args[2])

    @patch('app.enviar_a_supervisores_de')
    def test_sos_repetido_no_duplica_push(self, mock_envio):
        self.login('maria')
        # Primer SOS
        resp1 = self.cliente.post('/api/sos')
        self.assertEqual(resp1.status_code, 201)
        self.assertEqual(mock_envio.call_count, 1)

        # Segundo SOS cuando ya hay una activa -> devuelve 200 y no vuelve a llamar al envío
        resp2 = self.cliente.post('/api/sos')
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(mock_envio.call_count, 1)

    @patch('app.enviar_a_usuario')
    def test_atender_alerta_envia_push_al_paciente(self, mock_envio_usuario):
        # María lanza alerta SOS
        alerta = AlertSOS(user_id=self.maria.id, estado='ACTIVA')
        db.session.add(alerta)
        db.session.commit()

        # Alberto (su supervisor) atiende la alerta
        self.login('alberto')
        resp = self.cliente.post(f'/api/alertas/{alerta.id}/atender')
        self.assertEqual(resp.status_code, 200)

        self.assertTrue(mock_envio_usuario.called)
        args, kwargs = mock_envio_usuario.call_args
        self.assertEqual(args[0], self.maria.id)
        self.assertEqual(args[1], 'SOS')
        self.assertIn('Alberto', args[3])


class TestTickEIdempotencia(BaseTest):

    def setUp(self):
        super().setUp()
        os.environ['TESTING'] = '1'
        os.environ['CRON_TOKEN'] = 'secreto-cron-test-123'

    def tearDown(self):
        os.environ.pop('TESTING', None)
        os.environ.pop('CRON_TOKEN', None)
        super().tearDown()

    def test_tick_sin_token_da_403(self):
        resp = self.cliente.post('/interno/tick')
        self.assertEqual(resp.status_code, 403)

    def test_tick_token_incorrecto_da_403(self):
        resp = self.cliente.post('/interno/tick', headers={'X-Cron-Token': 'token-falso'})
        self.assertEqual(resp.status_code, 403)

    def test_tick_token_correcto_devuelve_200(self):
        resp = self.cliente.post('/interno/tick', headers={'X-Cron-Token': 'secreto-cron-test-123'})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get('ok'))
        self.assertIn('tomas_avisadas', data)

    def test_idempotencia_helpers_ya_avisado(self):
        self.assertFalse(ya_avisado('TOMA_SIN_CONFIRMAR', 'toma:999'))
        marcar_avisado('TOMA_SIN_CONFIRMAR', 'toma:999', user_id=self.maria.id)
        self.assertTrue(ya_avisado('TOMA_SIN_CONFIRMAR', 'toma:999'))

        # Intentar marcar de nuevo no debe fallar ni duplicar
        marcar_avisado('TOMA_SIN_CONFIRMAR', 'toma:999', user_id=self.maria.id)
        self.assertTrue(ya_avisado('TOMA_SIN_CONFIRMAR', 'toma:999'))

    @patch('notificaciones_bp.enviar_a_supervisores_de')
    def test_toma_sin_confirmar_15_minutos_aviso_unico(self, mock_envio):
        # Crear alarma y registro de toma con 20 minutos de antigüedad
        alarma = Alarm(user_id=self.maria.id, titulo='Ibuprofeno 600', hora='08:00', activa=True)
        db.session.add(alarma)
        db.session.commit()

        hace_20_min = ahora() - timedelta(minutes=20)
        toma = RegistroToma(
            alarma_id=alarma.id,
            user_id=self.maria.id,
            titulo='Ibuprofeno 600',
            fecha_prevista='2026-11-22',
            hora_prevista='08:00',
            estado='PENDIENTE',
            creado=hace_20_min
        )
        db.session.add(toma)
        db.session.commit()

        # Primer proceso: debe detectar la toma y enviar aviso
        avisos = procesar_tomas_sin_confirmar()
        self.assertEqual(avisos, 1)
        self.assertEqual(mock_envio.call_count, 1)

        # Segundo proceso en el siguiente minuto: idempotente, no vuelve a avisar
        avisos2 = procesar_tomas_sin_confirmar()
        self.assertEqual(avisos2, 0)
        self.assertEqual(mock_envio.call_count, 1)


if __name__ == '__main__':
    unittest.main()
