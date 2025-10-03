from extensions import db

class Valor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)

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
        return f'<CicloEscolar {self.nombre}>'

class Bloque(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)

class Alumno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    grado = db.Column(db.String(20), nullable=False)
    grupo = db.Column(db.String(5), nullable=False)
    nivel = db.Column(db.String(50), nullable=False)
    ciclo_id = db.Column(db.Integer, db.ForeignKey('ciclo_escolar.id'))
    

class Nominacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    votos = db.Column(db.Integer, default=0)    
