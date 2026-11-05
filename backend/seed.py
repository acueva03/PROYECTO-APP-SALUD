from app import app
from models import db, User, MedicalProfile, PesoRegistro

# SOLO PARA DESARROLLO: crea dos usuarios de ejemplo. Las cuentas reales se crean en /registro.
with app.app_context():
    if User.query.count() == 0:
        alberto = User(nombre='Alberto', username='alberto', rol='supervisor')
        maria = User(nombre='María', apellidos='Rodríguez', username='maria', edad=78, peso=62, rol='dependiente')
        
        # Contraseña de prueba (el registro real exige 8 caracteres con letra y número)
        alberto.set_password('1234')
        maria.set_password('1234')

        alberto.dependientes.append(maria)
        db.session.add_all([alberto, maria])
        db.session.commit()

        for fecha, kg in [('2026-09-01', 64.0), ('2026-09-15', 63.2), ('2026-10-01', 62.5), ('2026-10-20', 62.0)]:
            db.session.add(PesoRegistro(user_id=maria.id, fecha=fecha, kg=kg))
        db.session.commit()

        db.session.add(MedicalProfile(
            user_id=maria.id,
            grupo_sanguineo='A+',
            alergias='Ninguna conocida',
            medicacion='Ejemplo: paracetamol si hay dolor',
            contacto_emergencia_nombre='Alberto',
            contacto_emergencia_telefono='600000000'
        ))
        db.session.commit()
        print('Datos de prueba creados. Usuarios: alberto y maria (contraseña 1234)')
    else:
        print('La base de datos ya tiene usuarios; no se ha hecho nada')