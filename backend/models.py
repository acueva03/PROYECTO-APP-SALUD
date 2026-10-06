from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timezone

db = SQLAlchemy()


def ahora(): 
    return datetime.now(timezone.utc)


# Tabla intermedia para vincular Supervisores con Dependientes
supervisor_dependiente = db.Table(
    'supervisor_dependiente',
    db.Column('supervisor_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('dependiente_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(120), nullable=True)  
    telefono = db.Column(db.String(20), nullable=True)  
    edad = db.Column(db.Integer, nullable=True)
    peso = db.Column(db.Float, nullable=True)              
    altura = db.Column(db.Float, nullable=True)           
    rol = db.Column(db.String(20), nullable=False)         

    # Relaciones
    ficha_medica = db.relationship('MedicalProfile', backref='usuario', uselist=False,
                                   cascade='all, delete-orphan')
    alarmas = db.relationship('Alarm', backref='usuario', lazy=True,
                              cascade='all, delete-orphan')
    metricas = db.relationship('HealthMetric', backref='usuario', lazy=True,
                               cascade='all, delete-orphan')
    alertas_sos = db.relationship('AlertSOS', backref='usuario', lazy=True,
                                  cascade='all, delete-orphan')

    # Vinculación entre usuarios (Supervisor -> Dependientes)
    dependientes = db.relationship(
        'User',
        secondary=supervisor_dependiente,
        primaryjoin=(id == supervisor_dependiente.c.supervisor_id),
        secondaryjoin=(id == supervisor_dependiente.c.dependiente_id),
        backref='supervisores'
    )



class MedicalProfile(db.Model):
    __tablename__ = 'medical_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    grupo_sanguineo = db.Column(db.String(5))
    alergias = db.Column(db.Text)
    enfermedades_cronicas = db.Column(db.Text)
    medicacion = db.Column(db.Text)
    contacto_emergencia_nombre = db.Column(db.String(120))
    contacto_emergencia_telefono = db.Column(db.String(20))


class Alarm(db.Model):
    __tablename__ = 'alarms'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    titulo = db.Column(db.String(100), nullable=False)  # ej: "Beber agua"
    hora = db.Column(db.String(5), nullable=False)      # Formato HH:MM
    es_repetitiva = db.Column(db.Boolean, default=False)
    activa = db.Column(db.Boolean, default=True)


class HealthMetric(db.Model):
    __tablename__ = 'health_metrics'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    fecha = db.Column(db.Date, default=date.today)      # CAMBIO
    horas_sueno = db.Column(db.Float, nullable=True)
    estado_animo = db.Column(db.String(50), nullable=True)


class AlertSOS(db.Model):
    __tablename__ = 'alerts_sos'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    fecha_hora = db.Column(db.DateTime, default=ahora)  # CAMBIO
    estado = db.Column(db.String(20), default='ACTIVA')  # 'ACTIVA' o 'ATENDIDA'