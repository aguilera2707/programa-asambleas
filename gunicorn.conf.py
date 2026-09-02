# La importación anual de maestros actualiza decenas de contraseñas de forma
# segura. Ese trabajo puede superar el límite predeterminado de 30 segundos de
# Gunicorn en los recursos compartidos de Render.
timeout = 120
graceful_timeout = 120
