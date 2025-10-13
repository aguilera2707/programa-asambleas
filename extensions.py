# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_migrate import Migrate
import os

db = SQLAlchemy()
mail = Mail()
migrate = Migrate()

def init_extensions(app):
    """Inicializa todas las extensiones con reconexión automática a Neon."""
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///local.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,  # 🔹 Detecta conexiones caídas
        "pool_recycle": 280,    # 🔹 Reabre conexión si está inactiva > 4 min
    }

    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    print(" Extensiones inicializadas correctamente.")
