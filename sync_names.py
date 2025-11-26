# sync_names.py
"""
Sincroniza los nombres entre las tablas Maestro y Usuario.
Actualiza usuario.nombre = maestro.nombre siempre que coincidan los correos.

Ejecutar una sola vez:
    python sync_names.py
"""

from app import app
from extensions import db
from models import Usuario, Maestro

with app.app_context():
    maestros = Maestro.query.all()
    cambios = 0
    sin_usuario = []

    for maestro in maestros:
        usuario = Usuario.query.filter_by(email=maestro.correo).first()

        if usuario:
            if usuario.nombre != maestro.nombre:
                print(f"↪ Corrigiendo: {usuario.email}")
                print(f"    Antes: {usuario.nombre}")
                print(f"    Después: {maestro.nombre}")
                usuario.nombre = maestro.nombre
                cambios += 1
        else:
            # Si existiera un maestro sin usuario, lo mostramos
            sin_usuario.append(maestro.correo)

    db.session.commit()

    print("\n---------------------------------------")
    print(f"✔ Sincronización completa.")
    print(f"✔ Nombres actualizados: {cambios}")

    if sin_usuario:
        print("⚠ Maestros sin usuario relacionado:")
        for c in sin_usuario:
            print("   -", c)
    else:
        print("✔ Todos los maestros tienen usuario relacionado.")
