import unittest
import json
from datetime import date, timedelta
from app import app
from models import db, User, Alarm, AlertSOS

class TestAppSalud(unittest.TestCase):
    
    # --- TEST FIXTURE (Preparación y Limpieza) ---
    def setUp(self):
        """
        Se ejecuta ANTES de cada prueba.
        Crea una base de datos temporal en memoria para no modificar 'app_salud.db'.
        """
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        
        self.cliente = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        
        db.create_all()
        
        # Poblamos la BD temporal con usuarios de prueba
        self.maria = User(nombre='María', rol='dependiente')
        self.maria.set_password('1234')
        self.alberto = User(nombre='Alberto', rol='supervisor')
        self.alberto.set_password('1234')
        self.alberto.dependientes.append(self.maria)
        
        db.session.add_all([self.maria, self.alberto])
        db.session.commit()

    def tearDown(self):
        """
        Se ejecuta DESPUÉS de cada prueba.
        Destruye la base de datos temporal para garantizar la independencia de las pruebas.
        """
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # --- TEST CASES (Casos de prueba) ---
    
    def test_encriptacion_password(self):
        """
        Objetivo: Probar la lógica interna de los modelos (Caja Blanca).
        Verifica que el método check_password falle correctamente con claves erróneas.
        """
        usuario = User(nombre='TestUser', rol='dependiente')
        
        self.assertIsNone(usuario.password_hash)
        usuario.set_password('1234')
        
        self.assertIsNotNone(usuario.password_hash)
        self.assertNotEqual(usuario.password_hash, '1234') # Nunca debe guardarse en texto plano
        self.assertTrue(usuario.check_password('1234'))
        self.assertFalse(usuario.check_password('clave_incorrecta')) # Forzamos el fallo

    def test_emision_sos_seguridad(self):
        """
        Objetivo: Probar la seguridad de la ruta /api/sos (Caja Negra y límites).
        Fuerza al código a fallar si se intenta acceder sin sesión iniciada.
        """
        # 1. Intento sin iniciar sesión (debe fallar devolviendo 401)
        respuesta_bloqueada = self.cliente.post('/api/sos', json={})
        self.assertEqual(respuesta_bloqueada.status_code, 401)
        
        # 2. Iniciar sesión como María (dependiente)
        self.cliente.post('/login', data={'nombre': 'María', 'password': '1234'})
        
        # 3. Emitir SOS con sesión activa (debe funcionar devolviendo 201)
        respuesta_ok = self.cliente.post('/api/sos', json={})
        self.assertEqual(respuesta_ok.status_code, 201)
        
        # 4. Validar el impacto en la BD
        alerta = AlertSOS.query.first()
        self.assertIsNotNone(alerta)
        self.assertEqual(alerta.estado, 'ACTIVA')

    def test_crear_alarma_limites(self):
        """
        Objetivo: Probar el control de errores de la ruta /api/alarmas.
        Fuerza al código a fallar enviando formatos de hora inválidos y fechas pasadas.
        """
        self.cliente.post('/login', data={'nombre': 'María', 'password': '1234'})
        
        # 1. Forzar fallo: Hora inválida (Condición límite/errónea)
        resp_hora_invalida = self.cliente.post('/api/alarmas', json={
            'titulo': 'Pastilla', 'fecha': '2030-10-30', 'hora': '25:99'
        })
        self.assertEqual(resp_hora_invalida.status_code, 400)
        
        # 2. Forzar fallo: Fecha en el pasado (Condición límite)
        fecha_pasada = (date.today() - timedelta(days=2)).isoformat()
        resp_fecha_pasada = self.cliente.post('/api/alarmas', json={
            'titulo': 'Pastilla', 'fecha': fecha_pasada, 'hora': '10:00'
        })
        self.assertEqual(resp_fecha_pasada.status_code, 400)
        
        # 3. Datos correctos (Caso de éxito)
        fecha_futura = (date.today() + timedelta(days=2)).isoformat()
        resp_ok = self.cliente.post('/api/alarmas', json={
            'titulo': 'Pastilla', 'fecha': fecha_futura, 'hora': '10:00'
        })
        self.assertEqual(resp_ok.status_code, 201)

    def test_control_roles_autorizacion(self):
        """
        Objetivo: Comprobar que los roles bloquean o permiten el acceso a las rutas correctas.
        Fuerza a la aplicación a rechazar acciones que no corresponden al perfil del usuario.
        """
        # 1. Login como María (dependiente)
        self.cliente.post('/login', data={'nombre': 'María', 'password': '1234'})
        
        # María intenta acceder al panel del supervisor (la app debe redirigirla al login con código 302)
        resp_supervisor = self.cliente.get('/supervisor')
        self.assertEqual(resp_supervisor.status_code, 302)
        
        # 2. Login como Alberto (supervisor)
        self.cliente.post('/login', data={'nombre': 'Alberto', 'password': '1234'})
        
        # Alberto intenta emitir un SOS (debe fallar con un error 400 Bad Request)
        resp_sos_supervisor = self.cliente.post('/api/sos', json={})
        self.assertEqual(resp_sos_supervisor.status_code, 400)

    def test_registro_peso_limites(self):
        """
        Objetivo: Probar la validación de la API de salud (Bloque C).
        Verifica que no se puedan introducir pesos irreales o fechas futuras.
        """
        self.cliente.post('/login', data={'nombre': 'María', 'password': '1234'})
        
        # 1. Forzar fallo: Peso por debajo del límite (ej. 10 kg)
        resp_peso_bajo = self.cliente.post('/api/mi-peso', json={
            'kg': 10, 'fecha': date.today().isoformat()
        })
        self.assertEqual(resp_peso_bajo.status_code, 400)
        
        # 2. Forzar fallo: Fecha futura
        fecha_futura = (date.today() + timedelta(days=5)).isoformat()
        resp_fecha_futura = self.cliente.post('/api/mi-peso', json={
            'kg': 65, 'fecha': fecha_futura
        })
        self.assertEqual(resp_fecha_futura.status_code, 400)
        
        # 3. Caso de éxito: Peso normal (ej. 65 kg) hoy
        resp_ok = self.cliente.post('/api/mi-peso', json={
            'kg': 65, 'fecha': date.today().isoformat()
        })
        self.assertEqual(resp_ok.status_code, 201)

    def test_flujo_alarma_sonada_confirmada(self):
        """
        Objetivo: Simular el ciclo de vida real de un medicamento (Bloque B).
        Prueba que la alarma suena, genera un registro de toma y el usuario la confirma.
        """
        # 1. Inyectamos una alarma activa directamente en la BD temporal
        alarma = Alarm(user_id=self.maria.id, titulo='Pastilla Presión', hora='08:00', fecha=date.today().isoformat(), activa=True)
        db.session.add(alarma)
        db.session.commit()
        
        self.cliente.post('/login', data={'nombre': 'María', 'password': '1234'})
        
        # 2. Simulamos que la alarma suena en el frontend
        resp_sonada = self.cliente.post(f'/api/alarmas/{alarma.id}/sonada', json={
            'fecha_local': date.today().isoformat(),
            'hora_local': '08:00',
            'fecha_prevista': alarma.fecha
        })
        self.assertEqual(resp_sonada.status_code, 200)
        
        # Obtenemos el ID del registro que se acaba de crear en la BD
        datos_sonada = json.loads(resp_sonada.data)
        registro_id = datos_sonada['registro_id']
        
        # 3. Simulamos que el paciente confirma que se ha tomado la pastilla
        resp_confirmar = self.cliente.post(f'/api/tomas/{registro_id}/confirmar')
        self.assertEqual(resp_confirmar.status_code, 200)

    def test_alarma_dias_y_eliminar(self):
        """Alarma de lunes a viernes que empieza en sábado -> salta al lunes; y se puede eliminar."""
        self.cliente.post('/login', data={'nombre': 'María', 'password': '1234'})

        sabado = date.today()
        while sabado.weekday() != 5:
            sabado += timedelta(days=1)

        resp = self.cliente.post('/api/alarmas', json={
            'titulo': 'Pastilla', 'fecha': sabado.isoformat(), 'hora': '10:00',
            'repeticion': 'dias', 'dias': [0, 1, 2, 3, 4]
        })
        self.assertEqual(resp.status_code, 201)
        alarma = json.loads(resp.data)['alarma']
        self.assertEqual(alarma['dias'], [0, 1, 2, 3, 4])
        self.assertEqual(date.fromisoformat(alarma['fecha']).weekday(), 0)   # lunes

        # Sin ningún día marcado debe fallar
        resp_mal = self.cliente.post('/api/alarmas', json={
            'titulo': 'Pastilla', 'fecha': sabado.isoformat(), 'hora': '10:00',
            'repeticion': 'dias', 'dias': []
        })
        self.assertEqual(resp_mal.status_code, 400)

        # Eliminar y comprobar que ya no existe
        self.assertEqual(self.cliente.delete('/api/alarmas/' + str(alarma['id'])).status_code, 200)
        self.assertEqual(self.cliente.delete('/api/alarmas/' + str(alarma['id'])).status_code, 404)

if __name__ == '__main__':
    unittest.main()