from sqlalchemy import inspect


def comprobar_esquema(db):
    inspector = inspect(db.engine)
    tablas = set(inspector.get_table_names())
    faltan = []
    for tabla in db.metadata.sorted_tables:
        if tabla.name not in tablas:
            faltan.append(f'tabla {tabla.name}')
            continue
        existentes = {c['name'] for c in inspector.get_columns(tabla.name)}
        faltan += [f'{tabla.name}.{c.name}' for c in tabla.columns if c.name not in existentes]
    if faltan:
        raise RuntimeError('La base de datos no coincide con models.py. Falta: '
                           + ', '.join(faltan)
                           + '. Añádelo a actualizar_columnas() o restaura una copia (backup_bd.py).')