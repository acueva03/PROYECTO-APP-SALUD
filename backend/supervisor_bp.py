# supervisor con varios pacientes
#
# Un Blueprint es un "trozo" de rutas de Flask que vive en su propio archivo y se
# registra después en app.py. Así no hace falta tocar las rutas de los demás
# (menos conflictos de merge). Aquí van:
#   1) el helper de permisos paciente_supervisado_o_403 (el que usan P2, P3 y P4)
#   2) los endpoints nuevos del panel del supervisor
from datetime import timedelta, timezone

from flask import Blueprint, jsonify, session

from models import db, User, Alarm, AlertSOS, RegistroToma, ahora

supervisor_bp = Blueprint('supervisor_bp', __name__)

# Misma ventana que usa /api/mis-tomas-supervisadas: tomas pendientes de las últimas 24 h
HORAS_TOMAS_PENDIENTES = 24


# ---------------------------------------------------------------------------
# Utilidades pequeñas
# ---------------------------------------------------------------------------
def usuario_actual():
    """El usuario de la sesión, o None si no ha iniciado sesión."""
    user_id = session.get('user_id')
    return db.session.get(User, user_id) if user_id else None


def a_iso_utc(fecha):
    """SQLite guarda las fechas sin zona horaria (siempre en UTC).
    Aquí se les pone 'UTC' para que el navegador las convierta bien a su hora local."""
    return fecha.replace(tzinfo=timezone.utc).isoformat() if fecha else None


def supervisor_actual_o_error():
    """Devuelve (supervisor, None) o (None, respuesta_de_error)."""
    sup = usuario_actual()
    if not sup:
        return None, (jsonify({'error': 'No autorizado'}), 401)
    if sup.rol != 'supervisor':
        return None, (jsonify({'error': 'Prohibido'}), 403)
    return sup, None


# ---------------------------------------------------------------------------
# 1) HELPER DE PERMISOS (definitivo). TODOS los endpoints "por paciente" lo usan.
# ---------------------------------------------------------------------------
def paciente_supervisado_o_403(paciente_id):
    """Devuelve (paciente, None) o (None, respuesta_de_error).
    - Sin sesión -> 401. Sesión de un paciente -> 403.
    - Un id inexistente y un id de un paciente AJENO dan el MISMO 403,
      para no revelar qué pacientes existen."""
    sup, error = supervisor_actual_o_error()
    if error:
        return None, error
    paciente = db.session.get(User, paciente_id)
    if not paciente or paciente not in sup.dependientes:
        return None, (jsonify({'error': 'Prohibido'}), 403)
    return paciente, None


# ---------------------------------------------------------------------------
# 2) ENDPOINTS NUEVOS
# ---------------------------------------------------------------------------
@supervisor_bp.route('/api/supervisor/pacientes', methods=['GET'])
def listar_pacientes_supervisor():
    """Resumen de TODOS los pacientes del supervisor: lo usa la pestaña "Resumen"."""
    sup, error = supervisor_actual_o_error()
    if error:
        return error

    # fecha de corte en UTC "ingenua" (sin zona), que es como las guarda SQLite
    desde = (ahora() - timedelta(hours=HORAS_TOMAS_PENDIENTES)).replace(tzinfo=None)

    resultado = []
    for p in sup.dependientes:
        sos_activas = AlertSOS.query.filter_by(user_id=p.id, estado='ACTIVA').count()
        pendientes = RegistroToma.query.filter(
            RegistroToma.user_id == p.id,
            RegistroToma.estado == 'PENDIENTE',
            RegistroToma.creado >= desde).count()
        ultima = (RegistroToma.query
                  .filter(RegistroToma.user_id == p.id,
                          RegistroToma.estado == 'CONFIRMADA',
                          RegistroToma.confirmada_en.isnot(None))
                  .order_by(RegistroToma.confirmada_en.desc()).first())
        resultado.append({
            'id': p.id,
            'nombre': p.nombre_completo,
            'iniciales': p.iniciales,
            'edad': p.edad,
            'estado': 'SOS' if sos_activas else 'OK',
            'sos_activo': sos_activas > 0,
            'tomas_pendientes': pendientes,
            'ultima_toma': a_iso_utc(ultima.confirmada_en) if ultima else None,
        })

    # Los pacientes con SOS activo salen primero; el resto, por orden alfabético
    resultado.sort(key=lambda d: (not d['sos_activo'], d['nombre'].lower()))
    return jsonify(resultado)


@supervisor_bp.route('/api/supervisor/pacientes/<int:paciente_id>/alertas', methods=['GET'])
def alertas_de_paciente(paciente_id):
    """Últimos 10 SOS de un paciente (activos y atendidos). Pestaña "Alertas"."""
    paciente, error = paciente_supervisado_o_403(paciente_id)
    if error:
        return error
    alertas = (AlertSOS.query.filter_by(user_id=paciente.id)
               .order_by(AlertSOS.fecha_hora.desc()).limit(10).all())
    return jsonify([{'alerta_id': a.id, 'estado': a.estado,
                     'fecha_hora': a_iso_utc(a.fecha_hora)} for a in alertas])


@supervisor_bp.route('/api/supervisor/pacientes/<int:paciente_id>/medicacion', methods=['GET'])
def medicacion_de_paciente(paciente_id):
    """Alarmas programadas y tomas sin confirmar de un paciente. Pestaña "Medicación"."""
    paciente, error = paciente_supervisado_o_403(paciente_id)
    if error:
        return error

    desde = (ahora() - timedelta(hours=HORAS_TOMAS_PENDIENTES)).replace(tzinfo=None)
    pendientes = (RegistroToma.query
                  .filter(RegistroToma.user_id == paciente.id,
                          RegistroToma.estado == 'PENDIENTE',
                          RegistroToma.creado >= desde)
                  .order_by(RegistroToma.creado).all())
    alarmas = (Alarm.query.filter_by(user_id=paciente.id, eliminada=False)
               .order_by(Alarm.activa.desc(), Alarm.hora).all())
    # Riesgo 3.14.3: alarmas que el paciente ha eliminado (últimos 30 días), para avisar y poder restaurarlas
    # con POST /api/alarmas/<id>/restaurar
    desde_papelera = (ahora() - timedelta(days=30)).replace(tzinfo=None)
    eliminadas = (Alarm.query.filter(Alarm.user_id == paciente.id, Alarm.eliminada.is_(True),
                                     Alarm.eliminada_en >= desde_papelera)
                  .order_by(Alarm.eliminada_en.desc()).all())

    return jsonify({
        'tomas_pendientes': [{
            'titulo': t.titulo, 'dosis': t.dosis,
            'fecha_prevista': t.fecha_prevista, 'hora_prevista': t.hora_prevista,
            'creado': a_iso_utc(t.creado)} for t in pendientes],
        'alarmas': [{
            'id': a.id, 'titulo': a.titulo, 'hora': a.hora, 'fecha': a.fecha,
            'dosis': a.dosis, 'activa': a.activa, 'es_repetitiva': a.es_repetitiva,
            # '0,2,4' -> [0, 2, 4]  (lunes=0 ... domingo=6). [] = todos los días
            'dias': sorted({int(x) for x in (a.dias_semana or '').split(',') if x.strip().isdigit()}),
        } for a in alarmas],
        'eliminadas': [{
            'id': a.id, 'titulo': a.titulo, 'hora': a.hora, 'dosis': a.dosis,
            'eliminada_en': a_iso_utc(a.eliminada_en),
        } for a in eliminadas],
    })