from flask import Flask
from extensions import db, mail
from flask_login import LoginManager
import os
from models import Usuario
from routes import nom  # importa blueprint aquí directamente

from dotenv import load_dotenv
load_dotenv()

def create_app():
    app = Flask(__name__)

    # -------------------------------
    # 🔹 Configuración de base de datos
    # -------------------------------
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',  # URL de Neon (Render la inyecta automáticamente)
        'sqlite:///local.db'  # Fallback para entorno local
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # -------------------------------
    # 🔹 Configuración general
    # -------------------------------
    app.secret_key = 'clave_segura'
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # Límite de 2 MB

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
    # 🔹 Registrar Blueprint principal
    # -------------------------------
    app.register_blueprint(nom)

    # -------------------------------
    # 🔹 Crear tablas si no existen
    # -------------------------------
    with app.app_context():
        db.create_all()

    return app


# ✅ Punto de entrada estándar para Flask y Render
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
