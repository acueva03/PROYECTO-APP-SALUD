"""Configuración de la base de datos: SQLite en local y en los tests, PostgreSQL en el servidor.

Funciones puras (sin Flask ni base de datos), así se pueden probar sin conectar con nada.
"""
from sqlalchemy.engine import make_url


def url_base_de_datos(entorno, ruta_sqlite):
    """Devuelve la URL que debe usar la app.

    - Si hay DATABASE_URL (la usan los tests y el servidor en la nube), se usa esa.
    - Si no, el archivo SQLite local de siempre (ruta_sqlite).
    Algunos proveedores dan la URL como "postgres://..." y SQLAlchemy solo acepta "postgresql://...".
    Además se fija el driver (psycopg2): sin él, las versiones nuevas de SQLAlchemy buscan psycopg (v3),
    que no está instalado, y la app no arranca ("No module named 'psycopg'").
    """
    url = (entorno.get('DATABASE_URL') or '').strip()
    if not url:
        return 'sqlite:///' + ruta_sqlite
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    if url.startswith('postgresql://'):          # sin driver explícito (los que ya lo llevan, como +psycopg, se respetan)
        url = 'postgresql+psycopg2://' + url[len('postgresql://'):]
    return url


def es_sqlite(url):
    return url.startswith('sqlite')


def opciones_motor(url):
    """Opciones de conexión según el motor.

    check_same_thread y timeout son exclusivas de SQLite (con PostgreSQL la conexión falla).
    En PostgreSQL, pool_pre_ping comprueba la conexión antes de usarla y pool_recycle la renueva:
    los proveedores en la nube cierran las conexiones que llevan un rato inactivas.
    """
    if es_sqlite(url):
        return {'connect_args': {'check_same_thread': False, 'timeout': 15}}
    return {'pool_pre_ping': True, 'pool_recycle': 280}


def describir_url(url):
    """La URL sin la contraseña, para escribirla en el log sin filtrar credenciales."""
    try:
        return make_url(url).render_as_string(hide_password=True)
    except Exception:       # una URL mal escrita no debe impedir que se vea el error real al conectar
        return '(URL de base de datos no válida)'
