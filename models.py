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
    valores = db.relationship('Valor', back_populates='ciclo', lazy=True)


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
    ciclo_id = db.Column(db.Integer, db.ForeignKey('ciclos_escolares.id'), nullable=False)

    def __repr__(self):
        return f"<Maestro {self.nombre}>"


# -------------------------------
# 🔹 Modelo: Bloque
# -------------------------------
class Bloque(db.Model):
    __tablename__ = 'bloques'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    ciclo_id = db.Column(db.Integer, db.ForeignKey('ciclos_escolares.id'), nullable=False)

    # Relación inversa: cada bloque tiene muchos alumnos
    alumnos = db.relationship('Alumno', backref='bloque', lazy=True)

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

    ciclo_id = db.Column(db.Integer, db.ForeignKey('ciclos_escolares.id'), nullable=False)
    bloque_id = db.Column(db.Integer, db.ForeignKey('bloques.id'), nullable=True)

    def __repr__(self):
        return f"<Alumno {self.nombre} - {self.grado}{self.grupo}>"


# -------------------------------
# 🔹 Modelo: Valor institucional (dependiente del ciclo)
# -------------------------------
class Valor(db.Model):
    __tablename__ = 'valores'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    ciclo_id = db.Column(db.Integer, db.ForeignKey('ciclos_escolares.id'), nullable=False)  # ✅ FIX
    activo = db.Column(db.Boolean, default=True)

    ciclo = db.relationship('CicloEscolar', back_populates='valores', lazy=True)

    __table_args__ = (
        db.UniqueConstraint('nombre', 'ciclo_id', name='unique_valor_por_ciclo'),
    )

    def __repr__(self):
        return f"<Valor {self.nombre}>"


# -------------------------------
# 🔹 Modelo: Nominación (alumno o personal)
# -------------------------------
class Nominacion(db.Model):
    __tablename__ = 'nominaciones'

    id = db.Column(db.Integer, primary_key=True)

    # Puede ser una nominación a alumno o a maestro
    alumno_id = db.Column(db.Integer, db.ForeignKey('alumnos.id'), nullable=True)
    maestro_nominado_id = db.Column(db.Integer, db.ForeignKey('maestros.id'), nullable=True)

    # Quien hace la nominación (siempre es un maestro)
    maestro_id = db.Column(db.Integer, db.ForeignKey('maestros.id'), nullable=False)

    # Valor institucional asociado
    valor_id = db.Column(db.Integer, db.ForeignKey('valores.id'), nullable=False)
    ciclo_id = db.Column(db.Integer, db.ForeignKey('ciclos_escolares.id'), nullable=False)

    comentario = db.Column(db.Text, nullable=True)
    fecha = db.Column(db.Date, default=db.func.current_date())

    # Relaciones
    alumno = db.relationship('Alumno', foreign_keys=[alumno_id], backref='nominaciones_alumno', lazy=True)
    maestro = db.relationship('Maestro', foreign_keys=[maestro_id], backref='nominaciones_hechas', lazy=True)
    maestro_nominado = db.relationship('Maestro', foreign_keys=[maestro_nominado_id], backref='nominaciones_recibidas', lazy=True)
    valor = db.relationship('Valor', backref='nominaciones_valor', lazy=True)
    ciclo = db.relationship('CicloEscolar', backref='nominaciones_registradas', lazy=True)
    tipo = db.Column(db.String(20), default='alumno')  # 'alumno' o 'personal'

    def __repr__(self):
        if self.alumno_id:
            return f"<Nominacion Alumno {self.alumno_id} - Valor {self.valor_id}>"
        elif self.maestro_nominado_id:
            return f"<Nominacion Maestro {self.maestro_nominado_id} - Valor {self.valor_id}>"
        else:
            return f"<Nominacion sin objetivo - Valor {self.valor_id}>"





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
