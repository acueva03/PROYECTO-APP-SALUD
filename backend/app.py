import os
import threading
import time
from datetime import datetime, timedelta, timezone, date
# NUEVO: Añadidos session, redirect y url_for
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from sqlalchemy import inspect, text
from models import db, User, Alarm, HealthMetric, AlertSOS, MedicalProfile, RegistroToma, ahora

app = Flask(__name__, 
            template_folder='../frontend/templates', 
            static_folder='../frontend/static')

# NUEVO: Configuración de sesiones para el login seguro
app.config['SECRET_KEY'] = 'clave_super_secreta_cambiar_en_produccion'
app.config['SESSION_COOKIE_HTTPONLY'] = True

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'app_salud.db') 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'check_same_thread': False, 'timeout': 15}
}

db.init_app(app)

with app.app_context(): 
    db.create_all()

def actualizar_columnas():
    columnas = {c['name'] for c in inspect(db.engine).get_columns('alarms')}
    with db.engine.begin() as con:
        if 'fecha' not in columnas:
            con.execute(text('ALTER TABLE alarms ADD COLUMN fecha VARCHAR(10)'))
        if 'ultima_vez_sono' not in columnas:
            con.execute(text('ALTER TABLE alarms ADD COLUMN ultima_vez_sono DATETIME'))
        con.execute(text('UPDATE alarms SET fecha = :hoy WHERE fecha IS NULL AND activa = 1'),
                    {'hoy': date.today().isoformat()})

with app.app_context():
    actualizar_columnas()

def guardar_en_bd():
    try:
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print("ERROR de base de datos:", e)
        return False

def hora_valida(texto):
    try:
        datetime.strptime(texto, '%H:%M')
    except (ValueError, TypeError):
        return False
    return len(texto) == 5

def fecha_valida(texto):
    try:
        datetime.strptime(texto, '%Y-%m-%d')
    except (ValueError, TypeError):
        return False
    return len(texto) == 10

def siguiente_fecha(fecha_local, hora_local, hora_alarma):
    dia = datetime.strptime(fecha_local, '%Y-%m-%d').date()
    if hora_alarma <= hora_local:
        dia += timedelta(days=1)
    return dia.isoformat()

def alarma_a_dict(a):
    return {
        'id': a.id,
        'titulo': a.titulo,
        'hora': a.hora,
        'fecha': a.fecha,
        'es_repetitiva': a.es_repetitiva,
        'activa': a.activa,
        'ultima_vez_sono': (a.ultima_vez_sono.replace(tzinfo=timezone.utc).isoformat()
                            if a.ultima_vez_sono else None)
    }

def usuario_actual():
    user_id = session.get('user_id')
    return db.session.get(User, user_id) if user_id else None

# ---------------- NUEVO: RUTAS DE LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        nombre = data.get('nombre')
        password = data.get('password')
        
        usuario = User.query.filter_by(nombre=nombre).first()
        if usuario and usuario.check_password(password):
            session.clear()
            session['user_id'] = usuario.id
            session['rol'] = usuario.rol
            session['nombre'] = usuario.nombre
            
            if usuario.rol == 'supervisor':
                return redirect(url_for('supervisor'))
            return redirect(url_for('inicio'))
            
        return render_template('login.html', error="Nombre o contraseña incorrectos")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
# --------------------------------------------------------

# NUEVO: Rutas principales protegidas con sesión
@app.route('/')
def inicio():
    if 'user_id' not in session or session.get('rol') != 'dependiente':
        return redirect(url_for('login'))
    usuario = db.session.get(User, session['user_id'])
    return render_template('paciente.html', usuario=usuario)

@app.route('/supervisor')
def supervisor():
    if 'user_id' not in session or session.get('rol') != 'supervisor':
        return redirect(url_for('login'))
    usuario = db.session.get(User, session['user_id'])
    # De momento el panel muestra un solo paciente: el primero vinculado
    paciente = usuario.dependientes[0] if usuario.dependientes else None
    return render_template('supervisor.html', usuario=usuario, paciente=paciente)

@app.route('/api/alarmas', methods=['POST'])
def crear_alarma():
    user_id = session.get('user_id') # NUEVO: Sacado de la sesión segura
    if not user_id: return jsonify({'error': 'No autorizado'}), 401

    data = request.get_json(silent=True) or {}
    if not hora_valida(data.get('hora')): return jsonify({'error': 'Hora inválida'}), 400
    if not fecha_valida(data.get('fecha')): return jsonify({'error': 'Fecha inválida'}), 400

    titulo = (data.get('titulo') or '').strip()
    if not titulo: return jsonify({'error': 'Falta titulo'}), 400
    
    if datetime.strptime(data['fecha'], '%Y-%m-%d').date() < date.today() - timedelta(days=1):
        return jsonify({'error': 'La fecha no puede estar en el pasado'}), 400

    nueva_alarma = Alarm(
        user_id=user_id,
        titulo=titulo,
        hora=data.get('hora'),
        fecha=data.get('fecha'),
        es_repetitiva=bool(data.get('es_repetitiva', False))
    )
    db.session.add(nueva_alarma)
    if not guardar_en_bd():
        return jsonify({'error': 'No se pudo guardar la alarma'}), 500
    return jsonify({'mensaje': 'Alarma configurada', 'alarma': alarma_a_dict(nueva_alarma)}), 201

# NUEVO: La ruta ya no pide el id en la URL, lo coge de la sesión
@app.route('/api/mis-alarmas', methods=['GET'])
def listar_mis_alarmas():
    user_id = session.get('user_id')
    if not user_id: return jsonify({'error': 'No autorizado'}), 401
    usuario = db.session.get(User, user_id)
    incluir_todas = request.args.get('todas') == '1'
    alarmas = [a for a in usuario.alarmas if incluir_todas or a.activa]
    alarmas.sort(key=lambda a: ((a.fecha or ''), a.hora))
    return jsonify([alarma_a_dict(a) for a in alarmas])

@app.route('/api/sos', methods=['POST'])
def activar_sos():
    user_id = session.get('user_id') # NUEVO: Sacado de la sesión segura
    if not user_id: return jsonify({'error': 'No autorizado'}), 401
    usuario = db.session.get(User, user_id)
    if usuario.rol != 'dependiente':
        return jsonify({'error': 'Solo un dependiente puede emitir un SOS'}), 400
    
    existente = AlertSOS.query.filter_by(user_id=user_id, estado='ACTIVA').first()
    if existente:
        return jsonify({'mensaje': 'Ya existe una alerta SOS activa', 'alerta_id': existente.id}), 200

    alerta = AlertSOS(user_id=user_id)
    db.session.add(alerta)
    if not guardar_en_bd(): return jsonify({'error': 'Error interno'}), 500
    print("ALERTA SOS RECIBIDA:", alerta.id)
    return jsonify({'mensaje': 'Alerta SOS emitida', 'alerta_id': alerta.id}), 201

# NUEVO: Panel del supervisor, lee las alertas buscando por la sesión
@app.route('/api/mis-alertas', methods=['GET'])
def alertas_activas():
    supervisor_id = session.get('user_id')
    if not supervisor_id: return jsonify({'error': 'No autorizado'}), 401
    supervisor = db.session.get(User, supervisor_id)
    resultado = []
    for dep in supervisor.dependientes:
        for a in dep.alertas_sos:
            if a.estado == 'ACTIVA':
                resultado.append({'alerta_id': a.id, 'dependiente': dep.nombre,
                  'fecha_hora': a.fecha_hora.replace(tzinfo=timezone.utc).isoformat()})
    return jsonify(resultado)

@app.route('/api/alertas/<int:alerta_id>/atender', methods=['POST'])
def atender_alerta(alerta_id):
    sup = usuario_actual()
    if not sup: return jsonify({'error': 'No autorizado'}), 401
    if sup.rol != 'supervisor': return jsonify({'error': 'Prohibido'}), 403

    alerta = db.session.get(AlertSOS, alerta_id)
    if not alerta: return jsonify({'error': 'Alerta no encontrada'}), 404
    if alerta.usuario not in sup.dependientes:      # solo alertas de SUS dependientes
        return jsonify({'error': 'Prohibido'}), 403

    alerta.estado = 'ATENDIDA'
    if not guardar_en_bd(): return jsonify({'error': 'No se pudo marcar la alerta'}), 500
    return jsonify({'mensaje': 'Alerta atendida'}), 200

@app.route('/api/alarmas/<int:alarma_id>/estado', methods=['PATCH'])
def cambiar_estado_alarma(alarma_id):
    # NUEVO: hace falta sesión
    user_id = session.get('user_id')
    if not user_id: return jsonify({'error': 'No autorizado'}), 401

    alarma = db.session.get(Alarm, alarma_id)
    if not alarma: return jsonify({'error': 'Alarma no encontrada'}), 404

    # NUEVO: la alarma tiene que ser del usuario que llama
    if alarma.user_id != user_id: return jsonify({'error': 'Prohibido'}), 403

    data = request.get_json(silent=True) or {}
    if 'fecha' in data and not fecha_valida(data['fecha']): return jsonify({'error': 'Fecha inválida'}), 400
    if 'activa' in data: alarma.activa = bool(data['activa'])
    else: alarma.activa = not alarma.activa
    if 'fecha' in data: alarma.fecha = data['fecha']
    if not guardar_en_bd(): return jsonify({'error': 'Error al guardar'}), 500
    return jsonify({'mensaje': 'Actualizado', 'alarma_id': alarma.id, 'activa': alarma.activa}), 200

@app.route('/api/alarmas/<int:alarma_id>/sonada', methods=['POST'])
def alarma_sonada(alarma_id):
    # NUEVO: hace falta sesión
    user_id = session.get('user_id')
    if not user_id: return jsonify({'error': 'No autorizado'}), 401

    alarma = db.session.get(Alarm, alarma_id)
    if not alarma: return jsonify({'error': 'Alarma no encontrada'}), 404

    # NUEVO: la alarma tiene que ser del usuario que llama
    if alarma.user_id != user_id: return jsonify({'error': 'Prohibido'}), 403

    data = request.get_json(silent=True) or {}
    fecha_local, hora_local, fecha_prevista = data.get('fecha_local'), data.get('hora_local'), data.get('fecha_prevista')
    if not (fecha_valida(fecha_local) and hora_valida(hora_local) and fecha_valida(fecha_prevista)):
        return jsonify({'error': 'Datos faltantes'}), 400
    registro = RegistroToma.query.filter_by(alarma_id=alarma.id, fecha_prevista=fecha_prevista, hora_prevista=alarma.hora).first()
    if not registro:
        registro = RegistroToma(alarma_id=alarma.id, user_id=alarma.user_id, titulo=alarma.titulo, fecha_prevista=fecha_prevista, hora_prevista=alarma.hora)
        db.session.add(registro)
    if alarma.activa and alarma.fecha == fecha_prevista:
        alarma.ultima_vez_sono = ahora()
        if alarma.es_repetitiva: alarma.fecha = siguiente_fecha(fecha_local, hora_local, alarma.hora)
        else: alarma.activa = False
    if not guardar_en_bd(): return jsonify({'error': 'Error base de datos'}), 500
    return jsonify({'mensaje': 'Sonada', 'registro_id': registro.id, 'alarma': alarma_a_dict(alarma)}), 200

def toma_a_dict(t):
    return {'toma_id': t.id, 'titulo': t.titulo, 'fecha_prevista': t.fecha_prevista, 'hora_prevista': t.hora_prevista, 'estado': t.estado, 'creado': t.creado.replace(tzinfo=timezone.utc).isoformat()}

def tomas_pendientes_de(user_id, horas):
    limite = ahora() - timedelta(hours=horas)
    tomas = RegistroToma.query.filter_by(user_id=user_id, estado='PENDIENTE').order_by(RegistroToma.id).all()
    return [t for t in tomas if t.creado.replace(tzinfo=timezone.utc) >= limite]

@app.route('/api/tomas/<int:toma_id>/confirmar', methods=['POST'])
def confirmar_toma(toma_id):
    # NUEVO: hace falta sesión
    user_id = session.get('user_id')
    if not user_id: return jsonify({'error': 'No autorizado'}), 401

    toma = db.session.get(RegistroToma, toma_id)
    if not toma: return jsonify({'error': 'Toma no encontrada'}), 404

    # NUEVO: la toma tiene que ser del usuario que llama
    if toma.user_id != user_id: return jsonify({'error': 'Prohibido'}), 403

    if toma.estado != 'CONFIRMADA':
        toma.estado = 'CONFIRMADA'
        toma.confirmada_en = ahora()
        if not guardar_en_bd(): return jsonify({'error': 'Error base de datos'}), 500
    return jsonify({'mensaje': 'Toma confirmada'}), 200

# NUEVO: Rutas actualizadas sin ID en la URL
@app.route('/api/mis-tomas-pendientes', methods=['GET'])
def tomas_pendientes():
    user_id = session.get('user_id')
    if not user_id: return jsonify({'error': 'No autorizado'}), 401
    return jsonify([toma_a_dict(t) for t in tomas_pendientes_de(user_id, 6)])

@app.route('/api/mis-tomas-supervisadas', methods=['GET'])
def tomas_supervisor():
    supervisor_id = session.get('user_id')
    if not supervisor_id: return jsonify({'error': 'No autorizado'}), 401
    supervisor = db.session.get(User, supervisor_id)
    resultado = []
    for dep in supervisor.dependientes:
        for t in tomas_pendientes_de(dep.id, 24):
            d = toma_a_dict(t)
            d['dependiente'] = dep.nombre
            resultado.append(d)
    return jsonify(resultado)

if __name__ == '__main__':
    app.run(debug=True)