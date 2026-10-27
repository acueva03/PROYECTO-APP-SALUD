from app import app
from models import db, User, MedicalProfile, PesoRegistro

with app.app_context():
    if User.query.count() == 0:
        alberto = User(nombre='Alberto', rol='supervisor')
        maria = User(nombre='María', apellidos='Rodríguez', edad=78, peso=62, rol='dependiente')
        
        # Asignar contraseñas (1234) para las pruebas
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
        print('Datos de prueba creados (Contraseñas de Alberto y María: 1234)')
    else:
        print('La base de datos ya tiene usuarios; no se ha hecho nada')