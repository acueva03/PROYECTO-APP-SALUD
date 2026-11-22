# Módulo de Notificaciones Push (P4 - Andrés)
# Gestión de Firebase Cloud Messaging (FCM), contratos públicos y control de idempotencia.

import os
import json
import logging
import threading
from datetime import datetime, timezone

from models import db, DispositivoPush, User, AvisoEnviado, ahora

logger = logging.getLogger(__name__)

# Tipos de aviso válidos según el contrato de la aplicación
TIPOS_AVISO = {
    'SOS',
    'TOMA_SIN_CONFIRMAR',
    'ALARMA_NO_SONO',
    'CHECKIN_PERDIDO'
}

# Inicialización segura de Firebase Admin SDK
_firebase_app = None
_firebase_intentado = False


def inicializar_firebase():
    """Inicializa Firebase Admin SDK si existen credenciales en FIREBASE_CREDENTIALS.
    Si no existen o no está instalado, desactiva el envío real sin lanzar errores."""
    global _firebase_app, _firebase_intentado
    if _firebase_intentado:
        return _firebase_app

    _firebase_intentado = True
    cred_val = os.environ.get('FIREBASE_CREDENTIALS')
    if not cred_val:
        logger.info("FIREBASE_CREDENTIALS no configurado: notificaciones push en modo local/simulación.")
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials

        if os.path.isfile(cred_val):
            cred = credentials.Certificate(cred_val)
        else:
            cred_dict = json.loads(cred_val)
            cred = credentials.Certificate(cred_dict)

        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK inicializado correctamente.")
        return _firebase_app
    except Exception as e:
        logger.warning(f"No se pudo inicializar Firebase Admin SDK: {e}. Push desactivado.")
        return None


# ---------------------------------------------------------------------------
# Helpers de Idempotencia (contrato para P4 y P5)
# ---------------------------------------------------------------------------
def ya_avisado(tipo, clave):
    """Comprueba si ya se ha enviado un aviso para el tipo y clave dados."""
    return AvisoEnviado.query.filter_by(tipo=tipo, clave=clave).first() is not None


def marcar_avisado(tipo, clave, user_id=None):
    """Registra que se ha enviado un aviso para evitar duplicados en ticks posteriores."""
    if ya_avisado(tipo, clave):
        return
    try:
        aviso = AvisoEnviado(tipo=tipo, clave=clave, user_id=user_id or 0)
        db.session.add(aviso)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.warning(f"Error al marcar aviso como enviado ({tipo}, {clave}): {e}")


# ---------------------------------------------------------------------------
# Envío de notificaciones a través de FCM
# ---------------------------------------------------------------------------
def _limpiar_token_invalido(token):
    """Elimina de la base de datos un token no válido o caducado."""
    try:
        disp = DispositivoPush.query.filter_by(token=token).first()
        if disp:
            db.session.delete(disp)
            db.session.commit()
            logger.info("Token push inválido eliminado de la base de datos.")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al eliminar token inválido: {e}")


def _enviar_a_tokens(tokens, tipo, titulo, cuerpo, datos=None):
    """Envía el push a una lista de tokens utilizando Firebase Cloud Messaging.
    Si FCM no está activo, registra el aviso en log sin lanzar errores."""
    if not tokens:
        return 0

    app_fb = inicializar_firebase()
    canal = 'sos' if tipo == 'SOS' else 'avisos'
    payload_data = {}
    if datos:
        for k, v in datos.items():
            payload_data[str(k)] = str(v)
    payload_data['tipo'] = tipo

    logger.info(f"Despachando notificación push tipo '{tipo}' a {len(tokens)} dispositivo(s).")

    if not app_fb:
        # En local o tests sin Firebase, el envío se considera registrado exitosamente
        return len(tokens)

    enviados = 0
    try:
        try:
            import firebase_admin.messaging as messaging
        except ImportError:
            import sys
            messaging = getattr(sys.modules.get('firebase_admin'), 'messaging', None) or sys.modules.get('firebase_admin.messaging')

        if not messaging:
            logger.warning("Módulo messaging no disponible.")
            return len(tokens)

        for token in tokens:
            try:
                mensaje = messaging.Message(
                    notification=messaging.Notification(
                        title=titulo,
                        body=cuerpo,
                    ),
                    data=payload_data,
                    android=messaging.AndroidConfig(
                        priority='high',
                        notification=messaging.AndroidNotification(
                            channel_id=canal,
                            priority='max' if tipo == 'SOS' else 'high',
                            sound='default',
                        ),
                    ),
                    token=token,
                )
                messaging.send(mensaje, app=app_fb)
                enviados += 1
            except Exception as err:
                err_str = str(err).lower()
                if 'unregistered' in err_str or 'invalidargument' in err_str or 'not-found' in err_str:
                    logger.warning(f"Token FCM caducado o inválido: eliminando.")
                    _limpiar_token_invalido(token)
                else:
                    logger.error(f"Error al enviar push a token individual: {err}")
    except Exception as global_err:
        logger.error(f"Error inesperado durante envío FCM: {global_err}")

    return enviados


# ---------------------------------------------------------------------------
# Funciones Públicas (Contrato oficial)
# ---------------------------------------------------------------------------
def enviar_a_usuario(user_id, tipo, titulo, cuerpo, datos=None, en_segundo_plano=True):
    """Envía una notificación push a todos los dispositivos registrados de un usuario.
    
    Devuelve la cantidad de dispositivos destino y nunca lanza excepciones.
    """
    try:
        dispositivos = DispositivoPush.query.filter_by(user_id=user_id).all()
        if not dispositivos:
            return 0

        tokens = [d.token for d in dispositivos]

        if en_segundo_plano and not os.environ.get('TESTING'):
            hilo = threading.Thread(
                target=_enviar_a_tokens,
                args=(tokens, tipo, titulo, cuerpo, datos),
                daemon=True
            )
            hilo.start()
        else:
            _enviar_a_tokens(tokens, tipo, titulo, cuerpo, datos)

        return len(tokens)
    except Exception as e:
        logger.error(f"Error en enviar_a_usuario(user_id={user_id}, tipo={tipo}): {e}")
        return 0


def enviar_a_supervisores_de(paciente_id, tipo, titulo, cuerpo, datos=None, en_segundo_plano=True):
    """Envía una notificación push a todos los supervisores vinculados al paciente indicado.
    
    Devuelve la cantidad de dispositivos de supervisores contactados y nunca lanza excepciones.
    """
    try:
        paciente = db.session.get(User, paciente_id)
        if not paciente or not paciente.supervisores:
            return 0

        sup_ids = [s.id for s in paciente.supervisores]
        dispositivos = DispositivoPush.query.filter(DispositivoPush.user_id.in_(sup_ids)).all()
        if not dispositivos:
            return 0

        tokens = [d.token for d in dispositivos]

        if en_segundo_plano and not os.environ.get('TESTING'):
            hilo = threading.Thread(
                target=_enviar_a_tokens,
                args=(tokens, tipo, titulo, cuerpo, datos),
                daemon=True
            )
            hilo.start()
        else:
            _enviar_a_tokens(tokens, tipo, titulo, cuerpo, datos)

        return len(tokens)
    except Exception as e:
        logger.error(f"Error en enviar_a_supervisores_de(paciente_id={paciente_id}, tipo={tipo}): {e}")
        return 0
