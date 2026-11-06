import base64
import hashlib
import io
import re
import secrets

# Sin caracteres ambiguos: faltan 0/O y 1/I. 32 caracteres ^ 8 = más de un billón de combinaciones
ALFABETO = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
LONGITUD = 8
MINUTOS_VALIDEZ = 10     # caducidad del código
MAX_FALLOS = 5           # fallos permitidos...
VENTANA_MINUTOS = 10     # ...en esta ventana de tiempo

CODIGO_RE = re.compile('[' + ALFABETO + ']{' + str(LONGITUD) + '}')

# Mensaje único para código inexistente, caducado o ya usado: no damos pistas al atacante
MENSAJE_CODIGO_INVALIDO = 'Código no válido o caducado. Pide al paciente que genere uno nuevo.'


def generar_codigo():
    """Código aleatorio criptográficamente seguro (secrets, no random)."""
    return ''.join(secrets.choice(ALFABETO) for _ in range(LONGITUD))


def normalizar_codigo(texto):
    """' abcd-efgh ' -> 'ABCDEFGH'. Si no es texto, devuelve ''."""
    if not isinstance(texto, str):
        return ''
    return texto.replace('-', '').replace(' ', '').strip().upper()


def formato_valido(codigo):
    return bool(CODIGO_RE.fullmatch(codigo or ''))


def hash_codigo(codigo):
    """SHA-256 en hexadecimal (64 caracteres). Es lo único que se guarda en la base de datos."""
    return hashlib.sha256(codigo.encode('utf-8')).hexdigest()


def formatear_codigo(codigo):
    """'ABCDEFGH' -> 'ABCD-EFGH' (más fácil de leer y dictar)."""
    return codigo[:4] + '-' + codigo[4:]


def generar_qr(url):
    """Devuelve el QR como data-URI SVG, o None si la librería qrcode no está instalada."""
    try:
        import qrcode
        import qrcode.image.svg
    except ImportError:
        return None
    imagen = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2)
    buffer = io.BytesIO()
    imagen.save(buffer)
    return 'data:image/svg+xml;base64,' + base64.b64encode(buffer.getvalue()).decode()