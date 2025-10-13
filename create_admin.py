from extensions import db
from models import Usuario
from werkzeug.security import generate_password_hash
from app import app

# Configura el nuevo usuario admin
nombre_admin = "Administrador General"
email_admin = "admin@cela.edu.mx"
password_admin = "12345"
rol_admin = "admin"

with app.app_context():
    # Verifica si ya existe
    existente = Usuario.query.filter_by(email=email_admin).first()
    if existente:
        print("✅ Ya existe un administrador con ese correo.")
    else:
        nuevo_admin = Usuario(
            nombre=nombre_admin,
            email=email_admin,
            password_hash=generate_password_hash(password_admin),
            rol=rol_admin
        )
        db.session.add(nuevo_admin)
        db.session.commit()
        print("🎉 Administrador creado correctamente:")
        print(f"Correo: {email_admin}")
        print(f"Contraseña: {password_admin}")
