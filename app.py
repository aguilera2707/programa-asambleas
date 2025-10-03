# app.py

from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from extensions import db, mail
from models import Valor, CicloEscolar, Bloque, Alumno
from admin_views import CicloEscolarAdmin
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

# Inicialización de extensiones
db.init_app(app)
mail.init_app(app)

# Panel de administración
admin = Admin(app, name='Panel Admin', template_mode='bootstrap4')
admin.add_view(ModelView(Valor, db.session, category='Configuración'))
admin.add_view(CicloEscolarAdmin(CicloEscolar, db.session, category='Configuración'))
admin.add_view(ModelView(Bloque, db.session, category='Configuración'))
admin.add_view(ModelView(Alumno, db.session, category='Alumnos'))

# Rutas (Blueprint)
from routes import nom
app.register_blueprint(nom)

# Iniciar app
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
