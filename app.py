# app.py
from flask import Flask
from flask_login import LoginManager
from flask_admin import Admin
from dotenv import load_dotenv
import os

# Extensiones centralizadas
from extensions import init_extensions, db
from models import Usuario, CicloEscolar
from admin_views import CicloEscolarAdmin
from routes import nom, admin_bp

# Cargar variables de entorno
load_dotenv()

def create_app():
    app = Flask(__name__)

    # 🔹 Configuración general
    app.secret_key = os.getenv("SECRET_KEY", "clave_segura")
    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2 MB máx.

    # 🔹 Configuración de correo
    app.config.update(
        MAIL_SERVER="smtp.tu-servidor.com",
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME="usuario@dominio.com",
        MAIL_PASSWORD="tu_password",
        MAIL_DEFAULT_SENDER=("Colegio Asambleas", "no-reply@colegio.edu.mx"),
    )

    # ✅ Inicializar todas las extensiones en un solo lugar
    init_extensions(app)

    # 🔹 Configurar Login
    login_manager = LoginManager()
    login_manager.login_view = "nom.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    # 🔹 Flask-Admin
    admin = Admin(app, name="Panel Administrativo", template_mode="bootstrap4")
    admin.add_view(CicloEscolarAdmin(CicloEscolar, db.session, category="Configuración"))

    # 🔹 Registrar Blueprints
    app.register_blueprint(nom)
    app.register_blueprint(admin_bp)

    # 🔹 Crear tablas si no existen
    with app.app_context():
        db.create_all()

    return app

# Punto de entrada
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
