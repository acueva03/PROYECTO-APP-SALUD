import os
import shutil
import sqlite3
import sys
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ORIGEN = os.path.join(BASE_DIR, 'app_salud.db')
CARPETA = os.path.join(BASE_DIR, 'backups')
MAX_COPIAS = 20


def info_bd():
    """3.9.2: muestra tamaño y fecha de modificación antes de tocar nada."""
    if not os.path.exists(ORIGEN):
        print('AVISO: no existe app_salud.db')
        return False
    tam = os.path.getsize(ORIGEN)
    mod = datetime.fromtimestamp(os.path.getmtime(ORIGEN))
    print(f'app_salud.db -> {tam} bytes, modificada: {mod:%d/%m/%Y %H:%M:%S}')
    return True


def hacer_backup():
    """3.9.1: copia segura con fecha en backups/."""
    if not info_bd():
        return
    os.makedirs(CARPETA, exist_ok=True)
    nombre = 'app_salud_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.db'
    destino = os.path.join(CARPETA, nombre)

    origen = sqlite3.connect(ORIGEN)
    copia = sqlite3.connect(destino)
    with copia:
        origen.backup(copia)      # copia consistente aunque el servidor esté abierto
    copia.close()
    origen.close()
    print('Backup creado:', destino)

    # Guardamos solo las últimas MAX_COPIAS
    copias = sorted(f for f in os.listdir(CARPETA) if f.endswith('.db'))
    for viejo in copias[:-MAX_COPIAS]:
        os.remove(os.path.join(CARPETA, viejo))


def restaurar():
    """3.9.3: restaura la copia más reciente (parar el servidor antes)."""
    copias = sorted(f for f in os.listdir(CARPETA) if f.endswith('.db')) if os.path.isdir(CARPETA) else []
    if not copias:
        print('No hay copias en backups/')
        return
    ultima = os.path.join(CARPETA, copias[-1])
    if os.path.exists(ORIGEN):
        shutil.copy2(ORIGEN, ORIGEN + '.antes_de_restaurar')   # red de seguridad
    shutil.copy2(ultima, ORIGEN)
    print('Restaurada la copia:', ultima)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--restaurar':
        restaurar()
    else:
        hacer_backup()