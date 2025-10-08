# models.py
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db


# -------------------------------
# 🔹 Modelo: Valores institucionales
# -------------------------------
class Valor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f"<Valor {self.nombre}>"


# -------------------------------
# 🔹 Modelo: Ciclo Escolar
# -------------------------------
class CicloEscolar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    activo = db.Column(db.Boolean, default=False)

    fecha_inicio = db.Column(db.Date, nullable=True)
    fecha_fin = db.Column(db.Date, nullable=True)

    fecha_asamblea_1 = db.Column(db.Date, nullable=True)
    fecha_asamblea_2 = db.Column(db.Date, nullable=True)
    fecha_asamblea_3 = db.Column(db.Date, nullable=True)
    fecha_asamblea_4 = db.Column(db.Date, nullable=True)

    def __repr__(self):
        return f"<CicloEscolar {self.nombre}>"


# -------------------------------
# 🔹 Modelo: Bloque
# -------------------------------
class Bloque(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<Bloque {self.nombre}>"


# -------------------------------
# 🔹 Modelo: Alumno
# -------------------------------
class Alumno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    grado = db.Column(db.String(20), nullable=False)
    grupo = db.Column(db.String(5), nullable=False)
    nivel = db.Column(db.String(50), nullable=False)

    ciclo_id = db.Column(db.Integer, db.ForeignKey('ciclo_escolar.id'))

    def __repr__(self):
        return f"<Alumno {self.nombre} - {self.grado}{self.grupo}>"


# -------------------------------
# 🔹 Modelo: Nominación
# -------------------------------
class Nominacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    votos = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<Nominacion {self.nombre} ({self.categoria})>"


# -------------------------------
# 🔹 Modelo: Usuario (Login general)
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
