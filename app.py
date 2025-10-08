# app.py
from flask import Flask
from extensions import db, mail
from flask_login import LoginManager
from flask_admin import Admin
from dotenv import load_dotenv
import os

# Modelos y vistas admin
from models import Usuario, CicloEscolar
from admin_views import CicloEscolarAdmin

# Blueprints
from routes import nom, admin_bp


# -------------------------------
# 🔹 Cargar variables de entorno (.env)
# -------------------------------
load_dotenv()


def create_app():
    app = Flask(__name__)

    # -------------------------------
    # 🔹 Configuración de base de datos
    # -------------------------------
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',             # Render inyecta esta variable automáticamente
        'sqlite:///local.db'        # Fallback local
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # -------------------------------
    # 🔹 Configuración general
    # -------------------------------
    app.secret_key = os.getenv('SECRET_KEY', 'clave_segura')
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2 MB máx.

    # -------------------------------
    # 🔹 Configuración de correo
    # -------------------------------
    app.config.update(
        MAIL_SERVER='smtp.tu-servidor.com',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME='usuario@dominio.com',
        MAIL_PASSWORD='tu_password',
        MAIL_DEFAULT_SENDER=('Colegio Asambleas', 'no-reply@colegio.edu.mx')
    )

    # -------------------------------
    # 🔹 Inicialización de extensiones
    # -------------------------------
    db.init_app(app)
    mail.init_app(app)

    # -------------------------------
    # 🔹 Configuración de Flask-Login
    # -------------------------------
    login_manager = LoginManager()
    login_manager.login_view = 'nom.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    # -------------------------------
    # 🔹 Configuración de Flask-Admin
    # -------------------------------
    admin = Admin(app, name='Panel Administrativo', template_mode='bootstrap4')
    admin.add_view(CicloEscolarAdmin(CicloEscolar, db.session, category='Configuración'))

    # -------------------------------
    # 🔹 Registrar Blueprints
    # -------------------------------
    app.register_blueprint(nom)
    app.register_blueprint(admin_bp)

    # -------------------------------
    # 🔹 Crear tablas si no existen
    # -------------------------------
    with app.app_context():
        db.create_all()

    return app


# ✅ Punto de entrada estándar para Flask / Render
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
