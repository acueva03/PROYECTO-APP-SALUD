# Blueprint de Notificaciones Push y Tareas Periódicas (P4 - Andrés)
# Endpoints: /api/dispositivos (POST/DELETE) y /interno/tick (POST)

import os
from datetime import timedelta, timezone
from flask import Blueprint, request, jsonify, session

from models import db, User, DispositivoPush, ahora
from notificaciones import (
    enviar_a_supervisores_de,
    ya_avisado,
    marcar_avisado,
)

notificaciones_bp = Blueprint('notificaciones_bp', __name__)

MINUTOS_RETARDO_AVISO_TOMA = 15


# ---------------------------------------------------------------------------
# Endpoints de Registro de Dispositivos (Móviles)
# ---------------------------------------------------------------------------
@notificaciones_bp.route('/api/dispositivos', methods=['POST'])
def registrar_dispositivo():
    """Registra o actualiza el token push de un dispositivo móvil para el usuario con sesión activa."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'No autorizado'}), 401

    datos = request.get_json(silent=True) or {}
    token = datos.get('token')
    plataforma = datos.get('plataforma', 'android')

    if not token or not isinstance(token, str) or not token.strip() or len(token) > 255:
        return jsonify({'error': 'Token inválido'}), 400
    if not isinstance(plataforma, str) or not plataforma.strip() or len(plataforma.strip()) > 20:
        return jsonify({'error': 'Plataforma inválida'}), 400
    plataforma = plataforma.strip()

    token = token.strip()
    disp = DispositivoPush.query.filter_by(token=token).first()

    if disp:
        # Reasigna el token al usuario actual (móvil compartido o cambio de cuenta)
        disp.user_id = user_id
        disp.plataforma = plataforma
        disp.ultimo_uso = ahora()
    else:
        disp = DispositivoPush(
            user_id=user_id,
            token=token,
            plataforma=plataforma,
            ultimo_uso=ahora()
        )
        db.session.add(disp)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Error interno al registrar el dispositivo'}), 500

    return jsonify({'mensaje': 'Dispositivo registrado'}), 200


@notificaciones_bp.route('/api/dispositivos', methods=['DELETE'])
def desregistrar_dispositivo():
    """Elimina el registro de un token push (por ejemplo, al cerrar sesión)."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'No autorizado'}), 401

    datos = request.get_json(silent=True) or {}
    token = datos.get('token')
    if token is not None and not isinstance(token, str):
        return jsonify({'error': 'Token inválido'}), 400

    try:
        if token and token.strip():
            disp = DispositivoPush.query.filter_by(token=token.strip()).first()
            if disp:
                db.session.delete(disp)
        else:
            DispositivoPush.query.filter_by(user_id=user_id).delete()

        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Error interno al eliminar el dispositivo'}), 500

    return jsonify({'mensaje': 'Dispositivo desregistrado'}), 200


# ---------------------------------------------------------------------------
# Lógica de Tareas Periódicas (Tick del Cron)
# ---------------------------------------------------------------------------
def procesar_tomas_sin_confirmar():
    """Revisa tomas pendientes con más de 15 minutos y alarmas que no sonaron.
    Envía aviso push a los supervisores de forma idempotente (un único aviso por toma/alarma)."""
    from app import tomas_pendientes_de, alarmas_sin_sonar_de

    avisos_enviados = 0
    momento_actual = ahora()

    # Pacientes dependientes registrados
    pacientes = User.query.filter_by(rol='dependiente').all()

    for dep in pacientes:
        if not dep.supervisores:
            continue

        # 1. Tomas pendientes de confirmación
        tomas = tomas_pendientes_de(dep.id, 24)
        for toma in tomas:
            creado_utc = toma.creado.replace(tzinfo=timezone.utc) if toma.creado.tzinfo is None else toma.creado
            if (momento_actual - creado_utc) >= timedelta(minutes=MINUTOS_RETARDO_AVISO_TOMA):
                clave = f"toma:{toma.id}"
                if not ya_avisado('TOMA_SIN_CONFIRMAR', clave):
                    enviar_a_supervisores_de(
                        paciente_id=dep.id,
                        tipo='TOMA_SIN_CONFIRMAR',
                        titulo=f"Toma sin confirmar: {dep.nombre}",
                        cuerpo=f"La toma '{toma.titulo}' lleva más de 15 minutos sin confirmar.",
                        datos={'toma_id': str(toma.id), 'paciente_id': str(dep.id)}
                    )
                    marcar_avisado('TOMA_SIN_CONFIRMAR', clave, user_id=dep.id)
                    avisos_enviados += 1

        # 2. Alarmas que no han sonado en el móvil
        alarmas_no_sonadas = alarmas_sin_sonar_de(dep.id, 24)
        for alarma, momento in alarmas_no_sonadas:
            clave = f"alarma_no_sono:{alarma.id}:{alarma.fecha}:{alarma.hora}"
            if not ya_avisado('ALARMA_NO_SONO', clave):
                enviar_a_supervisores_de(
                    paciente_id=dep.id,
                    tipo='ALARMA_NO_SONO',
                    titulo=f"Alarma no sonada: {dep.nombre}",
                    cuerpo=f"La alarma '{alarma.titulo}' no ha sonado en el móvil de {dep.nombre}.",
                    datos={'alarma_id': str(alarma.id), 'paciente_id': str(dep.id)}
                )
                marcar_avisado('ALARMA_NO_SONO', clave, user_id=dep.id)
                avisos_enviados += 1

    return avisos_enviados


@notificaciones_bp.route('/interno/tick', methods=['POST'])
def interno_tick():
    """Endpoint llamado periódicamente (cada minuto) por un cron externo.
    
    Protegido por cabecera X-Cron-Token y la variable de entorno CRON_TOKEN.
    """
    token_esperado = os.environ.get('CRON_TOKEN')
    token_recibido = request.headers.get('X-Cron-Token')

    # Si CRON_TOKEN no está definido o no coincide el token recibido, 403 Forbidden
    if not token_esperado or token_recibido != token_esperado:
        return jsonify({'error': 'Acceso no autorizado'}), 403

    tomas_procesadas = procesar_tomas_sin_confirmar()

    # Integración con P5 (Laura): Check-in diario
    checkins_procesados = 0
    try:
        from checkin_bp import procesar_checkins_perdidos
        res = procesar_checkins_perdidos()
        checkins_procesados = res if isinstance(res, int) else 0
    except (ImportError, AttributeError):
        pass

    return jsonify({
        'ok': True,
        'tomas_avisadas': tomas_procesadas,
        'checkins_avisados': checkins_procesados
    }), 200
