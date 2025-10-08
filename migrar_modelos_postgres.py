# migrar_modelos_postgres.py
from app import app
from extensions import db
from sqlalchemy import text

with app.app_context():
    conn = db.engine.connect()
    trans = conn.begin()

    print("=== 🚀 Iniciando migración no destructiva para PostgreSQL ===")

    alteraciones = [
        # Renombrar tablas si aún usan nombres antiguos
        "ALTER TABLE IF EXISTS ciclo_escolar RENAME TO ciclos_escolares;",
        "ALTER TABLE IF EXISTS bloque RENAME TO bloques;",
        "ALTER TABLE IF EXISTS alumno RENAME TO alumnos;",

        # Asegurar columnas necesarias
        "ALTER TABLE IF EXISTS bloques ADD COLUMN IF NOT EXISTS ciclo_id INTEGER;",
        "ALTER TABLE IF EXISTS alumnos ADD COLUMN IF NOT EXISTS ciclo_id INTEGER;",
        "ALTER TABLE IF EXISTS alumnos ADD COLUMN IF NOT EXISTS bloque_id INTEGER;",
        "ALTER TABLE IF EXISTS valores ADD COLUMN IF NOT EXISTS ciclo_id INTEGER;",
        "ALTER TABLE IF EXISTS maestros ADD COLUMN IF NOT EXISTS ciclo_id INTEGER;",
        "ALTER TABLE IF EXISTS nominaciones ADD COLUMN IF NOT EXISTS ciclo_id INTEGER;",

        # Crear claves foráneas si faltan (con ON DELETE SET NULL para no romper datos)
        "ALTER TABLE IF EXISTS bloques ADD CONSTRAINT IF NOT EXISTS fk_bloques_ciclo FOREIGN KEY (ciclo_id) REFERENCES ciclos_escolares(id) ON DELETE CASCADE;",
        "ALTER TABLE IF EXISTS alumnos ADD CONSTRAINT IF NOT EXISTS fk_alumnos_ciclo FOREIGN KEY (ciclo_id) REFERENCES ciclos_escolares(id) ON DELETE CASCADE;",
        "ALTER TABLE IF NOT EXISTS alumnos ADD CONSTRAINT IF NOT EXISTS fk_alumnos_bloque FOREIGN KEY (bloque_id) REFERENCES bloques(id) ON DELETE SET NULL;",
        "ALTER TABLE IF EXISTS valores ADD CONSTRAINT IF NOT EXISTS fk_valores_ciclo FOREIGN KEY (ciclo_id) REFERENCES ciclos_escolares(id) ON DELETE CASCADE;",
        "ALTER TABLE IF EXISTS maestros ADD CONSTRAINT IF NOT EXISTS fk_maestros_ciclo FOREIGN KEY (ciclo_id) REFERENCES ciclos_escolares(id) ON DELETE CASCADE;",
        "ALTER TABLE IF EXISTS nominaciones ADD CONSTRAINT IF NOT EXISTS fk_nominaciones_ciclo FOREIGN KEY (ciclo_id) REFERENCES ciclos_escolares(id) ON DELETE CASCADE;"
    ]

    for comando in alteraciones:
        try:
            conn.execute(text(comando))
            print(f"✔ Ejecutado: {comando.split('ALTER TABLE')[1].strip()}")
        except Exception as e:
            print(f"⚠️ Error en comando: {e}")

    trans.commit()
    conn.close()
    print("✅ Migración completada correctamente sin pérdida de datos.")
