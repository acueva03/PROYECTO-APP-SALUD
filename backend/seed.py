from app import app
from models import db, User, MedicalProfile

with app.app_context():
    if User.query.count() == 0:
        alberto = User(nombre='Alberto', rol='supervisor')
        maria = User(nombre='María', apellidos='Rodríguez', edad=78, peso=62, rol='dependiente')
        alberto.dependientes.append(maria)
        db.session.add_all([alberto, maria])
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
        print('Datos de prueba creados')
    else:
        print('La base de datos ya tiene usuarios; no se ha hecho nada')
