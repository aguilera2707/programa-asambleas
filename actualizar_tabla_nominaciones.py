# actualizar_tabla_nominaciones.py
from app import app
from extensions import db
from sqlalchemy import text

with app.app_context():
    print("🚀 Verificando tabla 'nominaciones'...")

    comando = """
    ALTER TABLE nominaciones
    ADD COLUMN IF NOT EXISTS comentario TEXT,
    ADD COLUMN IF NOT EXISTS fecha DATE DEFAULT CURRENT_DATE;
    """

    try:
        db.session.execute(text(comando))
        db.session.commit()
        print("✅ Tabla 'nominaciones' actualizada correctamente.")
    except Exception as e:
        print(f"⚠️ Error al actualizar la tabla: {e}")
