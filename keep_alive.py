# keep_alive.py
import time
import requests

URL = "https://programa-asambleas.onrender.com/login"  # puedes usar /login o /, según cuál cargue más rápido
INTERVALO_MINUTOS = 3  # Render suele dormir después de ~15 min de inactividad

def mantener_activo():
    while True:
        try:
            r = requests.get(URL, timeout=10)
            print(f"[KEEP-ALIVE] Ping a {URL} → {r.status_code}")
        except Exception as e:
            print(f"[KEEP-ALIVE] Error: {e}")
        time.sleep(INTERVALO_MINUTOS * 60)

if __name__ == "__main__":
    mantener_activo()
