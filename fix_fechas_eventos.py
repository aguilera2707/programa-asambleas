# fix_fechas_eventos.py
from app import app
from extensions import db
from models import EventoAsamblea
from datetime import datetime
from zoneinfo import ZoneInfo

MX = ZoneInfo("America/Merida")
UTC = ZoneInfo("UTC")

with app.app_context():
    eventos = EventoAsamblea.query.all()
    print(f"Corrigiendo {len(eventos)} eventos...")

    for e in eventos:
        # Fecha de cierre (datetime naive guardada como si fuera UTC)
        fecha_original = e.fecha_cierre_nominaciones

        # Si ya está corregida (tiene hora típica de UTC convertida), no hacemos nada
        # Caso típico corregido: fechas que terminan en 03:00, 04:00, 05:00
        if fecha_original.tzinfo is None:
            # Interpretamos lo guardado como hora LOCAL de México (lo que realmente dijiste al crear el evento)
            local_dt = fecha_original.replace(tzinfo=MX)

            # Convertimos a UTC (la hora real que debe usarse en el sistema)
            utc_dt = local_dt.astimezone(UTC).replace(tzinfo=None)

            print(f"Corrigiendo evento {e.id}: {fecha_original} → {utc_dt}")

            e.fecha_cierre_nominaciones = utc_dt

    db.session.commit()
    print("✔ Corrección aplicada con éxito")
