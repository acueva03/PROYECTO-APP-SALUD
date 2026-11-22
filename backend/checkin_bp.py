# checkin_bp.py: Check-in diario «Estoy bien».
#
# Qué hace este archivo:
#   1) API del PACIENTE: hacer el check-in de hoy, ver su estado y configurar la hora límite.
#   2) API del SUPERVISOR: ver el estado de hoy y los últimos 14 días de un paciente SUYO.
#   3) procesar_checkins_perdidos(): la llama el endpoint /interno/tick de notificaciones_bp.py
#      (P4) cada minuto. Si un paciente no ha hecho el check-in y ya pasó su hora límite,
#      avisa a sus supervisores UNA sola vez por día.
#
# IMPORTANTE: este archivo NO importa "app" (así se evitan imports circulares).
# Usa solo models.py, supervisor_bp.py y notificaciones.py.
import re
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request, session
from sqlalchemy.exc import IntegrityError

from models import db, User, CheckIn, CheckinConfig, ahora, hoy_madrid, ZONA
from supervisor_bp import paciente_supervisado_o_403, a_iso_utc
from notificaciones import enviar_a_supervisores_de, ya_avisado, marcar_avisado

checkin_bp = Blueprint('checkin_bp', __name__)

# ---------------------------------------------------------------------------
# Constantes (cámbialas aquí si el equipo decide otros valores)
# ---------------------------------------------------------------------------
HORA_LIMITE_POR_DEFECTO = '11:00'     # hora límite si el paciente no ha configurado nada
HORA_LIMITE_MINIMA = '08:00'          # no se permite una hora límite antes de las 08:00...
HORA_LIMITE_MAXIMA = '23:00'          # ...ni después de las 23:00
CHECKIN_ACTIVO_POR_DEFECTO = True     # ¿tiene check-in un paciente que nunca lo ha configurado?
DIAS_HISTORIAL = 14                   # días que ve el supervisor

# Opciones del selector «¿Cómo te sientes?». El JS las lee de GET /api/mi-checkin,
# así que si añades o quitas una aquí, la pantalla se actualiza sola.
ESTADOS_ANIMO = ['Contento', 'Tranquilo', 'Cansado', 'Triste', 'Ansioso']

MSG_SESION_CADUCADA = 'Tu sesión ha caducado. Vuelve a iniciar sesión.'
MSG_NO_ES_PACIENTE = ('Esta acción es solo para cuentas de paciente. Si tienes varias pestañas abiertas, '
                      'es posible que hayas iniciado sesión con otra cuenta en este mismo navegador: recarga la página.')

# Formato estricto HH:MM (dos dígitos). Evita cosas como "9:00" o "09:00:00".
HORA_RE = re.compile(r'\d\d:\d\d')


# ---------------------------------------------------------------------------
# Utilidades pequeñas
# ---------------------------------------------------------------------------
def hora_madrid():
    """Hora actual en Madrid como 'HH:MM'. Va en una función aparte para poder
    sustituirla en los tests. Siempre la hora del SERVIDOR, nunca la del móvil (riesgo 3.13)."""
    return datetime.now(ZONA).strftime('%H:%M')


def hora_valida(texto):
    """True si es 'HH:MM' real (00:00-23:59)."""
    if not isinstance(texto, str) or not HORA_RE.fullmatch(texto):
        return False
    try:
        datetime.strptime(texto, '%H:%M')
    except ValueError:
        return False
    return True


def paciente_o_error():
    """Devuelve (paciente, None) o (None, respuesta_de_error). Mismo estilo que app.py."""
    user_id = session.get('user_id')
    usuario = db.session.get(User, user_id) if user_id else None
    if not usuario:
        return None, (jsonify({'error': MSG_SESION_CADUCADA}), 401)
    if usuario.rol != 'dependiente':
        return None, (jsonify({'error': MSG_NO_ES_PACIENTE}), 403)
    return usuario, None


def config_de(user_id):
    """Devuelve (activo, hora_limite) del paciente. Si no ha configurado nada, los valores por defecto."""
    fila = CheckinConfig.query.filter_by(user_id=user_id).first()
    if fila:
        return fila.activo, fila.hora_limite
    return CHECKIN_ACTIVO_POR_DEFECTO, HORA_LIMITE_POR_DEFECTO


def hora_local_de(momento_utc):
    """datetime UTC (de la BD, sin zona) -> 'HH:MM' en Madrid."""
    if momento_utc is None:
        return None
    return momento_utc.replace(tzinfo=timezone.utc).astimezone(ZONA).strftime('%H:%M')


def checkin_a_dict(c):
    """Un CheckIn (o None) convertido a diccionario para el JSON."""
    if c is None:
        return {'hecho': False, 'hecho_en': None, 'hora': None, 'estado_animo': None}
    return {'hecho': True, 'hecho_en': a_iso_utc(c.hecho_en),
            'hora': hora_local_de(c.hecho_en), 'estado_animo': c.estado_animo}


def estado_de_hoy(user_id):
    """'HECHO' | 'PENDIENTE' (aún a tiempo) | 'NO_REALIZADO' (ya pasó la hora límite) | 'DESACTIVADO'."""
    hoy = hoy_madrid().isoformat()
    if CheckIn.query.filter_by(user_id=user_id, fecha=hoy).first():
        return 'HECHO'
    activo, limite = config_de(user_id)
    if not activo:
        return 'DESACTIVADO'
    return 'NO_REALIZADO' if hora_madrid() >= limite else 'PENDIENTE'


# ---------------------------------------------------------------------------
# 1) API DEL PACIENTE
# ---------------------------------------------------------------------------
@checkin_bp.route('/api/checkin', methods=['POST'])
def hacer_checkin():
    """El paciente pulsa «Estoy bien». Es IDEMPOTENTE: si ya lo hizo hoy devuelve 200 con el de hoy
    (no crea otro). Si es nuevo, devuelve 201. Cuerpo opcional: {"estado_animo": "Contento"}."""
    paciente, error = paciente_o_error()
    if error:
        return error

    datos = request.get_json(silent=True)
    if datos is None:
        datos = {}
    if not isinstance(datos, dict):
        return jsonify({'error': 'Datos no válidos'}), 400

    animo = datos.get('estado_animo')
    if animo in (None, ''):
        animo = None                                    # el ánimo es opcional
    elif not isinstance(animo, str) or animo not in ESTADOS_ANIMO:
        return jsonify({'error': 'Estado de ánimo no válido'}), 400

    hoy = hoy_madrid().isoformat()                      # siempre la fecha de Madrid (riesgo 3.13)
    existente = CheckIn.query.filter_by(user_id=paciente.id, fecha=hoy).first()
    if existente:
        return jsonify({'mensaje': 'Ya habías confirmado hoy', 'ya_hecho': True, **checkin_a_dict(existente)}), 200

    nuevo = CheckIn(user_id=paciente.id, fecha=hoy, estado_animo=animo)
    db.session.add(nuevo)
    try:
        db.session.commit()
    except IntegrityError:
        # Dos peticiones a la vez (doble toque): la restricción única de la BD frena la segunda
        db.session.rollback()
        existente = CheckIn.query.filter_by(user_id=paciente.id, fecha=hoy).first()
        return jsonify({'mensaje': 'Ya habías confirmado hoy', 'ya_hecho': True, **checkin_a_dict(existente)}), 200
    except Exception as e:
        db.session.rollback()
        print('ERROR de base de datos (check-in):', e)
        return jsonify({'error': 'Error base de datos'}), 500

    return jsonify({'mensaje': 'Check-in guardado', 'ya_hecho': False, **checkin_a_dict(nuevo)}), 201


@checkin_bp.route('/api/mi-checkin', methods=['GET'])
def mi_checkin():
    """Estado de HOY del paciente + su configuración. Lo usa checkin.js al cargar la pantalla."""
    paciente, error = paciente_o_error()
    if error:
        return error
    hoy = hoy_madrid().isoformat()
    hecho = CheckIn.query.filter_by(user_id=paciente.id, fecha=hoy).first()
    activo, limite = config_de(paciente.id)
    return jsonify({
        'fecha': hoy,
        **checkin_a_dict(hecho),
        'activo': activo,
        'hora_limite': limite,
        'estados_animo': ESTADOS_ANIMO,
    })


@checkin_bp.route('/api/mi-checkin/config', methods=['PUT'])
def guardar_config_checkin():
    """Cambia la hora límite (08:00-23:00) y/o activa/desactiva el check-in.
    Cuerpo: {"hora_limite": "10:30", "activo": true}. Lo que no se envíe se deja como estaba."""
    paciente, error = paciente_o_error()
    if error:
        return error
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify({'error': 'Datos no válidos'}), 400

    activo_actual, limite_actual = config_de(paciente.id)
    limite = datos.get('hora_limite', limite_actual)
    activo = datos.get('activo', activo_actual)

    if not hora_valida(limite):
        return jsonify({'error': 'La hora límite no es válida (formato HH:MM)'}), 400
    if not HORA_LIMITE_MINIMA <= limite <= HORA_LIMITE_MAXIMA:    # comparar 'HH:MM' como texto funciona
        return jsonify({'error': f'La hora límite debe estar entre {HORA_LIMITE_MINIMA} y {HORA_LIMITE_MAXIMA}'}), 400
    if not isinstance(activo, bool):
        return jsonify({'error': 'El valor de «activo» no es válido'}), 400

    fila = CheckinConfig.query.filter_by(user_id=paciente.id).first()
    if not fila:
        fila = CheckinConfig(user_id=paciente.id)
        db.session.add(fila)
    fila.hora_limite = limite
    fila.activo = activo
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print('ERROR de base de datos (config check-in):', e)
        return jsonify({'error': 'Error base de datos'}), 500
    return jsonify({'mensaje': 'Configuración guardada', 'activo': fila.activo, 'hora_limite': fila.hora_limite}), 200


# ---------------------------------------------------------------------------
# 2) API DEL SUPERVISOR (solo lectura)
# ---------------------------------------------------------------------------
@checkin_bp.route('/api/supervisor/pacientes/<int:paciente_id>/checkin', methods=['GET'])
def checkin_de_paciente(paciente_id):
    """Estado de hoy y últimos 14 días del paciente. Usa el helper de permisos obligatorio:
    un supervisor NO puede ver pacientes ajenos (403 también para ids inexistentes)."""
    paciente, error = paciente_supervisado_o_403(paciente_id)
    if error:
        return error

    hoy = hoy_madrid()
    primer_dia = (hoy - timedelta(days=DIAS_HISTORIAL - 1)).isoformat()
    filas = CheckIn.query.filter(CheckIn.user_id == paciente.id, CheckIn.fecha >= primer_dia).all()
    por_fecha = {c.fecha: c for c in filas}

    # Una entrada por cada día (del más antiguo al de hoy), haya o no check-in
    dias = []
    for i in range(DIAS_HISTORIAL - 1, -1, -1):
        fecha = (hoy - timedelta(days=i)).isoformat()
        dias.append({'fecha': fecha, **checkin_a_dict(por_fecha.get(fecha))})

    activo, limite = config_de(paciente.id)
    return jsonify({
        'estado_hoy': estado_de_hoy(paciente.id),
        'activo': activo,
        'hora_limite': limite,
        'dias': dias,
    })


# ---------------------------------------------------------------------------
# 3) AVISO DE CHECK-IN NO REALIZADO (la llama /interno/tick de P4)
# ---------------------------------------------------------------------------
def procesar_checkins_perdidos():
    """Para cada paciente con check-in activo, con supervisores, cuya hora límite ya pasó y que
    no ha hecho el check-in de hoy: avisa a sus supervisores UNA sola vez por día.
    Devuelve cuántos avisos se han enviado."""
    avisos_enviados = 0
    hoy = hoy_madrid().isoformat()
    hora = hora_madrid()

    for paciente in User.query.filter_by(rol='dependiente').all():
        if not paciente.supervisores:
            continue                                     # nadie a quien avisar
        activo, limite = config_de(paciente.id)
        if not activo or hora < limite:
            continue                                     # desactivado, o aún está a tiempo
        if CheckIn.query.filter_by(user_id=paciente.id, fecha=hoy).first():
            continue                                     # ya lo hizo

        # Idempotencia: la clave lleva el día, así que hay un aviso por paciente y día
        clave = f'checkin:{paciente.id}:{hoy}'
        if ya_avisado('CHECKIN_PERDIDO', clave):
            continue

        enviar_a_supervisores_de(
            paciente_id=paciente.id,
            tipo='CHECKIN_PERDIDO',
            titulo=f'Check-in sin hacer: {paciente.nombre}',
            cuerpo=f'{paciente.nombre} no ha confirmado hoy que está bien (hora límite: {limite}).',
            datos={'tipo': 'CHECKIN_PERDIDO', 'paciente_id': str(paciente.id), 'fecha': hoy},
        )
        marcar_avisado('CHECKIN_PERDIDO', clave, user_id=paciente.id)
        avisos_enviados += 1

    return avisos_enviados