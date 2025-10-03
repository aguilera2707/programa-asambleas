# routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import db, mail
from flask_mail import Message
from models import Valor, Nominacion
from utils import generar_pdf, ciclo_actual
import os

nom = Blueprint('nom', __name__)

# Ruta principal
@nom.route('/')
def principal():
    ciclo = ciclo_actual()
    return render_template('principal.html', ciclo=ciclo)

# Nominación alumno (placeholder)
@nom.route('/nominaciones/alumno', methods=['GET', 'POST'])
def nominar_alumno():
    if request.method == 'POST':
        flash('Nominación de alumno guardada (placeholder).')
        return redirect(url_for('nom.principal'))
    return render_template('nominacion_alumno.html')

# Nominación personal con PDF + correo + registro en BD
@nom.route('/nominaciones/personal', methods=['GET','POST'])
def nominar_personal():
    if request.method == 'POST':
        nominador   = request.form['nominador']
        valores_ids = list(map(int, request.form.getlist('valores')))
        nominado    = request.form['nominado']
        razon       = request.form['razon']

        valores = Valor.query.filter(Valor.id.in_(valores_ids)).all()
        plantilla = os.path.join(os.getcwd(), 'docx_templates', 'formato_asamblea.docx')
        output_dir = os.path.join(os.getcwd(), 'invitaciones', 'personal')

        for valor in valores:
            context = {
                'fecha_evento'    : '2025-08-15',
                'valor'           : valor.nombre,
                'quien_nomina'    : nominador,
                'nominado'        : nominado,
                'texto_adicional' : razon
            }
            filename = f"{nominado}_{valor.nombre}"
            pdf_path = generar_pdf(plantilla, output_dir, context, filename)

            msg = Message(
                subject=f"Invitación Asamblea: {valor.nombre}",
                recipients=[f"{nominado}@colegio.edu.mx"]
            )
            msg.body = (
                f"Hola {nominado},\n\n"
                f"Has sido nominado para el valor «{valor.nombre}» por {nominador}.\n"
                "Adjunto encontrarás tu invitación en PDF.\n\n"
                "¡Nos vemos en la asamblea!\n"
            )
            with open(pdf_path, 'rb') as fp:
                msg.attach(f"{filename}.pdf", "application/pdf", fp.read())
            # mail.send(msg)  # Descomenta esto cuando configures SMTP

            # 🟩 GUARDAR también la nominación en la base de datos
            nueva_nom = Nominacion(
                nombre=nominado,
                categoria=valor.nombre,
                descripcion=razon
            )
            db.session.add(nueva_nom)

        # ⬇️ Confirmamos todo al final
        db.session.commit()

        flash(f'Se generaron y enviaron {len(valores)} invitaciones para {nominado}.')
        return redirect(url_for('nom.principal'))

    valores = Valor.query.all()
    return render_template('nominacion_personal.html', valores=valores)


# Panel de nominaciones (admin)
@nom.route('/admin/nominaciones', methods=['GET', 'POST'])
def panel_nominaciones():
    if request.method == 'POST':
        nombre = request.form['nombre']
        categoria = request.form['categoria']
        descripcion = request.form.get('descripcion', '')
        nueva = Nominacion(nombre=nombre, categoria=categoria, descripcion=descripcion)
        db.session.add(nueva)
        db.session.commit()
        return redirect(url_for('nom.panel_nominaciones'))

    nominaciones = Nominacion.query.all()
    return render_template('admin_nominaciones.html', nominaciones=nominaciones)
