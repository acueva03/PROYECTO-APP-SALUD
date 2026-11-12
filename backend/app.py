import os
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone, date
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from sqlalchemy import inspect, text, or_
from models import (db, User, Alarm, HealthMetric, AlertSOS, MedicalProfile, RegistroToma,
                    PesoRegistro, CodigoVinculo, IntentoVinculo, IntentoLogin, VinculoLog,
                    ahora, hoy_madrid, ZONA)
# NUEVO: reglas de usuario y contraseña
from validaciones import (normalizar_username, validar_username,
                          validar_password, username_desde_nombre)
from ficha import validar_ficha
from esquema import comprobar_esquema
from vinculos import (generar_codigo, normalizar_codigo, formato_valido, hash_codigo,
                      formatear_codigo, generar_qr, MINUTOS_VALIDEZ, MAX_FALLOS,
                      VENTANA_MINUTOS, MENSAJE_CODIGO_INVALIDO)
from supervisor_bp import supervisor_bp, paciente_supervisado_o_403, clave_orden
try:
    from dotenv import load_dotenv
except ImportError:      # sin python-dotenv solo se usan las variables del sistema
    load_dotenv = None

# Lee backend/.env (SECRET_KEY, PRODUCCION...). Ese archivo NO se sube a GitHub (.gitignore)
if load_dotenv:
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))


app = Flask(__name__, 
            template_folder='../frontend/templates', 
            static_folder='../frontend/static')

# Configuración de sesiones para el login seguro
# Sesiones seguras (riesgos 3.15 y 3.17)
clave = os.environ.get('SECRET_KEY')
if not clave:
    clave = secrets.token_hex(32)
    print('AVISO: no hay SECRET_KEY en backend/.env. Se usa una clave temporal: las sesiones se cerrarán al reiniciar.')
app.config['SECRET_KEY'] = clave
app.config['SESSION_COOKIE_HTTPONLY'] = True                 # JavaScript no puede leer la cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'                # no se envía desde otras webs (anti-CSRF)
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('PRODUCCION') == '1'   # solo por HTTPS en producción
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)               # 3.17: la sesión dura 30 días

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# CAMBIADO: si existe la variable DATABASE_URL (la usan los tests) se usa esa base de datos;
# si no, la real app_salud.db
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or ('sqlite:///' + os.path.join(BASE_DIR, 'app_salud.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'check_same_thread': False, 'timeout': 15}
}

db.init_app(app)

app.register_blueprint(supervisor_bp)      # activa las rutas de supervisor_bp.py

with app.app_context(): 
    db.create_all()

def actualizar_columnas():
    necesarias = {
        'alarms': [('fecha', 'VARCHAR(10)'),
                   ('ultima_vez_sono', 'DATETIME'),
                   ('dosis', 'VARCHAR(50)'),
                   ('dias_semana', 'VARCHAR(20)'),
                   ('eliminada', 'BOOLEAN NOT NULL DEFAULT 0'),     # riesgo 3.14 (borrado lógico)
                   ('eliminada_en', 'DATETIME')],
        'registros_toma': [('dosis', 'VARCHAR(50)')],
        'users': [('username', 'VARCHAR(50)'),
          ('password_hash', 'VARCHAR(256)')],                       # NUEVO 
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
MAX_FALLOS_LOGIN = 5          # riesgo 3.15: fallos permitidos...
VENTANA_LOGIN_MINUTOS = 10    # ...en esta ventana de tiempo, por usuario e IP

def fallos_login_recientes(username, ip):
    """Logins fallidos en los últimos 10 min de ESTE usuario desde ESTA IP."""
    desde = (ahora() - timedelta(minutes=VENTANA_LOGIN_MINUTOS)).replace(tzinfo=None)
    return IntentoLogin.query.filter(
        IntentoLogin.fecha >= desde,
        IntentoLogin.username == username,
        IntentoLogin.ip == ip
    ).count()

# CAMBIADO: el login busca por username (único) y se bloquea tras 5 fallos
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        username = normalizar_username(data.get('username'))[:50]
        password = data.get('password') or ''
        ip = request.remote_addr or ''

        # Se comprueba ANTES de mirar la contraseña: durante el bloqueo ni la buena sirve.
        # Vale igual para usuarios que no existen, así no se revela quién tiene cuenta.
        if username and fallos_login_recientes(username, ip) >= MAX_FALLOS_LOGIN:
            return render_template('login.html',
                                   error='Demasiados intentos fallidos. Espera 10 minutos e inténtalo de nuevo.'), 429

        usuario = User.query.filter_by(username=username).first() if username else None
        if usuario and usuario.check_password(password):
            IntentoLogin.query.filter_by(username=username, ip=ip).delete()   # acierta: contador a cero
            guardar_en_bd()
            session.clear()
            session.permanent = True            # 3.17: la sesión dura 30 días
            session['user_id'] = usuario.id
            session['rol'] = usuario.rol
            session['nombre'] = usuario.nombre

            if usuario.rol == 'supervisor':
                return redirect(url_for('supervisor'))
            return redirect(url_for('inicio'))

        # Fallo: se anota (y se limpian los antiguos para que la tabla no crezca sin fin)
        if username:
            limite = (ahora() - timedelta(days=1)).replace(tzinfo=None)
            IntentoLogin.query.filter(IntentoLogin.fecha < limite).delete()
            db.session.add(IntentoLogin(username=username, ip=ip))
            guardar_en_bd()

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
    session.permanent = True            # 3.17: la sesión dura 30 días
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
       # CAMBIADO: se pasan TODOS los pacientes, por orden alfabético
    pacientes = sorted(usuario.dependientes, key=lambda p: clave_orden(p.nombre_completo))
    return render_template('supervisor.html', usuario=usuario, pacientes=pacientes)

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
    alarmas = [a for a in usuario.alarmas if not a.eliminada and (incluir_todas or a.activa)]
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
                resultado.append({'alerta_id': a.id, 'dependiente': dep.nombre, 'dependiente_id': dep.id,
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
    if alarma.eliminada: return jsonify({'error': 'Alarma no encontrada'}), 404   # 3.14: está en la papelera

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
    if alarma.eliminada: return jsonify({'error': 'Alarma no encontrada'}), 404  # ya estaba en la papelera

    # Riesgo 3.14: borrado LÓGICO. La alarma deja de sonar y de listarse, pero se puede recuperar.
    alarma.eliminada = True
    alarma.eliminada_en = ahora()
    if not guardar_en_bd(): return jsonify({'error': 'No se pudo eliminar la alarma'}), 500
    return jsonify({'mensaje': 'Alarma eliminada', 'alarma_id': alarma.id}), 200

# ---------------- PAPELERA DE ALARMAS (riesgo 3.14) ----------------
DIAS_PAPELERA = 30      # la papelera muestra lo eliminado en los últimos 30 días

def eliminadas_de(user_id):
    """Alarmas eliminadas recientemente, la más reciente primero."""
    desde = (ahora() - timedelta(days=DIAS_PAPELERA)).replace(tzinfo=None)
    alarmas = (Alarm.query.filter(Alarm.user_id == user_id, Alarm.eliminada.is_(True),
                                  Alarm.eliminada_en >= desde)
               .order_by(Alarm.eliminada_en.desc()).all())
    resultado = []
    for a in alarmas:
        d = alarma_a_dict(a)
        d['eliminada_en'] = a.eliminada_en.replace(tzinfo=timezone.utc).isoformat()
        resultado.append(d)
    return resultado

def reprogramar_si_ya_paso(alarma):
    """Al recuperar una alarma activa cuya hora ya pasó, la mueve a la próxima vez que toque
    (si no, sonaría nada más recuperarla como «perdida»)."""
    if not alarma.activa:
        return
    ahora_madrid = datetime.now(ZONA)
    hoy, hora_actual = ahora_madrid.date(), ahora_madrid.strftime('%H:%M')
    if alarma.fecha and (alarma.fecha, alarma.hora) > (hoy.isoformat(), hora_actual):
        return                                          # todavía no ha llegado: se queda como estaba
    dia = hoy if alarma.hora > hora_actual else hoy + timedelta(days=1)
    alarma.fecha = primera_fecha_valida(dia.isoformat(), dias_a_lista(alarma.dias_semana))

@app.route('/api/mis-alarmas-eliminadas', methods=['GET'])
def listar_alarmas_eliminadas():
    usuario, error = paciente_actual()
    if error: return error
    return jsonify(eliminadas_de(usuario.id))

@app.route('/api/alarmas/<int:alarma_id>/restaurar', methods=['POST'])
def restaurar_alarma(alarma_id):
    """La recupera el propio paciente o un supervisor vinculado a él (3.14.3)."""
    usuario = usuario_actual()
    if not usuario: return jsonify({'error': 'No autorizado'}), 401
    alarma = db.session.get(Alarm, alarma_id)
    if not alarma: return jsonify({'error': 'Alarma no encontrada'}), 404
    es_suya = alarma.user_id == usuario.id
    es_su_supervisor = usuario.rol == 'supervisor' and alarma.usuario in usuario.dependientes
    if not (es_suya or es_su_supervisor): return jsonify({'error': 'Prohibido'}), 403
    if not alarma.eliminada: return jsonify({'error': 'Esta alarma no está eliminada'}), 409

    alarma.eliminada = False
    alarma.eliminada_en = None
    reprogramar_si_ya_paso(alarma)
    if not guardar_en_bd(): return jsonify({'error': 'No se pudo recuperar la alarma'}), 500
    return jsonify({'mensaje': 'Alarma recuperada', 'alarma': alarma_a_dict(alarma)}), 200

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
    if alarma.eliminada: return jsonify({'error': 'Alarma no encontrada'}), 404   # 3.14

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
    return {'toma_id': t.id, 'titulo': t.titulo, 'dosis': t.dosis, 'fecha_prevista': t.fecha_prevista, 'hora_prevista': t.hora_prevista, 'estado': t.estado, 'creado': t.creado.replace(tzinfo=timezone.utc).isoformat()}

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

# Riesgo 3.16.3: "Deshacer" durante 1 minuto. El servidor da 30 s de margen por la red.
SEGUNDOS_PARA_DESHACER = 90

@app.route('/api/tomas/<int:toma_id>/deshacer', methods=['POST'])
def deshacer_toma(toma_id):
    user_id = session.get('user_id')
    if not user_id: return jsonify({'error': 'No autorizado'}), 401
    toma = db.session.get(RegistroToma, toma_id)
    if not toma: return jsonify({'error': 'Toma no encontrada'}), 404
    if toma.user_id != user_id: return jsonify({'error': 'Prohibido'}), 403
    if toma.estado != 'CONFIRMADA' or not toma.confirmada_en:
        return jsonify({'error': 'Esta toma no está confirmada'}), 409
    if ahora() - toma.confirmada_en.replace(tzinfo=timezone.utc) > timedelta(seconds=SEGUNDOS_PARA_DESHACER):
        return jsonify({'error': 'Ya no se puede deshacer'}), 409
    toma.estado = 'PENDIENTE'
    toma.confirmada_en = None
    if not guardar_en_bd(): return jsonify({'error': 'Error base de datos'}), 500
    return jsonify({'mensaje': 'Toma pendiente de nuevo'}), 200

@app.route('/api/mis-tomas-pendientes', methods=['GET'])
def tomas_pendientes():
    user_id = session.get('user_id')
    if not user_id: return jsonify({'error': 'No autorizado'}), 401
    return jsonify([toma_a_dict(t) for t in tomas_pendientes_de(user_id, 6)])

# Riesgo 3.12.3: si la pantalla del paciente estaba cerrada, la alarma nunca suena y no se crea
# ningún RegistroToma, así que el supervisor no se enteraba. Una alarma ACTIVA cuya hora pasó hace
# más de 15 minutos es una alarma que no ha sonado: al sonar, su fecha avanza o se desactiva.
MINUTOS_SIN_SONAR = 15

def alarmas_sin_sonar_de(user_id, horas=24):
    ahora_madrid = datetime.now(ZONA)
    limite_reciente = ahora_madrid - timedelta(minutes=MINUTOS_SIN_SONAR)
    limite_antiguo = ahora_madrid - timedelta(hours=horas)
    resultado = []
    for a in Alarm.query.filter_by(user_id=user_id, activa=True, eliminada=False).all():
        if not a.fecha:
            continue
        try:
            momento = datetime.strptime(a.fecha + ' ' + a.hora, '%Y-%m-%d %H:%M').replace(tzinfo=ZONA)
        except ValueError:
            continue
        if not (limite_antiguo <= momento <= limite_reciente):
            continue
        # Si ya hay registro de toma para esa fecha y hora, sí sonó (y ya sale como toma pendiente)
        if RegistroToma.query.filter_by(alarma_id=a.id, fecha_prevista=a.fecha, hora_prevista=a.hora).first():
            continue
        resultado.append((a, momento))
    return resultado

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
            d['dependiente_id'] = dep.id      
            resultado.append(d)
        # 3.12.3: mismo formato que una toma pendiente, para que el panel las muestre como "sin confirmar"
        for a, momento in alarmas_sin_sonar_de(dep.id, 24):
            resultado.append({'toma_id': None, 'titulo': a.titulo + ' (no ha sonado en su móvil)',
                              'dosis': a.dosis, 'fecha_prevista': a.fecha, 'hora_prevista': a.hora,
                              'estado': 'NO_SONO', 'sin_sonar': True,
                              'creado': momento.astimezone(timezone.utc).isoformat(),
                              'dependiente': dep.nombre, 'dependiente_id': dep.id})
    return jsonify(resultado)

# ---------------- APARTADO "MI SALUD" ----------------
def paciente_actual():
    """Devuelve (usuario, None) o (None, respuesta_de_error)."""
    usuario = usuario_actual()
    if not usuario: return None, (jsonify({'error': 'No autorizado'}), 401)
    if usuario.rol != 'dependiente': return None, (jsonify({'error': 'Prohibido'}), 403)
    return usuario, None

def datos_salud(usuario):
    """Datos de salud de un usuario. Los usan el paciente y su supervisor."""
    ficha = usuario.ficha_medica
    imc = None
    if usuario.peso and usuario.altura:
        altura_m = usuario.altura / 100 if usuario.altura > 3 else usuario.altura  # admite cm o m
        imc = round(usuario.peso / (altura_m ** 2), 1)
    return {
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
    }

def pesos_de(user_id):
    registros = (PesoRegistro.query.filter_by(user_id=user_id)
                 .order_by(PesoRegistro.fecha, PesoRegistro.id).all())
    return [{'fecha': r.fecha, 'kg': r.kg} for r in registros]

def tomas_de(user_id, dias):
    dias = max(1, min(dias, 365))
    desde = (hoy_madrid() - timedelta(days=dias)).isoformat()
    tomas = (RegistroToma.query
             .filter(RegistroToma.user_id == user_id, RegistroToma.fecha_prevista >= desde)
             .order_by(RegistroToma.fecha_prevista.desc(), RegistroToma.hora_prevista.desc()).all())
    return [{
        'titulo': t.titulo, 'dosis': t.dosis,
        'fecha_prevista': t.fecha_prevista, 'hora_prevista': t.hora_prevista,
        'estado': t.estado,
        'confirmada_en': (t.confirmada_en.replace(tzinfo=timezone.utc).isoformat()
                          if t.confirmada_en else None)
    } for t in tomas]

@app.route('/api/mi-salud', methods=['GET'])
def mi_salud():
    usuario, error = paciente_actual()
    if error: return error
    return jsonify(datos_salud(usuario))

@app.route('/api/mi-peso', methods=['GET'])
def listar_peso():
    usuario, error = paciente_actual()
    if error: return error
    return jsonify(pesos_de(usuario.id))

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

# ---------------- EDITAR FICHA MÉDICA Y DATOS PERSONALES (el propio paciente) ----------------
CAMPOS_FICHA = ('grupo_sanguineo', 'alergias', 'enfermedades_cronicas', 'medicacion',
                'contacto_emergencia_nombre', 'contacto_emergencia_telefono')

@app.route('/api/mi-ficha', methods=['GET'])
def leer_ficha():
    usuario, error = paciente_actual()
    if error: return error
    ficha = usuario.ficha_medica
    datos = {'edad': usuario.edad, 'altura': usuario.altura, 'telefono': usuario.telefono}
    for campo in CAMPOS_FICHA:
        datos[campo] = getattr(ficha, campo) if ficha else None
    return jsonify(datos)

@app.route('/api/mi-ficha', methods=['PUT'])
def guardar_ficha():
    usuario, error = paciente_actual()
    if error: return error
    limpio, mensaje = validar_ficha(request.get_json(silent=True))
    if mensaje: return jsonify({'error': mensaje}), 400

    usuario.edad = limpio['edad']
    usuario.altura = limpio['altura']
    usuario.telefono = limpio['telefono']
    ficha = usuario.ficha_medica
    if not ficha:                                   # pacientes nuevos: aún no tienen ficha
        ficha = MedicalProfile(user_id=usuario.id)
        db.session.add(ficha)
    for campo in CAMPOS_FICHA:
        setattr(ficha, campo, limpio[campo])
    if not guardar_en_bd(): return jsonify({'error': 'No se pudieron guardar los datos'}), 500
    return jsonify({'mensaje': 'Datos guardados'}), 200

@app.route('/api/mi-historial-tomas', methods=['GET'])
def historial_tomas():
    usuario, error = paciente_actual()
    if error: return error
    return jsonify(tomas_de(usuario.id, request.args.get('dias', 30, type=int)))

# ---------------- SALUD DEL PACIENTE, VISTA DEL SUPERVISOR (solo lectura) ----------------

@app.route('/api/supervisor/pacientes/<int:paciente_id>/salud', methods=['GET'])
def supervisor_salud(paciente_id):
    paciente, error = paciente_supervisado_o_403(paciente_id)
    if error: return error
    return jsonify(datos_salud(paciente))

@app.route('/api/supervisor/pacientes/<int:paciente_id>/peso', methods=['GET'])
def supervisor_peso(paciente_id):
    paciente, error = paciente_supervisado_o_403(paciente_id)
    if error: return error
    return jsonify(pesos_de(paciente.id))

@app.route('/api/supervisor/pacientes/<int:paciente_id>/tomas', methods=['GET'])
def supervisor_tomas(paciente_id):
    paciente, error = paciente_supervisado_o_403(paciente_id)
    if error: return error
    return jsonify(tomas_de(paciente.id, request.args.get('dias', 30, type=int)))

@app.route('/supervisor/salud/<int:paciente_id>')
def pagina_salud_supervisor(paciente_id):
    sup = usuario_actual()
    if not sup or sup.rol != 'supervisor':
        return redirect(url_for('login'))
    paciente = db.session.get(User, paciente_id)
    if not paciente or paciente not in sup.dependientes:
        return redirect(url_for('supervisor'))
    return render_template('supervisor_salud.html', usuario=sup, paciente=paciente)

# ---------------- VINCULACIÓN SUPERVISOR <-> PACIENTE (código y QR) ----------------
# Mensajes claros: así un "Prohibido" no confunde (lo típico en pruebas es tener dos cuentas
# abiertas en el mismo navegador: la cookie de sesión es una sola y la última en entrar gana)
MSG_SESION_CADUCADA = 'Tu sesión ha caducado. Vuelve a iniciar sesión.'
MSG_NO_ES_SUPERVISOR = ('Esta acción es solo para cuentas de supervisor. Si tienes varias pestañas abiertas, '
                        'es posible que hayas iniciado sesión con otra cuenta en este mismo navegador: recarga la página.')
MSG_NO_ES_PACIENTE = ('Esta acción es solo para cuentas de paciente. Si tienes varias pestañas abiertas, '
                      'es posible que hayas iniciado sesión con otra cuenta en este mismo navegador: recarga la página.')

def supervisor_o_error():
    """Devuelve (supervisor, None) o (None, respuesta_de_error) con un mensaje que explica el motivo."""
    usuario = usuario_actual()
    if not usuario: return None, (jsonify({'error': MSG_SESION_CADUCADA}), 401)
    if usuario.rol != 'supervisor': return None, (jsonify({'error': MSG_NO_ES_SUPERVISOR}), 403)
    return usuario, None

def paciente_o_error():
    """Devuelve (paciente, None) o (None, respuesta_de_error) con un mensaje que explica el motivo."""
    usuario = usuario_actual()
    if not usuario: return None, (jsonify({'error': MSG_SESION_CADUCADA}), 401)
    if usuario.rol != 'dependiente': return None, (jsonify({'error': MSG_NO_ES_PACIENTE}), 403)
    return usuario, None

def anotar_vinculo(accion, supervisor_id, paciente_id, iniciado_por):
    """Apunta en el historial un vínculo o desvinculación (se confirma con el commit de quien llama)."""
    db.session.add(VinculoLog(supervisor_id=supervisor_id, paciente_id=paciente_id,
                              accion=accion, iniciado_por=iniciado_por))

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
    paciente, error = paciente_o_error()
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
    sup, error = supervisor_o_error()
    if error: return error

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
        anotar_vinculo('VINCULADO', sup.id, paciente.id, 'SUPERVISOR')
    if not guardar_en_bd(): return jsonify({'error': 'No se pudo completar la vinculación'}), 500

    mensaje = ('Ya estabas vinculado con ' if ya_vinculado else 'Vinculado correctamente con ') + paciente.nombre_completo
    return jsonify({'mensaje': mensaje,
                    'paciente': {'id': paciente.id, 'nombre': paciente.nombre_completo}}), 200

# ---- Ver y deshacer vínculos. Cada parte solo puede tocar SU lado del vínculo ----
@app.route('/api/vinculos/pacientes', methods=['GET'])
def mis_pacientes_vinculados():
    """SUPERVISOR: lista de pacientes con los que está vinculado."""
    sup, error = supervisor_o_error()
    if error: return error
    return jsonify([{'id': p.id, 'nombre': p.nombre_completo} for p in sup.dependientes])

@app.route('/api/vinculos/pacientes/<int:paciente_id>', methods=['DELETE'])
def desvincular_paciente(paciente_id):
    """SUPERVISOR: deja de supervisar a un paciente. Solo quita SU vínculo; otros supervisores no se tocan."""
    sup, error = supervisor_o_error()
    if error: return error

    paciente = db.session.get(User, paciente_id)
    if not paciente or paciente not in sup.dependientes:
        return jsonify({'error': 'No estás vinculado con ese paciente'}), 404

    sup.dependientes.remove(paciente)
    anotar_vinculo('DESVINCULADO', sup.id, paciente.id, 'SUPERVISOR')
    if not guardar_en_bd(): return jsonify({'error': 'No se pudo desvincular. Inténtalo de nuevo.'}), 500
    return jsonify({'mensaje': 'Te has desvinculado de ' + paciente.nombre_completo}), 200

@app.route('/api/vinculos/supervisores', methods=['GET'])
def mis_supervisores():
    """PACIENTE: quién le supervisa (el paciente debe poder saberlo siempre)."""
    paciente, error = paciente_o_error()
    if error: return error
    return jsonify([{'id': s.id, 'nombre': s.nombre_completo} for s in paciente.supervisores])

@app.route('/api/vinculos/supervisores/<int:supervisor_id>', methods=['DELETE'])
def quitar_supervisor(supervisor_id):
    """PACIENTE: revoca el acceso de un supervisor (el supervisor deja de ver sus datos y avisos)."""
    paciente, error = paciente_o_error()
    if error: return error

    sup = db.session.get(User, supervisor_id)
    if not sup or sup not in paciente.supervisores:
        return jsonify({'error': 'Ese supervisor no está vinculado contigo'}), 404

    paciente.supervisores.remove(sup)
    anotar_vinculo('DESVINCULADO', sup.id, paciente.id, 'PACIENTE')
    if not guardar_en_bd(): return jsonify({'error': 'No se pudo quitar al supervisor. Inténtalo de nuevo.'}), 500
    return jsonify({'mensaje': sup.nombre_completo + ' ya no es tu supervisor'}), 200

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