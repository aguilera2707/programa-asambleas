from app import app
from extensions import db
from models import Nominacion
from datetime import timedelta

with app.app_context():

    MESES_AFECTADOS = {11, 12}   # diciembre corregido a noviembre, lo revertimos también
    DIAS_AFECTADOS = set(range(1, 32))  # todos los días posibles dentro de esas fechas
    revertidas = 0
    saltadas = 0

    print("🔄 Revirtiendo corrección previa de fechas...\n")

    nominaciones = Nominacion.query.all()

    for n in nominaciones:

        if not n.fecha:
            continue

        año = n.fecha.year
        mes = n.fecha.month
        dia = n.fecha.day

        # Revertimos solo las fechas que sabemos fueron movidas
        # (diciembre 1–12 y el 30 de noviembre)
        if (mes == 12 and dia <= 12) or (mes == 11 and dia == 30):
            n.fecha = n.fecha + timedelta(days=1)
            revertidas += 1
        else:
            saltadas += 1

    db.session.commit()

    print(f"✔ Reversión completada.")
    print(f"   ✔ Fechas revertidas: {revertidas}")
    print(f"   ✔ Fechas no tocadas: {saltadas}")