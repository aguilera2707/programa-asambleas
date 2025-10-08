# models.py
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db
from datetime import datetime


# -------------------------------
# 🔹 Modelo: Ciclo Escolar (Eje central del sistema)
# -------------------------------
class CicloEscolar(db.Model):
    __tablename__ = 'ciclos_escolares'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)  # Ej: "2024-2025"
    activo = db.Column(db.Boolean, default=False)

    fecha_inicio = db.Column(db.Date, nullable=True)
    fecha_fin = db.Column(db.Date, nullable=True)
    observaciones = db.Column(db.Text, nullable=True)

    # Relaciones con los demás modelos
    maestros = db.relationship('Maestro', backref='ciclo', lazy=True)
    alumnos = db.relationship('Alumno', backref='ciclo', lazy=True)
    bloques = db.relationship('Bloque', backref='ciclo', lazy=True)
    valores = db.relationship('Valor', backref='ciclo', lazy=True)
    nominaciones = db.relationship('Nominacion', backref='ciclo', lazy=True)

    def __repr__(self):
        return f"<CicloEscolar {self.nombre}>"


# -------------------------------
# 🔹 Modelo: Maestro
# -------------------------------
class Maestro(db.Model):
    __tablename__ = 'maestros'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    ciclo_id = db.Column(db.Integer, db.ForeignKey('ciclos_escolares.id'))

    def __repr__(self):
        return f"<Maestro {self.nombre}>"


# -------------------------------
# 🔹 Modelo: Bloque (agrupa grados y salones del ciclo)
# -------------------------------
class Bloque(db.Model):
    __tablename__ = 'bloques'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    ciclo_id = db.Column(db.Integer, db.ForeignKey('ciclos_escolares.id'))

    def __repr__(self):
        return f"<Bloque {self.nombre}>"


# -------------------------------
# 🔹 Modelo: Alumno
# -------------------------------
class Alumno(db.Model):
    __tablename__ = 'alumnos'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    grado = db.Column(db.String(20), nullable=False)
    grupo = db.Column(db.String(5), nullable=False)
    nivel = db.Column(db.String(50), nullable=False)

    bloque_id = db.Column(db.Integer, db.ForeignKey('bloques.id'))
    ciclo_id = db.Column(db.Integer, db.ForeignKey('ciclos_escolares.id'))

    def __repr__(self):
        return f"<Alumno {self.nombre} - {self.grado}{self.grupo}>"


# -------------------------------
# 🔹 Modelo: Valor institucional (dependiente del ciclo)
# -------------------------------
class Valor(db.Model):
    __tablename__ = 'valores'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    ciclo_id = db.Column(db.Integer, db.ForeignKey('ciclos_escolares.id'))

    def __repr__(self):
        return f"<Valor {self.nombre}>"


# -------------------------------
# 🔹 Modelo: Nominación (conexión entre maestro, alumno y valor)
# -------------------------------
class Nominacion(db.Model):
    __tablename__ = 'nominaciones'

    id = db.Column(db.Integer, primary_key=True)
    alumno_id = db.Column(db.Integer, db.ForeignKey('alumnos.id'))
    maestro_id = db.Column(db.Integer, db.ForeignKey('maestros.id'))
    valor_id = db.Column(db.Integer, db.ForeignKey('valores.id'))
    ciclo_id = db.Column(db.Integer, db.ForeignKey('ciclos_escolares.id'))

    razon = db.Column(db.Text, nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Nominacion Alumno={self.alumno_id} Valor={self.valor_id}>"


# -------------------------------
# 🔹 Modelo: Usuario (Login general del sistema)
# -------------------------------
class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default='personal')  # opciones: 'alumno', 'profesor', 'admin'

    # 🔐 Métodos seguros de contraseña
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<Usuario {self.nombre} ({self.rol})>"
