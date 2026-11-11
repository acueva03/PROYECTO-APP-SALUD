from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timezone

# Importar herramientas de seguridad para cifrar contraseñas (Riesgo 3.5)
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Fecha y hora actual
def ahora(): 
    return datetime.now(timezone.utc)

from zoneinfo import ZoneInfo

ZONA = ZoneInfo('Europe/Madrid')

def hoy_madrid():
    """Fecha de hoy en Madrid, con independencia de la zona horaria del servidor (riesgo 3.13)."""
    return datetime.now(ZONA).date()

# Tabla intermedia para vincular Supervisores con Dependientes
supervisor_dependiente = db.Table(
    'supervisor_dependiente',
    db.Column('supervisor_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('dependiente_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

# Un usuario de la aplicación (datos personales)
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

    # NUEVO (Sprint 3): nombre de usuario único para iniciar sesión.
    # nullable=True porque los usuarios antiguos no lo tenían (se rellena al arrancar la app).
    username = db.Column(db.String(50), unique=True, nullable=True, index=True)

    # Campo para la contraseña encriptada
    password_hash = db.Column(db.String(256), nullable=True)

    # Función para generar el hash de la contraseña
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Función para comprobar si la contraseña coincide
    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    # Nombre y apellidos juntos, para mostrarlos en las pantallas
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellidos or ''}".strip()

    # Iniciales para el avatar (ej: María Rodríguez -> MR)
    @property
    def iniciales(self):
        ini = self.nombre[0] if self.nombre else ''
        if self.apellidos:
            ini += self.apellidos[0]
        return ini.upper()

    # Relaciones
    ficha_medica = db.relationship('MedicalProfile', backref='usuario', uselist=False, cascade='all, delete-orphan')
    alarmas = db.relationship('Alarm', backref='usuario', lazy=True, cascade='all, delete-orphan')
    metricas = db.relationship('HealthMetric', backref='usuario', lazy=True, cascade='all, delete-orphan')
    alertas_sos = db.relationship('AlertSOS', backref='usuario', lazy=True, cascade='all, delete-orphan')

    # Vinculación entre usuarios (Supervisor -> Dependientes)
    dependientes = db.relationship(
        'User',
        secondary=supervisor_dependiente,
        primaryjoin=(id == supervisor_dependiente.c.supervisor_id),
        secondaryjoin=(id == supervisor_dependiente.c.dependiente_id),
        backref='supervisores'
    )

# Guarda la ficha médica de un usuario
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

# Guarda las métricas diarias de un usuario (fecha, horas de sueño, estado de ánimo)
class HealthMetric(db.Model):
    __tablename__ = 'health_metrics'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    fecha = db.Column(db.Date, default=hoy_madrid) 
    horas_sueno = db.Column(db.Float, nullable=True)
    estado_animo = db.Column(db.String(50), nullable=True)

# Almacena los avisos y recordatorios de un usuario
class Alarm(db.Model):
    __tablename__ = 'alarms'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    titulo = db.Column(db.String(100), nullable=False)
    hora = db.Column(db.String(5), nullable=False)
    fecha = db.Column(db.String(10), nullable=True)
    es_repetitiva = db.Column(db.Boolean, default=False)
    activa = db.Column(db.Boolean, default=True)
    ultima_vez_sono = db.Column(db.DateTime, nullable=True)
    dosis = db.Column(db.String(50), nullable=True)
    dias_semana = db.Column(db.String(20), nullable=True)   # '0,2,4' (lunes=0 ... domingo=6)
    # Riesgo 3.14: borrado lógico. "Eliminar" solo la marca; se puede recuperar desde la papelera.
    # (Columna añadida también en actualizar_columnas() de app.py, regla 3.19)
    eliminada = db.Column(db.Boolean, default=False, nullable=False)
    eliminada_en = db.Column(db.DateTime, nullable=True)

# Alerta SOS, guarda la fecha/hora y su estado: activa o atendida
class AlertSOS(db.Model):
    __tablename__ = 'alerts_sos'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    fecha_hora = db.Column(db.DateTime, default=ahora)
    estado = db.Column(db.String(20), default='ACTIVA')

# Cada vez que suena una alarma se crea un registro
class RegistroToma(db.Model):
    __tablename__ = 'registros_toma'
    id = db.Column(db.Integer, primary_key=True)
    alarma_id = db.Column(db.Integer, db.ForeignKey('alarms.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    titulo = db.Column(db.String(100), nullable=False)
    fecha_prevista = db.Column(db.String(10), nullable=False)
    hora_prevista = db.Column(db.String(5), nullable=False)
    estado = db.Column(db.String(20), default='PENDIENTE')
    creado = db.Column(db.DateTime, default=ahora)
    confirmada_en = db.Column(db.DateTime, nullable=True)
    dosis = db.Column(db.String(50), nullable=True)

class PesoRegistro(db.Model):
    __tablename__ = 'pesos'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    fecha = db.Column(db.String(10), nullable=False)   # 'AAAA-MM-DD', igual que en las alarmas
    kg = db.Column(db.Float, nullable=False)

# Código temporal para vincular un supervisor con un paciente.
# NUNCA se guarda el código en claro: solo su hash SHA-256.
class CodigoVinculo(db.Model):
    __tablename__ = 'codigos_vinculo'
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    codigo_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    creado = db.Column(db.DateTime, default=ahora)
    expira = db.Column(db.DateTime, nullable=False)
    usado = db.Column(db.Boolean, default=False, nullable=False)

# Cada canje fallido se anota para bloquear la fuerza bruta (5 fallos en 10 minutos)
class IntentoVinculo(db.Model):
    __tablename__ = 'intentos_vinculo'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ip = db.Column(db.String(45), nullable=True)
    fecha = db.Column(db.DateTime, default=ahora)

# Historial de vínculos y desvinculaciones (son datos de salud: RGPD).
# iniciado_por dice quién lo hizo: 'SUPERVISOR' (canjeó el código o se desvinculó) o 'PACIENTE' (quitó al supervisor)
class VinculoLog(db.Model):
    __tablename__ = 'vinculo_log'
    id = db.Column(db.Integer, primary_key=True)
    supervisor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    paciente_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    accion = db.Column(db.String(20), nullable=False)          # 'VINCULADO' o 'DESVINCULADO'
    iniciado_por = db.Column(db.String(20), nullable=False)    # 'SUPERVISOR' o 'PACIENTE'
    fecha = db.Column(db.DateTime, default=ahora)

# Cada login fallido se anota para bloquear la fuerza bruta (riesgo 3.15): 5 fallos en 10 minutos
class IntentoLogin(db.Model):
    __tablename__ = 'intentos_login'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, index=True)
    ip = db.Column(db.String(45), nullable=True)
    fecha = db.Column(db.DateTime, default=ahora)