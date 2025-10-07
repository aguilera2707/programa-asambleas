from flask import Flask
from extensions import db, mail
from models import Valor, CicloEscolar, Bloque, Alumno, Usuario
from flask_login import LoginManager
import os


app = Flask(__name__)
app.secret_key = 'clave_segura'

# Configuración de base de datos y correo
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config.update(
    MAIL_SERVER='smtp.tu-servidor.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='usuario@dominio.com',
    MAIL_PASSWORD='tu_password',
    MAIL_DEFAULT_SENDER=('Colegio Asambleas', 'no-reply@colegio.edu.mx')
)
# 🔹 Límite de tamaño para archivos subidos (2 MB)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

# --- 🔐 Configuración de Flask-Login ---
login_manager = LoginManager()
login_manager.login_view = 'nom.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))
# ---------------------------------------


# Inicialización de extensiones
db.init_app(app)
mail.init_app(app)

# Crear tablas si no existen
with app.app_context():
    db.create_all()

# Rutas (Blueprint)
from routes import nom
app.register_blueprint(nom)

# Iniciar app
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
