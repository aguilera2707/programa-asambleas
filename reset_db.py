from app import create_app
from extensions import db
from models import *

app = create_app()

with app.app_context():
    print("⚙️ Eliminando todas las tablas...")
    db.drop_all()
    print("✅ Tablas eliminadas. Recreando estructura...")
    db.create_all()
    print("✅ Estructura recreada correctamente.")
