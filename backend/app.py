import os
import threading
import time
from datetime import datetime
from datetime import timezone
from flask import Flask, render_template, request, jsonify
from models import db, User, Alarm, HealthMetric, AlertSOS, MedicalProfile

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

def guardar_en_bd():
    """Hace commit. Devuelve True si fue bien; si falla, deshace y devuelve False."""
    try:
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print("ERROR de base de datos:", e)   # 3.2.2: se ve en la consola de Flask
        return False

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
    data = request.get_json()
    nueva_alarma = Alarm(
        user_id=data.get('user_id'),
        titulo=data.get('titulo'),
        hora=data.get('hora'),
        es_repetitiva=data.get('es_repetitiva', False)
    )
    db.session.add(nueva_alarma)
    if not guardar_en_bd():
        return jsonify({'error': 'No se pudo guardar la alarma'}), 500
    return jsonify({'mensaje': 'Alarma configurada con éxito'}), 201

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
    if 'activa' in data:
        alarma.activa = bool(data['activa'])
    else:
        alarma.activa = not alarma.activa

    if not guardar_en_bd():
        return jsonify({'error': 'No se pudo cambiar el estado de la alarma'}), 500
    return jsonify({
        'mensaje': 'Estado de alarma actualizado',
        'alarma_id': alarma.id,
        'activa': alarma.activa
    }), 200

if __name__ == '__main__':
    app.run(debug=True)