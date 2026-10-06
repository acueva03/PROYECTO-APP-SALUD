import os

from flask import Flask, render_template, request, jsonify
from models import db, User, Alarm, HealthMetric, AlertSOS, MedicalProfile

# Inicializamos la aplicación Flask
app = Flask(__name__)

# Configuración de SQLite (creará el archivo app_salud.db localmente)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'app_salud.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Crear las tablas automáticamente al iniciar
with app.app_context():
    db.create_all()

# --- EJEMPLOS DE RUTAS API ---

@app.route('/api/usuarios', methods=['POST'])
def crear_usuario():
    data = request.get_json()
    nuevo_usuario = User(
        nombre=data.get('nombre'),
        edad=data.get('edad'),
        peso=data.get('peso'),
        rol=data.get('rol', 'dependiente')
    )
    db.session.add(nuevo_usuario)
    db.session.commit()
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
    db.session.commit()
    return jsonify({'mensaje': 'Alarma configurada con éxito'}), 201

@app.route('/api/sos', methods=['POST'])
def activar_sos():
    data = request.get_json()
    alerta = AlertSOS(user_id=data.get('user_id'))
    db.session.add(alerta)
    db.session.commit()
    return jsonify({'mensaje': 'Alerta SOS emitida', 'alerta_id': alerta.id}), 201

# Ruta principal: Muestra la pantalla del paciente (El botón SOS de Laura)
@app.route('/')
def inicio():
    # Intenta cargar la página de Laura si existe, si no, muestra un mensaje
    try:
        return render_template('paciente.html')
    except:
        return "<h1>Servidor Flask funcionando</h1><p>Aquí se cargará el HTML de Laura (paciente.html) cuando te lo entregue.</p>"

# Ruta secundaria: Muestra la pantalla del supervisor (El panel de Sofía)
@app.route('/supervisor')
def supervisor():
    # Intenta cargar la página de Sofía si existe, si no, muestra un mensaje
    try:
        return render_template('supervisor.html')
    except:
        return "<h1>Panel de Supervisor</h1><p>Aquí se cargará el HTML de Sofía (supervisor.html) cuando te lo entregue.</p>"

@app.route('/alerta', methods=['POST'])
def recibir_alerta():
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id', 1)   # provisional hasta que haya login
    alerta = AlertSOS(user_id=user_id)
    db.session.add(alerta)
    db.session.commit()
    print("ALERTA RECIBIDA", alerta.id)
    return jsonify({"status": "ok", "alerta_id": alerta.id}), 200

# Vincular un supervisor con un dependiente
@app.route('/api/vinculos', methods=['POST'])
def vincular():
    data = request.get_json()
    supervisor = db.session.get(User, data.get('supervisor_id'))
    dependiente = db.session.get(User, data.get('dependiente_id'))
    if not supervisor or not dependiente:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    if dependiente not in supervisor.dependientes:
        supervisor.dependientes.append(dependiente)
        db.session.commit()
    return jsonify({'mensaje': 'Vínculo creado'}), 201


# Guardar o actualizar la ficha médica de un usuario
@app.route('/api/usuarios/<int:user_id>/ficha-medica', methods=['PUT'])
def guardar_ficha(user_id):
    usuario = db.session.get(User, user_id)
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    data = request.get_json()
    ficha = usuario.ficha_medica or MedicalProfile(user_id=user_id)
    for campo in ('grupo_sanguineo', 'alergias', 'enfermedades_cronicas', 'medicacion',
                  'contacto_emergencia_nombre', 'contacto_emergencia_telefono'):
        if campo in data:
            setattr(ficha, campo, data[campo])
    db.session.add(ficha)
    db.session.commit()
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
                                  'fecha_hora': a.fecha_hora.isoformat()})
    return jsonify(resultado)


# Marcar una alerta como atendida
@app.route('/api/alertas/<int:alerta_id>/atender', methods=['POST'])
def atender_alerta(alerta_id):
    alerta = db.session.get(AlertSOS, alerta_id)
    if not alerta:
        return jsonify({'error': 'Alerta no encontrada'}), 404
    alerta.estado = 'ATENDIDA'
    db.session.commit()
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

if __name__ == '__main__':
    # Arrancamos el servidor en modo desarrollo
    app.run(debug=True)
