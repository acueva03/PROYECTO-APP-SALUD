import re
import unicodedata

USERNAME_RE = re.compile(r'[a-z0-9._-]{3,30}')


def normalizar_username(texto):
    """' Pedro ' -> 'pedro'. Así 'Pedro' y 'pedro' son el mismo usuario."""
    return (texto or '').strip().lower()


def validar_username(username):
    """Devuelve None si es válido, o un mensaje de error."""
    # fullmatch: con match + '$' se colaría un salto de línea al final
    if not USERNAME_RE.fullmatch(username or ''):
        return ('El usuario debe tener de 3 a 30 caracteres: letras minúsculas sin tildes, '
                'números, punto, guion o guion bajo')
    return None


def validar_password(password):
    """Política mínima: 8-128 caracteres, con al menos una letra y un número."""
    if not isinstance(password, str) or len(password) < 8:
        return 'La contraseña debe tener al menos 8 caracteres'
    if len(password) > 128:
        return 'La contraseña es demasiado larga (máximo 128 caracteres)'
    if not any(c.isalpha() for c in password):
        return 'La contraseña debe incluir al menos una letra'
    if not any(c.isdigit() for c in password):
        return 'La contraseña debe incluir al menos un número'
    return None


def username_desde_nombre(nombre):
    """'María' -> 'maria'. Sirve para dar username a los usuarios que ya existían."""
    sin_tildes = unicodedata.normalize('NFKD', nombre or '').encode('ascii', 'ignore').decode()
    base = re.sub(r'[^a-z0-9]', '', sin_tildes.lower())
    return base[:20] or 'usuario'