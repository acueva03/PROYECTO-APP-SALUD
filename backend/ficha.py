"""Validación de la ficha médica y los datos personales (funcionalidad nueva de P4).
Funciones puras, sin base de datos: se pueden probar sin arrancar la app."""
import re

GRUPOS_SANGUINEOS = {'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'}
TELEFONO_RE = re.compile(r'[0-9 +().-]{6,20}')

# campo: (nombre para el mensaje de error, máximo de caracteres)
CAMPOS_TEXTO = {
    'alergias': ('Las alergias', 500),
    'enfermedades_cronicas': ('Las enfermedades crónicas', 500),
    'medicacion': ('La medicación', 500),
    'contacto_emergencia_nombre': ('El nombre del contacto', 120),
}


def _vacio(valor):
    return valor is None or (isinstance(valor, str) and not valor.strip())


def _numero(valor, nombre, minimo, maximo, entero):
    """Devuelve (numero_o_None, error_o_None). Vacío -> None (campo sin rellenar)."""
    if _vacio(valor):
        return None, None
    if isinstance(valor, bool) or not isinstance(valor, (int, float, str)):
        return None, f'{nombre} no es válida'
    try:
        texto = str(valor).strip().replace(',', '.')
        n = int(texto) if entero else float(texto)
    except ValueError:
        return None, f'{nombre} no es válida'
    if not minimo <= n <= maximo:          # también rechaza nan e inf
        return None, f'{nombre} debe estar entre {minimo} y {maximo}'
    return n, None


def _telefono(valor, nombre):
    if _vacio(valor):
        return None, None
    if not isinstance(valor, str) or not TELEFONO_RE.fullmatch(valor.strip()):
        return None, f'{nombre} no es válido'
    return valor.strip(), None


def validar_ficha(data):
    """Devuelve (datos_limpios, None) o (None, mensaje_de_error).
    Los campos que no vienen o vienen vacíos quedan a None."""
    if not isinstance(data, dict):
        return None, 'Datos no válidos'
    limpio = {}

    limpio['edad'], error = _numero(data.get('edad'), 'La edad', 0, 120, True)
    if error: return None, error
    limpio['altura'], error = _numero(data.get('altura'), 'La altura', 50, 250, False)   # en cm
    if error: return None, error

    limpio['telefono'], error = _telefono(data.get('telefono'), 'El teléfono')
    if error: return None, error
    limpio['contacto_emergencia_telefono'], error = _telefono(
        data.get('contacto_emergencia_telefono'), 'El teléfono del contacto')
    if error: return None, error

    grupo = data.get('grupo_sanguineo')
    if _vacio(grupo):
        limpio['grupo_sanguineo'] = None
    elif isinstance(grupo, str) and grupo.strip().upper() in GRUPOS_SANGUINEOS:
        limpio['grupo_sanguineo'] = grupo.strip().upper()
    else:
        return None, 'Grupo sanguíneo no válido'

    for campo, (nombre, maximo) in CAMPOS_TEXTO.items():
        valor = data.get(campo)
        if _vacio(valor):
            limpio[campo] = None
        elif not isinstance(valor, str):
            return None, f'{nombre} no es válido'
        elif len(valor.strip()) > maximo:
            return None, f'{nombre} no puede superar {maximo} caracteres'
        else:
            limpio[campo] = valor.strip()
    return limpio, None
