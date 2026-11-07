import os
import threading
import time
from datetime import datetime, timedelta, timezone, date
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from sqlalchemy import inspect, text, or_
from models import (db, User, Alarm, HealthMetric, AlertSOS, MedicalProfile, RegistroToma,
                    PesoRegistro, CodigoVinculo, IntentoVinculo, ahora, hoy_madrid, ZONA)
# NUEVO: reglas de usuario y contraseña
from validaciones import (normalizar_username, validar_username,
                          validar_password, username_desde_nombre)
from esquema import comprobar_esquema
from vinculos import (generar_codigo, normalizar_codigo, formato_valido, hash_codigo,
                      formatear_codigo, generar_qr, MINUTOS_VALIDEZ, MAX_FALLOS,
                      VENTANA_MINUTOS, MENSAJE_CODIGO_INVALIDO)

app = Flask(__name__, 
            template_folder='../frontend/templates', 
            static_folder='../frontend/static')

# Configuración de sesiones para el login seguro
app.config['SECRET_KEY'] = 'clave_super_secreta_cambiar_en_produccion'
app.config['SESSION_COOKIE_HTTPONLY'] = True

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# CAMBIADO: si existe la variable DATABASE_URL (la usan los tests) se usa esa base de datos;
# si no, la real app_salud.db
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or ('sqlite:///' + os.path.join(BASE_DIR, 'app_salud.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'check_same_thread': False, 'timeout': 15}
}

db.init_app(app)

with app.app_context(): 
    db.create_all()

def actualizar_columnas():
    necesarias = {
        'alarms': [('fecha', 'VARCHAR(10)'),
                   ('ultima_vez_sono', 'DATETIME'),
                   ('dosis', 'VARCHAR(50)'),
                   ('dias_semana', 'VARCHAR(20)')],
        'registros_toma': [('dosis', 'VARCHAR(50)')],
        'users': [('username', 'VARCHAR(50)')],                       # NUEVO
    }
    inspector = inspect(db.engine)
    with db.engine.begin() as con:
        for tabla, columnas in necesarias.items():
            existentes = {c['name'] for c in inspector.get_columns(tabla)}
            for nombre, tipo in columnas:
                if nombre not in existentes:
                    con.execute(text(f'ALTER TABLE {tabla} ADD COLUMN {nombre} {tipo}'))
        # NUEVO: SQLite no deja añadir UNIQUE con ALTER TABLE, así que se hace con un índice único
        con.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)'))
        con.execute(text('UPDATE alarms SET fecha = :hoy WHERE fecha IS NULL AND activa = 1'),
                    {'hoy': hoy_madrid().isoformat()})

# NUEVO: da username a los usuarios que ya existían (Alberto -> alberto)
def rellenar_usernames():
    usados = {u.username for u in User.query.filter(User.username.isnot(None)).all()}
    for u in User.query.filter(User.username.is_(None)).all():
        candidato = username_desde_nombre(u.nombre)
        if len(candidato) < 3 or candidato in usados:
            candidato = f'{candidato}{u.id}'
        u.username = candidato
        usados.add(candidato)
    db.session.commit()

with app.app_context():
    actualizar_columnas()
    rellenar_usernames()                                              # NUEVO
    comprobar_esquema(db)                                            # NUEVO

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

def dias_a_lista(texto):
    """'0,1,4' -> [0, 1, 4]. Lunes=0 ... domingo=6 (igual que date.weekday()). Vacío -> [] (todos los días)."""
    if not texto:
        return []
    return sorted({int(x) for x in texto.split(',') if x.strip().isdigit()})


def leer_repeticion(data):
    """Interpreta lo que manda el navegador. Devuelve (es_repetitiva, dias_texto, error)."""
    repeticion = data.get('repeticion')
    if repeticion is None:                       # formato antiguo: solo es_repetitiva
        return bool(data.get('es_repetitiva', False)), None, None
    if repeticion == 'una':
        return False, None, None
    if repeticion == 'diaria':
        return True, None, None
    if repeticion == 'dias':
        dias = data.get('dias')
        if (not isinstance(dias, list) or not dias or
                any(isinstance(d, bool) or not isinstance(d, int) or not 0 <= d <= 6 for d in dias)):
            return None, None, 'Elige al menos un día de la semana'
        dias = sorted(set(dias))
        if len(dias) == 7:                       # los 7 días = todos los días
            return True, None, None
        return True, ','.join(str(d) for d in dias), None
    return None, None, 'Tipo de repetición inválido'


def primera_fecha_valida(fecha, dias):
    """Si la fecha cae en un día no elegido, avanza hasta el primer día elegido."""
    dia = datetime.strptime(fecha, '%Y-%m-%d').date()
    if dias:
        for _ in range(7):
            if dia.weekday() in dias:
                break
            dia += timedelta(days=1)
    return dia.isoformat()


def siguiente_fecha(fecha_local, hora_local, hora_alarma, dias=None):
    """Próxima fecha de una alarma repetitiva que acaba de sonar (respetando los días elegidos)."""
    dia = datetime.strptime(fecha_local, '%Y-%m-%d').date()
    if hora_alarma <= hora_local:
        dia += timedelta(days=1)
    return primera_fecha_valida(dia.isoformat(), dias)

def alarma_a_dict(a):
    return {
        'id': a.id,
        'titulo': a.titulo,
        'hora': a.hora,
        'fecha': a.fecha,
        'es_repetitiva': a.es_repetitiva,
        'activa': a.activa,
        'ultima_vez_sono': (a.ultima_vez_sono.replace(tzinfo=timezone.utc).isoformat()
                            if a.ultima_vez_sono else None),
        'dosis': a.dosis,
        'dias': dias_a_lista(a.dias_semana)      # [] = todos los días
    }

def usuario_actual():
    user_id = session.get('user_id')
    return db.session.get(User, user_id) if user_id else None

# ---------------- RUTAS DE LOGIN, REGISTRO Y LOGOUT ----------------
# CAMBIADO: el login ahora busca por username (único), no por nombre
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        username = normalizar_username(data.get('username'))
        password = data.get('password') or ''

        usuario = User.query.filter_by(username=username).first() if username else None
        if usuario and usuario.check_password(password):
            session.clear()
            session['user_id'] = usuario.id
            session['rol'] = usuario.rol
            session['nombre'] = usuario.nombre
            
            if usuario.rol == 'supervisor':
                return redirect(url_for('supervisor'))
            return redirect(url_for('inicio'))
            
        # Mensaje genérico: no decimos si falló el usuario o la contraseña
        return render_template('login.html', error="Usuario o contraseña incorrectos"), 401
    return render_template('login.html')

# NUEVO: cualquiera puede crear su cuenta (paciente o supervisor)
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'GET':
        return render_template('registro.html', valores={})

    data = request.form
    nombre = (data.get('nombre') or '').strip()
    apellidos = (data.get('apellidos') or '').strip()
    username = normalizar_username(data.get('username'))
    password = data.get('password') or ''
    rol = data.get('rol')

    error = None
    if not nombre or len(nombre) > 100 or len(apellidos) > 120:
        error = 'Escribe tu nombre (y apellidos de forma razonable)'
    elif rol not in ('dependiente', 'supervisor'):
        error = 'Elige un tipo de cuenta'
    else:
        error = validar_username(username) or validar_password(password)
        if not error and password != data.get('password2'):
            error = 'Las contraseñas no coinciden'
        if not error and User.query.filter_by(username=username).first():
            error = 'Ese nombre de usuario ya está en uso'

    if error:
        return render_template('registro.html', error=error, valores=data), 400

    usuario = User(nombre=nombre, apellidos=apellidos or None, username=username, rol=rol)
    usuario.set_password(password)
    db.session.add(usuario)
    if not guardar_en_bd():
        return render_template('registro.html', error='No se pudo crear la cuenta. Inténtalo de nuevo.', valores=data), 500

    # Al registrarse entra directamente con su cuenta
    session.clear()
    session['user_id'] = usuario.id
    session['rol'] = usuario.rol
    session['nombre'] = usuario.nombre
    return redirect(url_for('supervisor') if usuario.rol == 'supervisor' else url_for('inicio'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
# --------------------------------------------------------

# Rutas principales protegidas con sesión:
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
    
    if datetime.strptime(data['fecha'], '%Y-%m-%d').date() < hoy_madrid() - timedelta(days=1):
        return jsonify({'error': 'La fecha no puede estar en el pasado'}), 400

    es_repetitiva, dias_texto, error = leer_repeticion(data)
    if error: return jsonify({'error': error}), 400
    # Si el primer día no encaja con los días marcados, empieza el siguiente día marcado
    fecha_inicio = primera_fecha_valida(data['fecha'], dias_a_lista(dias_texto))

    nueva_alarma = Alarm(
        user_id=user_id,
        titulo=titulo,
        hora=data.get('hora'),
        fecha=fecha_inicio,
        es_repetitiva=es_repetitiva,
        dias_semana=dias_texto,
        dosis=((data.get('dosis') or '').strip()[:50] or None)
    )
    db.session.add(nueva_alarma)
    if not guardar_en_bd():
        return jsonify({'error': 'No se pudo guardar la alarma'}), 500
    return jsonify({'mensaje': 'Alarma configurada', 'alarma': alarma_a_dict(nueva_alarma)}), 201

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
    user_id = session.get('user_id')
    if not user_id: return jsonify({'error': 'No autorizado'}), 401

    alarma = db.session.get(Alarm, alarma_id)
    if not alarma: return jsonify({'error': 'Alarma no encontrada'}), 404

    # la alarma tiene que ser del usuario que llama
    if alarma.user_id != user_id: return jsonify({'error': 'Prohibido'}), 403

    data = request.get_json(silent=True) or {}
    if 'fecha' in data and not fecha_valida(data['fecha']): return jsonify({'error': 'Fecha inválida'}), 400
    if 'activa' in data: alarma.activa = bool(data['activa'])
    else: alarma.activa = not alarma.activa
    if 'fecha' in data: alarma.fecha = data['fecha']
    if alarma.activa and alarma.fecha and alarma.dias_semana:
        alarma.fecha = primera_fecha_valida(alarma.fecha, dias_a_lista(alarma.dias_semana))
    if not guardar_en_bd(): return jsonify({'error': 'Error al guardar'}), 500
    return jsonify({'mensaje': 'Actualizado', 'alarma_id': alarma.id, 'activa': alarma.activa}), 200

@app.route('/api/alarmas/<int:alarma_id>', methods=['DELETE'])
def eliminar_alarma(alarma_id):
    user_id = session.get('user_id')
    if not user_id: return jsonify({'error': 'No autorizado'}), 401

    alarma = db.session.get(Alarm, alarma_id)
    if not alarma: return jsonify({'error': 'Alarma no encontrada'}), 404
    if alarma.user_id != user_id: return jsonify({'error': 'Prohibido'}), 403   # solo borra las suyas

    db.session.delete(alarma)
    if not guardar_en_bd(): return jsonify({'error': 'No se pudo eliminar la alarma'}), 500
    return jsonify({'mensaje': 'Alarma eliminada'}), 200

def fecha_local_plausible(fecha_local):
    """3.13: la fecha que manda el móvil no puede diferir más de 1 día de la de Madrid."""
    dia = datetime.strptime(fecha_local, '%Y-%m-%d').date()
    return abs((dia - hoy_madrid()).days) <= 1

@app.route('/api/alarmas/<int:alarma_id>/sonada', methods=['POST'])
def alarma_sonada(alarma_id):
    user_id = session.get('user_id')
    if not user_id: return jsonify({'error': 'No autorizado'}), 401

    alarma = db.session.get(Alarm, alarma_id)
    if not alarma: return jsonify({'error': 'Alarma no encontrada'}), 404

    # la alarma tiene que ser del usuario que llama
    if alarma.user_id != user_id: return jsonify({'error': 'Prohibido'}), 403

    data = request.get_json(silent=True) or {}
    fecha_local, hora_local, fecha_prevista = data.get('fecha_local'), data.get('hora_local'), data.get('fecha_prevista')
    if not (fecha_valida(fecha_local) and hora_valida(hora_local) and fecha_valida(fecha_prevista)):
        return jsonify({'error': 'Datos faltantes'}), 400
    if not fecha_local_plausible(fecha_local):
        return jsonify({'error': 'La fecha de tu dispositivo no es correcta'}), 400
    registro = RegistroToma.query.filter_by(alarma_id=alarma.id, fecha_prevista=fecha_prevista, hora_prevista=alarma.hora, dosis=alarma.dosis).first()
    if not registro:
        registro = RegistroToma(alarma_id=alarma.id, user_id=alarma.user_id, titulo=alarma.titulo, fecha_prevista=fecha_prevista, hora_prevista=alarma.hora, dosis=alarma.dosis)
        db.session.add(registro)
    if alarma.activa and alarma.fecha == fecha_prevista:
        alarma.ultima_vez_sono = ahora()
        if alarma.es_repetitiva: alarma.fecha = siguiente_fecha(fecha_local, hora_local, alarma.hora, dias_a_lista(alarma.dias_semana))
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
    user_id = session.get('user_id')
    if not user_id: return jsonify({'error': 'No autorizado'}), 401

    toma = db.session.get(RegistroToma, toma_id)
    if not toma: return jsonify({'error': 'Toma no encontrada'}), 404

    # la toma tiene que ser del usuario que llama
    if toma.user_id != user_id: return jsonify({'error': 'Prohibido'}), 403

    if toma.estado != 'CONFIRMADA':
        toma.estado = 'CONFIRMADA'
        toma.confirmada_en = ahora()
        if not guardar_en_bd(): return jsonify({'error': 'Error base de datos'}), 500
    return jsonify({'mensaje': 'Toma confirmada'}), 200

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

# ---------------- APARTADO "MI SALUD" ----------------
def paciente_actual():
    """Devuelve (usuario, None) o (None, respuesta_de_error)."""
    usuario = usuario_actual()
    if not usuario: return None, (jsonify({'error': 'No autorizado'}), 401)
    if usuario.rol != 'dependiente': return None, (jsonify({'error': 'Prohibido'}), 403)
    return usuario, None

@app.route('/api/mi-salud', methods=['GET'])
def mi_salud():
    usuario, error = paciente_actual()
    if error: return error
    ficha = usuario.ficha_medica
    imc = None
    if usuario.peso and usuario.altura:
        altura_m = usuario.altura / 100 if usuario.altura > 3 else usuario.altura  # admite cm o m
        imc = round(usuario.peso / (altura_m ** 2), 1)
    return jsonify({
        'nombre_completo': usuario.nombre_completo,
        'edad': usuario.edad,
        'peso': usuario.peso,
        'altura': usuario.altura,
        'imc': imc,
        'grupo_sanguineo': ficha.grupo_sanguineo if ficha else None,
        'alergias': ficha.alergias if ficha else None,
        'enfermedades_cronicas': ficha.enfermedades_cronicas if ficha else None,
        'medicacion': ficha.medicacion if ficha else None,
        'contacto_emergencia': (f"{ficha.contacto_emergencia_nombre} ({ficha.contacto_emergencia_telefono})"
                                if ficha and ficha.contacto_emergencia_nombre else None)
    })

@app.route('/api/mi-peso', methods=['GET'])
def listar_peso():
    usuario, error = paciente_actual()
    if error: return error
    registros = (PesoRegistro.query.filter_by(user_id=usuario.id)
                 .order_by(PesoRegistro.fecha, PesoRegistro.id).all())
    return jsonify([{'fecha': r.fecha, 'kg': r.kg} for r in registros])

@app.route('/api/mi-peso', methods=['POST'])
def anadir_peso():
    usuario, error = paciente_actual()
    if error: return error
    data = request.get_json(silent=True) or {}
    try:
        kg = float(data.get('kg'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Peso inválido'}), 400
    if not 20 <= kg <= 300: return jsonify({'error': 'El peso debe estar entre 20 y 300 kg'}), 400
    fecha = data.get('fecha')
    if not fecha_valida(fecha): return jsonify({'error': 'Fecha inválida'}), 400
    if fecha > hoy_madrid().isoformat(): return jsonify({'error': 'La fecha no puede ser futura'}), 400

    # Si es el pesaje más reciente, actualiza también el peso "actual" del usuario
    ultimo = (PesoRegistro.query.filter_by(user_id=usuario.id)
              .order_by(PesoRegistro.fecha.desc(), PesoRegistro.id.desc()).first())
    db.session.add(PesoRegistro(user_id=usuario.id, fecha=fecha, kg=round(kg, 1)))
    if not ultimo or fecha >= ultimo.fecha:
        usuario.peso = round(kg, 1)
    if not guardar_en_bd(): return jsonify({'error': 'No se pudo guardar el peso'}), 500
    return jsonify({'mensaje': 'Peso guardado'}), 201

@app.route('/api/mi-historial-tomas', methods=['GET'])
def historial_tomas():
    usuario, error = paciente_actual()
    if error: return error
    dias = max(1, min(request.args.get('dias', 30, type=int), 365))
    desde = (hoy_madrid() - timedelta(days=dias)).isoformat()
    tomas = (RegistroToma.query
             .filter(RegistroToma.user_id == usuario.id, RegistroToma.fecha_prevista >= desde)
             .order_by(RegistroToma.fecha_prevista.desc(), RegistroToma.hora_prevista.desc()).all())
    return jsonify([{
        'titulo': t.titulo, 'dosis': t.dosis,
        'fecha_prevista': t.fecha_prevista, 'hora_prevista': t.hora_prevista,
        'estado': t.estado,
        'confirmada_en': (t.confirmada_en.replace(tzinfo=timezone.utc).isoformat()
                          if t.confirmada_en else None)
    } for t in tomas])

# ---------------- VINCULACIÓN SUPERVISOR <-> PACIENTE (código y QR) ----------------
def fallos_recientes(user_id, ip):
    """Canjes fallidos en los últimos 10 min de esta cuenta O de esta IP."""
    desde = (ahora() - timedelta(minutes=VENTANA_MINUTOS)).replace(tzinfo=None)
    return IntentoVinculo.query.filter(
        IntentoVinculo.fecha >= desde,
        or_(IntentoVinculo.user_id == user_id, IntentoVinculo.ip == ip)
    ).count()

@app.route('/api/vinculos/codigo', methods=['POST'])
def crear_codigo_vinculo():
    """El PACIENTE genera un código de un solo uso, válido 10 minutos."""
    paciente, error = paciente_actual()
    if error: return error

    # Un código nuevo invalida los anteriores que no se hubieran usado
    CodigoVinculo.query.filter_by(paciente_id=paciente.id, usado=False).update({'usado': True})

    for _ in range(5):
        codigo = generar_codigo()
        if not CodigoVinculo.query.filter_by(codigo_hash=hash_codigo(codigo)).first():
            break
    else:
        return jsonify({'error': 'No se pudo generar el código'}), 500

    expira = ahora() + timedelta(minutes=MINUTOS_VALIDEZ)
    db.session.add(CodigoVinculo(paciente_id=paciente.id, codigo_hash=hash_codigo(codigo), expira=expira))
    if not guardar_en_bd(): return jsonify({'error': 'No se pudo guardar el código'}), 500

    # El QR contiene una URL que abre la pantalla de vincular con el código ya escrito
    url = request.host_url + 'vincular?c=' + codigo
    return jsonify({
        'codigo': formatear_codigo(codigo),
        'expira': expira.isoformat(),
        'minutos': MINUTOS_VALIDEZ,
        'url': url,
        'qr': generar_qr(url)
    }), 201

@app.route('/api/vinculos/canjear', methods=['POST'])
def canjear_codigo_vinculo():
    """El SUPERVISOR introduce el código y queda vinculado con el paciente."""
    sup = usuario_actual()
    if not sup: return jsonify({'error': 'No autorizado'}), 401
    if sup.rol != 'supervisor': return jsonify({'error': 'Prohibido'}), 403

    ip = request.remote_addr or ''
    # Se comprueba ANTES de mirar el código: durante el bloqueo ni el código bueno sirve
    if fallos_recientes(sup.id, ip) >= MAX_FALLOS:
        return jsonify({'error': 'Demasiados intentos fallidos. Espera 10 minutos e inténtalo de nuevo.'}), 429

    data = request.get_json(silent=True) or {}
    codigo = normalizar_codigo(data.get('codigo'))
    registro = None
    if formato_valido(codigo):
        registro = CodigoVinculo.query.filter_by(codigo_hash=hash_codigo(codigo)).first()

    # Inexistente, ya usado y caducado dan EXACTAMENTE la misma respuesta
    invalido = (registro is None or registro.usado or
                registro.expira.replace(tzinfo=timezone.utc) < ahora())
    if invalido:
        db.session.add(IntentoVinculo(user_id=sup.id, ip=ip))
        guardar_en_bd()
        return jsonify({'error': MENSAJE_CODIGO_INVALIDO}), 400

    paciente = db.session.get(User, registro.paciente_id)
    if not paciente or paciente.rol != 'dependiente':
        return jsonify({'error': MENSAJE_CODIGO_INVALIDO}), 400

    # Marcar como usado de forma atómica: si dos supervisores lo canjean a la vez, solo gana uno
    filas = CodigoVinculo.query.filter_by(id=registro.id, usado=False).update({'usado': True})
    if filas == 0:
        db.session.rollback()
        return jsonify({'error': MENSAJE_CODIGO_INVALIDO}), 400

    ya_vinculado = paciente in sup.dependientes
    if not ya_vinculado:
        sup.dependientes.append(paciente)
    if not guardar_en_bd(): return jsonify({'error': 'No se pudo completar la vinculación'}), 500

    mensaje = ('Ya estabas vinculado con ' if ya_vinculado else 'Vinculado correctamente con ') + paciente.nombre_completo
    return jsonify({'mensaje': mensaje,
                    'paciente': {'id': paciente.id, 'nombre': paciente.nombre_completo}}), 200

@app.route('/vincular')
def pagina_vincular():
    sup = usuario_actual()
    if not sup or sup.rol != 'supervisor':
        return redirect(url_for('login'))
    # Si el supervisor llega desde el QR, el código viene en ?c= y se rellena solo (NO se canjea con un GET)
    return render_template('vincular.html', usuario=sup, codigo=request.args.get('c', '')[:20])

@app.route('/api/hora', methods=['GET'])
def hora_servidor():
    """3.13: el móvil compara su reloj con este. No necesita sesión y no devuelve datos personales."""
    en_madrid = datetime.now(ZONA)
    return jsonify({
        'ahora_utc': datetime.now(timezone.utc).isoformat(),
        'fecha': en_madrid.date().isoformat(),
        'hora': en_madrid.strftime('%H:%M'),
        'zona': 'Europe/Madrid'
    })

@app.errorhandler(500)
def error_interno(e):
    return jsonify({'error': 'Error interno del servidor'}), 500

if __name__ == '__main__':
    app.run(debug=True)