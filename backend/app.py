from flask import Flask, render_template, request, jsonify

# Inicializamos la aplicación Flask
app = Flask(__name__)

from flask import Flask, jsonify, request
from models import db, User, Alarm, HealthMetric, AlertSOS

# Configuración de SQLite (creará el archivo app_salud.db localmente)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app_salud.db'
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
    # Imprime la alerta en la consola de Visual Studio Code al presionar el botón SOS
    print("ALERTA RECIBIDA")
    
    # Responde al cliente (JavaScript de Andrés) confirmando que la alerta llegó
    return jsonify({"status": "ok", "mensaje": "Alerta recibida correctamente"}), 200

if __name__ == '__main__':
    # Arrancamos el servidor en modo desarrollo
    app.run(debug=True)
