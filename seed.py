# seed.py
from app import app, db
from models import Valor

with app.app_context():
    valores_iniciales = ['Responsabilidad','Respeto','Colaboración','Empatía']
    for nombre in valores_iniciales:
        if not Valor.query.filter_by(nombre=nombre).first():
            db.session.add(Valor(nombre=nombre))
    db.session.commit()
    print("Valores semillados con éxito.")
