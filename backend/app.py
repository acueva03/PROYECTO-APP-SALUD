import os
import threading
import time
from datetime import datetime, timedelta, timezone, date
from flask import Flask, render_template, request, jsonify
from sqlalchemy import inspect, text
from models import db, User, Alarm, HealthMetric, AlertSOS, MedicalProfile, RegistroToma, ahora
# Inicializamos la aplicación Flask
app = Flask(__name__)

# Configuración de SQLite (creará el archivo app_salud.db localmente)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'app_salud.db') #configura la base de datos SQLite
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False #desactiva el seguimiento de modificaciones para mejorar el rendimiento
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'check_same_thread': False, 'timeout': 15}
}


db.init_app(app) #conecta la base de datos con la aplicación Flask

# Crear las tablas automáticamente al iniciar
with app.app_context(): 
    db.create_all()

def actualizar_columnas():
    """db.create_all() no añade columnas a tablas que ya existen: lo hacemos a mano."""
    columnas = {c['name'] for c in inspect(db.engine).get_columns('alarms')}
    with db.engine.begin() as con:
        if 'fecha' not in columnas:
            con.execute(text('ALTER TABLE alarms ADD COLUMN fecha VARCHAR(10)'))
        if 'ultima_vez_sono' not in columnas:
            con.execute(text('ALTER TABLE alarms ADD COLUMN ultima_vez_sono DATETIME'))
        # Las alarmas activas sin fecha nunca sonarían: les ponemos la de hoy
        con.execute(text('UPDATE alarms SET fecha = :hoy WHERE fecha IS NULL AND activa = 1'),
                    {'hoy': date.today().isoformat()})

with app.app_context():
    actualizar_columnas()

def guardar_en_bd():
    """Hace commit. Devuelve True si fue bien; si falla, deshace y devuelve False."""
    try:
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print("ERROR de base de datos:", e)   # 3.2.2: se ve en la consola de Flask
        return False

# ---------- Ayudas para las alarmas ----------

def hora_valida(texto):
    """True si texto es una hora real con formato HH:MM de 5 caracteres (ej. 08:30, no 8:30)."""
    try:
        datetime.strptime(texto, '%H:%M')
    except (ValueError, TypeError):
        return False
    return len(texto) == 5


def fecha_valida(texto):
    """True si texto es una fecha real con formato AAAA-MM-DD de 10 caracteres (ej. 2026-10-17)."""
    try:
        datetime.strptime(texto, '%Y-%m-%d')
    except (ValueError, TypeError):
        return False
    return len(texto) == 10


def siguiente_fecha(fecha_local, hora_local, hora_alarma):
    """Próxima fecha en la que debe sonar una alarma REPETITIVA que acaba de sonar.
    - Si ya ha pasado la hora de la alarma hoy -> mañana.
    - Si todavía no (alarma perdida de un día anterior que suena tarde) -> hoy.
    """
    dia = datetime.strptime(fecha_local, '%Y-%m-%d').date()
    if hora_alarma <= hora_local:
        dia += timedelta(days=1)
    return dia.isoformat()


def alarma_a_dict(a):
    """Cómo se envía una alarma al navegador."""
    return {
        'id': a.id,
        'titulo': a.titulo,
        'hora': a.hora,                          # texto "HH:MM"
        'fecha': a.fecha,                        # texto "AAAA-MM-DD": próxima vez que suena
        'es_repetitiva': a.es_repetitiva,
        'activa': a.activa,
        # UTC con zona horaria (igual que las alertas SOS); None si todavía no ha sonado
        'ultima_vez_sono': (a.ultima_vez_sono.replace(tzinfo=timezone.utc).isoformat()
                            if a.ultima_vez_sono else None)
    }

@app.route('/api/usuarios', methods=['POST'])
def crear_usuario():
    data = request.get_json(silent=True) or {}
    if not data.get('nombre'):
        return jsonify({'error': 'Falta el nombre'}), 400
    nuevo_usuario = User(
        nombre=data.get('nombre'),
        edad=data.get('edad'),
        peso=data.get('peso'),
        rol=data.get('rol', 'dependiente')
    )
    db.session.add(nuevo_usuario)
    if not guardar_en_bd():
        return jsonify({'error': 'No se pudo crear el usuario'}), 500
    return jsonify({'mensaje': 'Usuario creado con éxito', 'id': nuevo_usuario.id}), 201

@app.route('/api/alarmas', methods=['POST'])
def crear_alarma():
    # silent=True: si el cuerpo no es JSON devuelve None en vez de lanzar un error raro
    data = request.get_json(silent=True) or {}

    # Hora HH:MM real (00:00 a 23:59) y de 5 caracteres: rechaza "8:30"
    if not hora_valida(data.get('hora')):
        return jsonify({'error': 'La hora debe tener formato HH:MM (ej. 08:30)'}), 400

    # NUEVO: fecha exacta en la que debe sonar (en una repetitiva, el primer día)
    if not fecha_valida(data.get('fecha')):
        return jsonify({'error': 'La fecha debe tener formato AAAA-MM-DD (ej. 2026-10-17)'}), 400

    titulo = (data.get('titulo') or '').strip()
    user_id = data.get('user_id')
    if not titulo or not isinstance(user_id, int) or isinstance(user_id, bool):
        return jsonify({'error': 'Faltan titulo o user_id (número)'}), 400

    # Margen de un día por si el navegador y el servidor tienen zonas horarias distintas
    if datetime.strptime(data['fecha'], '%Y-%m-%d').date() < date.today() - timedelta(days=1):
        return jsonify({'error': 'La fecha no puede estar en el pasado'}), 400
    if len(titulo) > 100:
        return jsonify({'error': 'El título no puede pasar de 100 caracteres'}), 400

    # NUEVO: SQLite no obliga a que el user_id exista, así que lo comprobamos nosotros
    if not db.session.get(User, data.get('user_id')):
        return jsonify({'error': 'Usuario no encontrado'}), 404

    nueva_alarma = Alarm(
        user_id=data.get('user_id'),
        titulo=titulo,
        hora=data.get('hora'),
        fecha=data.get('fecha'),
        es_repetitiva=bool(data.get('es_repetitiva', False))
    )
    db.session.add(nueva_alarma)
    if not guardar_en_bd():
        return jsonify({'error': 'No se pudo guardar la alarma'}), 500
    return jsonify({'mensaje': 'Alarma configurada con éxito',
                    'alarma': alarma_a_dict(nueva_alarma)}), 201
# Devuelve las alarmas ACTIVAS de un usuario.
# La página del paciente llama a esta ruta para saber a qué horas debe avisar.
@app.route('/api/usuarios/<int:user_id>/alarmas', methods=['GET'])
def listar_alarmas(user_id):
    usuario = db.session.get(User, user_id)
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    # Por defecto solo las activas. Con ?todas=1 también las desactivadas y las que ya sonaron.
    incluir_todas = request.args.get('todas') == '1'
    alarmas = [a for a in usuario.alarmas if incluir_todas or a.activa]
    alarmas.sort(key=lambda a: ((a.fecha or ''), a.hora))   # por fecha y luego por hora
    return jsonify([alarma_a_dict(a) for a in alarmas])

@app.route('/api/sos', methods=['POST'])
def activar_sos():
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')
    if user_id is None:
        return jsonify({'error': 'Falta user_id'}), 400
    usuario = db.session.get(User, user_id)
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    if usuario.rol != 'dependiente':
        return jsonify({'error': 'Solo un dependiente puede emitir un SOS'}), 400
    
    # 2. Evitar alertas duplicadas: si ya hay una activa, reutilizarla
    existente = AlertSOS.query.filter_by(user_id=user_id, estado='ACTIVA').first()
    if existente:
        return jsonify({'mensaje': 'Ya existe una alerta SOS activa',
                        'alerta_id': existente.id}), 200

    # 3. Crear y guardar la alerta nueva
    alerta = AlertSOS(user_id=user_id)
    db.session.add(alerta)
    if not guardar_en_bd():
        return jsonify({'error': 'Error interno'}), 500
    print("ALERTA SOS RECIBIDA:", alerta.id)
    return jsonify({'mensaje': 'Alerta SOS emitida', 'alerta_id': alerta.id}), 201

# Ruta principal: Muestra la pantalla del paciente (El botón SOS de Laura)
@app.route('/')
def inicio():
    # Intenta cargar la página de Laura si existe, si no, muestra un mensaje
    try:
        return render_template('paciente.html')
    except:
        return "<h1>Error al cargar la página del paciente</h1>"

# Ruta secundaria: Muestra la pantalla del supervisor (El panel de Sofía)
@app.route('/supervisor')
def supervisor():
    # Intenta cargar la página de Sofía si existe, si no, muestra un mensaje
    try:
        return render_template('supervisor.html')
    except:
        return "<h1>Error al cargar la página del supervisor</h1>"

# Vincular un supervisor con un dependiente
@app.route('/api/vinculos', methods=['POST'])
def vincular():
    data = request.get_json(silent=True) or {}
    supervisor = db.session.get(User, data.get('supervisor_id'))
    dependiente = db.session.get(User, data.get('dependiente_id'))
    if not supervisor or not dependiente:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    if dependiente not in supervisor.dependientes:
        supervisor.dependientes.append(dependiente)
        if not guardar_en_bd():
            return jsonify({'error': 'No se pudo crear el vínculo'}), 500
    return jsonify({'mensaje': 'Vínculo creado'}), 201


# Guardar o actualizar la ficha médica de un usuario
@app.route('/api/usuarios/<int:user_id>/ficha-medica', methods=['PUT'])
def guardar_ficha(user_id):
    usuario = db.session.get(User, user_id)
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    data = request.get_json(silent=True) or {}
    ficha = usuario.ficha_medica or MedicalProfile(user_id=user_id)
    for campo in ('grupo_sanguineo', 'alergias', 'enfermedades_cronicas', 'medicacion',
                  'contacto_emergencia_nombre', 'contacto_emergencia_telefono'):
        if campo in data:
            setattr(ficha, campo, data[campo])
    db.session.add(ficha)
    if not guardar_en_bd():
        return jsonify({'error': 'No se pudo guardar la ficha médica'}), 500
    return jsonify({'mensaje': 'Ficha médica guardada'}), 200


# Alertas activas de los dependientes de un supervisor (para el panel)
@app.route('/api/supervisores/<int:supervisor_id>/alertas', methods=['GET'])
def alertas_activas(supervisor_id):
    supervisor = db.session.get(User, supervisor_id)
    if not supervisor:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    resultado = []
    for dep in supervisor.dependientes:
        for a in dep.alertas_sos:
            if a.estado == 'ACTIVA':
                resultado.append({'alerta_id': a.id, 'dependiente': dep.nombre,
                  'fecha_hora': a.fecha_hora.replace(tzinfo=timezone.utc).isoformat()})
    return jsonify(resultado)


# Marcar una alerta como atendida
@app.route('/api/alertas/<int:alerta_id>/atender', methods=['POST'])
def atender_alerta(alerta_id):
    alerta = db.session.get(AlertSOS, alerta_id)
    if not alerta:
        return jsonify({'error': 'Alerta no encontrada'}), 404
    alerta.estado = 'ATENDIDA'
    if not guardar_en_bd():
        return jsonify({'error': 'No se pudo marcar la alerta como atendida'}), 500
    return jsonify({'mensaje': 'Alerta atendida'}), 200

@app.route('/api/usuarios/<int:user_id>', methods=['GET'])
def obtener_usuario(user_id):
    usuario = db.session.get(User, user_id)
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    return jsonify({
        'id': usuario.id,
        'nombre': usuario.nombre,
        'apellidos': usuario.apellidos,
        'telefono': usuario.telefono,
        'edad': usuario.edad,
        'peso': usuario.peso,
        'altura': usuario.altura,
        'rol': usuario.rol
    })

@app.route('/api/alarmas/<int:alarma_id>/estado', methods=['PATCH'])
def cambiar_estado_alarma(alarma_id):
    alarma = db.session.get(Alarm, alarma_id)
    if not alarma:
        return jsonify({'error': 'Alarma no encontrada'}), 404

    data = request.get_json(silent=True) or {}

    # NUEVO: al reactivar se puede enviar la nueva fecha. Validamos ANTES de tocar nada.
    if 'fecha' in data and not fecha_valida(data['fecha']):
        return jsonify({'error': 'La fecha debe tener formato AAAA-MM-DD (ej. 2026-10-17)'}), 400

    if 'activa' in data:
        alarma.activa = bool(data['activa'])
    else:
        alarma.activa = not alarma.activa
    if 'fecha' in data:
        alarma.fecha = data['fecha']

    if not guardar_en_bd():
        return jsonify({'error': 'No se pudo cambiar el estado de la alarma'}), 500
    return jsonify({
        'mensaje': 'Estado de alarma actualizado',
        'alarma_id': alarma.id,
        'activa': alarma.activa
    }), 200


# NUEVO: el navegador avisa aquí cuando una alarma acaba de sonar.
# Así "ya sonó" queda guardado en la base de datos y no se pierde al cerrar la pestaña.
@app.route('/api/alarmas/<int:alarma_id>/sonada', methods=['POST'])
def alarma_sonada(alarma_id):
    alarma = db.session.get(Alarm, alarma_id)
    if not alarma:
        return jsonify({'error': 'Alarma no encontrada'}), 404

    data = request.get_json(silent=True) or {}
    fecha_local = data.get('fecha_local')
    hora_local = data.get('hora_local')
    fecha_prevista = data.get('fecha_prevista')   # la fecha que tenía la alarma cuando sonó
    if not (fecha_valida(fecha_local) and hora_valida(hora_local) and fecha_valida(fecha_prevista)):
        return jsonify({'error': 'Faltan fecha_local, hora_local y fecha_prevista'}), 400

    # Si el navegador reintenta, reutilizamos el registro en vez de crear uno duplicado
    registro = RegistroToma.query.filter_by(
        alarma_id=alarma.id, fecha_prevista=fecha_prevista, hora_prevista=alarma.hora).first()
    if not registro:
        registro = RegistroToma(alarma_id=alarma.id, user_id=alarma.user_id, titulo=alarma.titulo,
                                fecha_prevista=fecha_prevista, hora_prevista=alarma.hora)
        db.session.add(registro)

    # Solo movemos la alarma la primera vez (si ya se movió, un reintento no la vuelve a mover)
    if alarma.activa and alarma.fecha == fecha_prevista:
        alarma.ultima_vez_sono = ahora()
        if alarma.es_repetitiva:
            alarma.fecha = siguiente_fecha(fecha_local, hora_local, alarma.hora)
        else:
            alarma.activa = False

    if not guardar_en_bd():
        return jsonify({'error': 'No se pudo registrar que la alarma sonó'}), 500
    return jsonify({'mensaje': 'Alarma registrada como sonada',
                    'registro_id': registro.id,
                    'alarma': alarma_a_dict(alarma)}), 200

# ---------- Tomas / confirmaciones ----------

def toma_a_dict(t):
    return {
        'toma_id': t.id,
        'titulo': t.titulo,
        'fecha_prevista': t.fecha_prevista,
        'hora_prevista': t.hora_prevista,
        'estado': t.estado,
        'creado': t.creado.replace(tzinfo=timezone.utc).isoformat()
    }


def tomas_pendientes_de(user_id, horas):
    """Tomas PENDIENTES de un usuario creadas en las últimas `horas` horas."""
    limite = ahora() - timedelta(hours=horas)
    tomas = RegistroToma.query.filter_by(user_id=user_id, estado='PENDIENTE') \
                              .order_by(RegistroToma.id).all()
    return [t for t in tomas if t.creado.replace(tzinfo=timezone.utc) >= limite]


# La paciente confirma que ha hecho lo que decía la alarma ("Ya lo hice")
@app.route('/api/tomas/<int:toma_id>/confirmar', methods=['POST'])
def confirmar_toma(toma_id):
    toma = db.session.get(RegistroToma, toma_id)
    if not toma:
        return jsonify({'error': 'Toma no encontrada'}), 404
    if toma.estado != 'CONFIRMADA':
        toma.estado = 'CONFIRMADA'
        toma.confirmada_en = ahora()
        if not guardar_en_bd():
            return jsonify({'error': 'No se pudo confirmar la toma'}), 500
    return jsonify({'mensaje': 'Toma confirmada'}), 200


# Pendientes de la paciente (la página las pide al abrirse, por si se recargó)
@app.route('/api/usuarios/<int:user_id>/tomas-pendientes', methods=['GET'])
def tomas_pendientes(user_id):
    if not db.session.get(User, user_id):
        return jsonify({'error': 'Usuario no encontrado'}), 404
    return jsonify([toma_a_dict(t) for t in tomas_pendientes_de(user_id, 6)])


# Para el panel del supervisor: tomas sin confirmar de sus dependientes (últimas 24 h)
@app.route('/api/supervisores/<int:supervisor_id>/tomas', methods=['GET'])
def tomas_supervisor(supervisor_id):
    supervisor = db.session.get(User, supervisor_id)
    if not supervisor:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    resultado = []
    for dep in supervisor.dependientes:
        for t in tomas_pendientes_de(dep.id, 24):
            d = toma_a_dict(t)
            d['dependiente'] = dep.nombre
            resultado.append(d)
    return jsonify(resultado)

if __name__ == '__main__':
    app.run(debug=True)