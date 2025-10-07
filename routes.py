# routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, mail
from flask_mail import Message
from models import Valor, Nominacion, Usuario
from utils import generar_pdf, ciclo_actual
from werkzeug.utils import secure_filename
import pandas as pd
from flask import send_file
from io import BytesIO
from flask import jsonify
import os

nom = Blueprint('nom', __name__)

# --- Rutas principales y nominaciones ---
@nom.route('/')
@login_required
def principal():
    ciclo = ciclo_actual()
    return render_template('principal.html', ciclo=ciclo, usuario=current_user)

@nom.route('/nominaciones/alumno', methods=['GET', 'POST'])
def nominar_alumno():
    if request.method == 'POST':
        flash('Nominación de alumno guardada (placeholder).')
        return redirect(url_for('nom.principal'))
    return render_template('nominacion_alumno.html')

@nom.route('/nominaciones/personal', methods=['GET','POST'])
def nominar_personal():
    if request.method == 'POST':
        nominador   = request.form['nominador']
        valores_ids = list(map(int, request.form.getlist('valores')))
        nominado    = request.form['nominado']
        razon       = request.form['razon']

        valores = Valor.query.filter(Valor.id.in_(valores_ids)).all()
        output_dir = os.path.join(os.getcwd(), 'invitaciones', 'personal')

        for valor in valores:
            context = {
                'fecha_evento': '2025-08-15',
                'valor': valor.nombre,
                'quien_nomina': nominador,
                'nominado': nominado,
                'texto_adicional': razon
            }
            filename = f"{nominado}_{valor.nombre}"

            pdf_path = generar_pdf('invitacion.html', context, output_dir, filename)

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
            # mail.send(msg)  # Descomenta cuando configures SMTP

            nueva_nom = Nominacion(nombre=nominado, categoria=valor.nombre, descripcion=razon)
            db.session.add(nueva_nom)

        db.session.commit()
        flash(f'Se generaron y enviaron {len(valores)} invitaciones para {nominado}.')
        return redirect(url_for('nom.principal'))

    valores = Valor.query.all()
    return render_template('nominacion_personal.html', valores=valores)

# --- Panel nominaciones admin ---
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

# --- Login ---
@nom.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = Usuario.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f'Bienvenido, {user.nombre}', 'success')
            return redirect(url_for('nom.principal'))
        else:
            flash('Correo o contraseña incorrectos', 'danger')

    return render_template('login.html')

# --- Crear usuario ---
@nom.route('/crear_usuario', methods=['GET', 'POST'])
@login_required
def crear_usuario():
    if current_user.rol != 'admin':
        flash("Acceso denegado: solo los administradores pueden crear usuarios.", "warning")
        return redirect(url_for('nom.principal'))

    mensaje = None

    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        email = request.form['correo'].strip().lower()
        password = request.form['password']
        rol = request.form['rol']

        if not nombre or not email or not password or not rol:
            mensaje = "⚠️ Todos los campos son obligatorios."
            return render_template('crear_usuario.html', mensaje=mensaje)

        existente = Usuario.query.filter_by(email=email).first()
        if existente:
            mensaje = "⚠️ Ya existe un usuario registrado con ese correo."
            return render_template('crear_usuario.html', mensaje=mensaje)

        nuevo_usuario = Usuario(nombre=nombre, email=email, rol=rol)
        nuevo_usuario.set_password(password)

        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            mensaje = "✅ Usuario creado con éxito."
        except Exception as e:
            db.session.rollback()
            mensaje = f"❌ Error al crear el usuario: {str(e)}"

    return render_template('crear_usuario.html', mensaje=mensaje)

@nom.route('/admin')
@login_required
def panel_admin():
    if current_user.rol != 'admin':
        flash("🚫 Se necesita ser administrador para poder acceder a este apartado.", "danger")
        return redirect(url_for('nom.principal'))
    return render_template('panel_admin.html')

# --- Cerrar sesión ---
@nom.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for('nom.login'))

import tempfile
UPLOAD_FOLDER = tempfile.gettempdir()  # ✅ Usa carpeta temporal del sistema (Windows/Linux compatible)
ALLOWED_EXTENSIONS = {'xlsx', 'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@nom.route('/admin/usuarios/importar/<rol>', methods=['POST'])
@login_required
def importar_usuarios(rol):
    if current_user.rol != 'admin':
        flash("🚫 No tienes permisos para importar usuarios.", "danger")
        return redirect(url_for('nom.panel_usuarios'))

    file = request.files.get('file')
    if not file or file.filename == '':
        flash("⚠️ No se seleccionó ningún archivo.", "warning")
        return redirect(url_for('nom.panel_usuarios'))

    if not allowed_file(file.filename):
        flash("❌ Solo se permiten archivos Excel (.xlsx) o CSV.", "danger")
        return redirect(url_for('nom.panel_usuarios'))

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    try:
        # Leer archivo Excel o CSV
        if filename.endswith('.xlsx'):
            df = pd.read_excel(filepath)
        else:
            df = pd.read_csv(filepath)

        # Validar columnas requeridas
        columnas_requeridas = {'nombre', 'email', 'contraseña'}
        if not columnas_requeridas.issubset(set(df.columns.str.lower())):
            flash("❌ La plantilla no contiene las columnas requeridas (nombre, email, contraseña).", "danger")
            return redirect(url_for('nom.panel_usuarios'))

        usuarios_creados = 0
        for _, row in df.iterrows():
            nombre = str(row['nombre']).strip()
            email = str(row['email']).strip().lower()
            password = str(row['contraseña']).strip()

            if not nombre or not email or not password:
                continue

            existente = Usuario.query.filter_by(email=email).first()
            if existente:
                continue  # Evitar duplicados

            nuevo_usuario = Usuario(nombre=nombre, email=email, rol=rol)
            nuevo_usuario.set_password(password)
            db.session.add(nuevo_usuario)
            usuarios_creados += 1

            # Guardar por lotes de 50 para no saturar
            if usuarios_creados % 50 == 0:
                db.session.commit()

        db.session.commit()
        flash(f"✅ Se importaron correctamente {usuarios_creados} usuarios del rol {rol}.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al procesar el archivo: {str(e)}", "danger")

    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

    return redirect(url_for('nom.panel_usuarios'))

@nom.route('/admin/usuarios')
@login_required
def panel_usuarios():
    if current_user.rol != 'admin':
        flash("🚫 Solo los administradores pueden acceder a esta sección.", "danger")
        return redirect(url_for('nom.principal'))
    return render_template('panel_usuarios.html')

@nom.route('/admin/usuarios/plantilla/<rol>')
@login_required
def descargar_plantilla(rol):
    if current_user.rol != 'admin':
        flash("🚫 Solo los administradores pueden descargar plantillas.", "danger")
        return redirect(url_for('nom.panel_usuarios'))

    # Crea la plantilla base
    columnas = ["nombre", "email", "contraseña"]
    df = pd.DataFrame(columns=columnas)

    # Usa BytesIO para evitar escribir en disco
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=f"{rol.capitalize()}s")

    output.seek(0)
    filename = f"Plantilla_{rol}.xlsx"

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
@nom.route('/admin/usuarios/lista/<rol>')
@login_required
def lista_usuarios(rol):
    if current_user.rol != 'admin':
        return jsonify({"error": "No autorizado"}), 403

    usuarios = Usuario.query.filter_by(rol=rol).all()
    data = [
        {
            "id": u.id,
            "nombre": u.nombre,
            "email": u.email,
            "rol": u.rol
        }
        for u in usuarios
    ]
    return jsonify(data)


@nom.route('/admin/usuarios/eliminar/<int:id>', methods=['DELETE'])
@login_required
def eliminar_usuario(id):
    if current_user.rol != 'admin':
        return jsonify({"message": "No autorizado"}), 403

    usuario = Usuario.query.get(id)
    if not usuario:
        return jsonify({"message": "Usuario no encontrado"}), 404

    db.session.delete(usuario)
    db.session.commit()
    return jsonify({"message": f"Usuario {usuario.nombre} eliminado correctamente."}), 200