# routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, mail
from flask_mail import Message
from werkzeug.utils import secure_filename
from models import Valor, Nominacion, Usuario, CicloEscolar
from utils import generar_pdf, ciclo_actual
import pandas as pd
import tempfile
import os
from io import BytesIO
from models import Maestro
from models import Alumno, Bloque
from flask import send_file
from datetime import datetime
from flask import send_file, request, jsonify
from flask import jsonify


# -------------------------------
# 🔹 Definición de Blueprints
# -------------------------------
nom = Blueprint('nom', __name__)
admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')


# -------------------------------
# 🔹 Ruta Keep-Alive (para evitar que Render se duerma)
# -------------------------------
@nom.route("/keepalive")
def keepalive():
    return "OK", 200

@nom.route("/status")
def status():
    return "OK", 200


# -------------------------------
# 🔹 Página principal (protegida)
# -------------------------------
@nom.route('/')
@login_required
def principal():
    ciclo = ciclo_actual()
    return render_template('principal.html', ciclo=ciclo, usuario=current_user)




# -------------------------------
# 🔹 Login y logout
# -------------------------------
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


@nom.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for('nom.login'))


# -------------------------------
# 🔹 Panel de administración general
# -------------------------------
@nom.route('/admin')
@login_required
def panel_admin():
    if current_user.rol != 'admin':
        flash("🚫 Se necesita ser administrador para poder acceder a este apartado.", "danger")
        return redirect(url_for('nom.principal'))
    return render_template('panel_admin.html')


# -------------------------------
# 🔹 Crear usuario manualmente
# -------------------------------
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


# -------------------------------
# 🔹 Importar usuarios desde Excel o CSV
# -------------------------------
UPLOAD_FOLDER = tempfile.gettempdir()
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
        if filename.endswith('.xlsx'):
            df = pd.read_excel(filepath)
        else:
            df = pd.read_csv(filepath)

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
                continue

            nuevo_usuario = Usuario(nombre=nombre, email=email, rol=rol)
            nuevo_usuario.set_password(password)
            db.session.add(nuevo_usuario)
            usuarios_creados += 1

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


# -------------------------------
# 🔹 Panel de usuarios
# -------------------------------
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

    columnas = ["nombre", "email", "contraseña"]
    df = pd.DataFrame(columns=columnas)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=f"{rol.capitalize()}s")
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=f"Plantilla_{rol}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@nom.route('/admin/usuarios/lista/<rol>')
@login_required
def lista_usuarios(rol):
    if current_user.rol != 'admin':
        return jsonify({"error": "No autorizado"}), 403

    usuarios = Usuario.query.filter_by(rol=rol).all()
    data = [
        {"id": u.id, "nombre": u.nombre, "email": u.email, "rol": u.rol}
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


# -------------------------------
# 🔹 Ruta de prueba de conexión a Neon
# -------------------------------
@nom.route("/check_db")
def check_db():
    try:
        db.session.execute("SELECT 1")
        return "✅ Conectado correctamente a Neon.tech"
    except Exception as e:
        return f"❌ Error de conexión: {e}"


# -------------------------------
# 🔹 Administración de ciclos escolares
# -------------------------------
@admin_bp.route('/ciclos', methods=['GET', 'POST'])
def gestionar_ciclos():
    ciclos = CicloEscolar.query.order_by(CicloEscolar.id.desc()).all()
    if request.method == 'POST':
        nombre = request.form['nombre']
        inicio = request.form.get('fecha_inicio')
        fin = request.form.get('fecha_fin')
        nuevo = CicloEscolar(nombre=nombre, fecha_inicio=inicio, fecha_fin=fin)
        db.session.add(nuevo)
        db.session.commit()
        flash(f'Ciclo {nombre} creado correctamente.')
        return redirect(url_for('admin_bp.gestionar_ciclos'))
    return render_template('admin_ciclos.html', ciclos=ciclos)


# -------------------------------
# 🔹 Activar un ciclo escolar
# -------------------------------
@admin_bp.route('/ciclos/activar/<int:ciclo_id>', methods=['POST'])
def activar_ciclo(ciclo_id):
    ciclo = CicloEscolar.query.get_or_404(ciclo_id)

    # Desactivar todos los demás
    CicloEscolar.query.update({CicloEscolar.activo: False})

    # Activar este
    ciclo.activo = True
    db.session.commit()

    return jsonify({"success": True, "activo_id": ciclo_id})

# -------------------------------
# 🔹 Importar maestros al ciclo activo
# -------------------------------
@admin_bp.route('/maestros/importar', methods=['POST'])
@login_required
def importar_maestros_ciclo():
    if current_user.rol != 'admin':
        flash("🚫 Solo los administradores pueden importar maestros.", "danger")
        return redirect(url_for('nom.panel_usuarios'))

    file = request.files.get('file')
    if not file or file.filename == '':
        flash("⚠️ No se seleccionó ningún archivo.", "warning")
        return redirect(url_for('admin_bp.maestros_ciclo'))

    filename = secure_filename(file.filename)
    filepath = os.path.join(tempfile.gettempdir(), filename)
    file.save(filepath)

    try:
        # Detectar formato
        df = pd.read_excel(filepath) if filename.endswith('.xlsx') else pd.read_csv(filepath)

        columnas_requeridas = {'nombre', 'email'}
        if not columnas_requeridas.issubset(set(df.columns.str.lower())):
            flash("❌ La plantilla debe contener las columnas: nombre, correo.", "danger")
            return redirect(url_for('admin_bp.maestros_ciclo'))

        # Obtener ciclo activo
        ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
        if not ciclo_activo:
            flash("⚠️ No hay ningún ciclo activo. Activa un ciclo primero.", "warning")
            return redirect(url_for('admin_bp.gestionar_ciclos'))

        importados, existentes = 0, 0
        for _, row in df.iterrows():
            nombre = str(row['nombre']).strip()
            correo = str(row['email']).strip().lower()

            if not nombre or not correo:
                continue

            # Si ya existe usuario con ese correo, lo reusamos
            usuario = Usuario.query.filter_by(email=correo).first()
            if not usuario:
                usuario = Usuario(nombre=nombre, email=correo, rol='profesor')
                usuario.set_password('123456')  # contraseña temporal
                db.session.add(usuario)

            # Verificar si ya está en la tabla maestros
            existe_maestro = Maestro.query.filter_by(correo=correo, ciclo_id=ciclo_activo.id).first()
            if existe_maestro:
                existentes += 1
                continue

            maestro = Maestro(nombre=nombre, correo=correo, ciclo_id=ciclo_activo.id)
            db.session.add(maestro)
            importados += 1

        db.session.commit()
        flash(f"✅ {importados} maestros importados al ciclo {ciclo_activo.nombre}. {existentes} ya existían.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al importar: {e}", "danger")

    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

    return redirect(url_for('admin_bp.maestros_ciclo'))

# -------------------------------
# 🔹 Listado de maestros del ciclo activo
# -------------------------------
@admin_bp.route('/maestros')
@login_required
def maestros_ciclo():
    if current_user.rol != 'admin':
        flash("🚫 Solo los administradores pueden acceder.", "danger")
        return redirect(url_for('nom.principal'))

    ciclo = CicloEscolar.query.filter_by(activo=True).first()
    maestros = Maestro.query.filter_by(ciclo_id=ciclo.id).all() if ciclo else []
    return render_template('admin_maestros.html', maestros=maestros, ciclo=ciclo)

# -------------------------------
# 🔹 Listado e importación de alumnos del ciclo activo
# -------------------------------
@admin_bp.route('/alumnos', methods=['GET'])
@login_required
def alumnos_ciclo():
    if current_user.rol != 'admin':
        flash("🚫 Solo los administradores pueden acceder.", "danger")
        return redirect(url_for('nom.principal'))

    ciclo = CicloEscolar.query.filter_by(activo=True).first()
    alumnos = Alumno.query.filter_by(ciclo_id=ciclo.id).all() if ciclo else []
    bloques = Bloque.query.filter_by(ciclo_id=ciclo.id).all() if ciclo else []

    return render_template('admin_alumnos.html', alumnos=alumnos, ciclo=ciclo, bloques=bloques)


# -------------------------------
# 🔹 Importar alumnos al ciclo activo (normalizado y sin duplicados)
# -------------------------------
@admin_bp.route('/alumnos/importar', methods=['POST'])
@login_required
def importar_alumnos_ciclo():
    if current_user.rol != 'admin':
        flash("🚫 Solo los administradores pueden importar alumnos.", "danger")
        return redirect(url_for('nom.principal'))

    file = request.files.get('file')
    if not file or file.filename == '':
        flash("⚠️ No se seleccionó ningún archivo.", "warning")
        return redirect(url_for('admin_bp.alumnos_ciclo'))

    filename = secure_filename(file.filename)
    filepath = os.path.join(tempfile.gettempdir(), filename)
    file.save(filepath)

    try:
        # Detectar formato (Excel o CSV)
        df = pd.read_excel(filepath) if filename.endswith('.xlsx') else pd.read_csv(filepath)
        df.columns = [c.strip().lower() for c in df.columns]  # Normaliza encabezados

        columnas_requeridas = {'nombre', 'grado', 'grupo', 'nivel', 'bloque'}
        if not columnas_requeridas.issubset(set(df.columns)):
            faltan = ", ".join(columnas_requeridas - set(df.columns))
            flash(f"❌ La plantilla debe contener las columnas: {faltan}", "danger")
            return redirect(url_for('admin_bp.alumnos_ciclo'))

        ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
        if not ciclo_activo:
            flash("⚠️ No hay un ciclo activo. Activa un ciclo primero.", "warning")
            return redirect(url_for('admin_bp.gestionar_ciclos'))

        importados, existentes = 0, 0

        for _, row in df.iterrows():
            nombre = str(row["nombre"]).strip().title()
            grado = str(row["grado"]).strip()
            grupo = str(row["grupo"]).strip().upper()
            nivel = str(row["nivel"]).strip().capitalize()
            bloque_nombre = str(row["bloque"]).strip()

            if not (nombre and grado and grupo and nivel and bloque_nombre):
                continue

            # Buscar o crear bloque
            bloque = Bloque.query.filter_by(nombre=bloque_nombre, ciclo_id=ciclo_activo.id).first()
            if not bloque:
                bloque = Bloque(nombre=bloque_nombre, ciclo_id=ciclo_activo.id)
                db.session.add(bloque)
                db.session.commit()

            # Evita duplicados ignorando mayúsculas/minúsculas
            ya = Alumno.query.filter(
                db.func.lower(Alumno.nombre) == nombre.lower(),
                Alumno.grado == grado,
                db.func.upper(Alumno.grupo) == grupo.upper(),
                Alumno.ciclo_id == ciclo_activo.id
            ).first()

            if ya:
                existentes += 1
                continue

            nuevo = Alumno(
                nombre=nombre,
                grado=grado,
                grupo=grupo,
                nivel=nivel,
                ciclo_id=ciclo_activo.id,
                bloque_id=bloque.id
            )
            db.session.add(nuevo)
            importados += 1

        db.session.commit()
        flash(f"✅ {importados} alumnos importados al ciclo {ciclo_activo.nombre}. {existentes} ya existían.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al importar alumnos: {e}", "danger")

    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

    return redirect(url_for('admin_bp.alumnos_ciclo'))


# -------------------------------
# 🔹 Gestión de Bloques del Ciclo Activo
# -------------------------------
@admin_bp.route('/bloques', methods=['GET', 'POST'])
@login_required
def bloques_ciclo():
    if current_user.rol != 'admin':
        flash("🚫 Solo los administradores pueden acceder.", "danger")
        return redirect(url_for('nom.principal'))

    ciclo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo:
        flash("⚠️ No hay un ciclo activo. Activa un ciclo antes de administrar bloques.", "warning")
        return redirect(url_for('admin_bp.gestionar_ciclos'))

    # Crear bloque manualmente
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        if not nombre:
            flash("⚠️ El nombre del bloque no puede estar vacío.", "warning")
            return redirect(url_for('admin_bp.bloques_ciclo'))

        existente = Bloque.query.filter_by(nombre=nombre, ciclo_id=ciclo.id).first()
        if existente:
            flash(f"⚠️ El bloque '{nombre}' ya existe en este ciclo.", "warning")
        else:
            nuevo = Bloque(nombre=nombre, ciclo_id=ciclo.id)
            db.session.add(nuevo)
            db.session.commit()
            flash(f"✅ Bloque '{nombre}' creado exitosamente.", "success")

        return redirect(url_for('admin_bp.bloques_ciclo'))

    # Mostrar lista de bloques del ciclo actual
    bloques = (
        db.session.query(Bloque)
        .filter_by(ciclo_id=ciclo.id)
        .order_by(Bloque.id.asc())
        .all()
    )

    # Contar alumnos por bloque
    conteos = {
        b.id: Alumno.query.filter_by(bloque_id=b.id).count() for b in bloques
    }

    return render_template('admin_bloques.html', ciclo=ciclo, bloques=bloques, conteos=conteos)


# -------------------------------
# 🔹 Eliminar bloque (solo si está vacío)
# -------------------------------
@admin_bp.route('/bloques/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_bloque(id):
    if current_user.rol != 'admin':
        return jsonify({"error": "No autorizado"}), 403

    bloque = Bloque.query.get_or_404(id)
    alumnos_asociados = Alumno.query.filter_by(bloque_id=bloque.id).count()

    if alumnos_asociados > 0:
        flash("❌ No se puede eliminar un bloque con alumnos asignados.", "danger")
        return redirect(url_for('admin_bp.bloques_ciclo'))

    db.session.delete(bloque)
    db.session.commit()
    flash(f"🗑️ Bloque '{bloque.nombre}' eliminado correctamente.", "success")
    return redirect(url_for('admin_bp.bloques_ciclo'))

ALLOWED_EXT_ALUMNOS = {"xlsx", "csv"}

def _allowed_file_alumnos(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT_ALUMNOS

# -------------------------------
# 🔹 Alumnos del ciclo activo (vista + importación por BLOQUE)
# -------------------------------
ALLOWED_EXT_ALUMNOS = {"xlsx", "csv"}

def _allowed_file_alumnos(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT_ALUMNOS


@admin_bp.route('/alumnos', methods=['GET'])
@login_required
def admin_alumnos():
    """Vista principal de alumnos del ciclo activo"""
    if current_user.rol != 'admin':
        flash("🚫 Solo los administradores pueden acceder.", "danger")
        return redirect(url_for('nom.principal'))

    ciclo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo:
        flash("⚠️ No hay un ciclo activo. Activa un ciclo primero.", "warning")
        return redirect(url_for('admin_bp.gestionar_ciclos'))

    bloques = Bloque.query.filter_by(ciclo_id=ciclo.id).order_by(Bloque.id.asc()).all()
    alumnos = Alumno.query.filter_by(ciclo_id=ciclo.id).order_by(Alumno.grado, Alumno.grupo, Alumno.nombre).all()
    return render_template('admin_alumnos.html', ciclo=ciclo, bloques=bloques, alumnos=alumnos)


@admin_bp.route('/alumnos/importar_bloque', methods=['POST'])
@login_required
def importar_alumnos_por_bloque():
    """Importa alumnos al ciclo activo según bloque seleccionado"""
    if current_user.rol != 'admin':
        flash("🚫 Solo los administradores pueden importar alumnos.", "danger")
        return redirect(url_for('nom.principal'))

    ciclo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo:
        flash("⚠️ No hay un ciclo activo. Activa un ciclo primero.", "warning")
        return redirect(url_for('admin_bp.gestionar_ciclos'))

    bloque_id = request.form.get("bloque_id", type=int)
    if not bloque_id:
        flash("⚠️ Selecciona un bloque para importar.", "warning")
        return redirect(url_for('admin_bp.admin_alumnos'))

    bloque = Bloque.query.filter_by(id=bloque_id, ciclo_id=ciclo.id).first()
    if not bloque:
        flash("❌ El bloque seleccionado no existe en el ciclo activo.", "danger")
        return redirect(url_for('admin_bp.admin_alumnos'))

    file = request.files.get("file")
    if not file or file.filename == "":
        flash("⚠️ No se seleccionó archivo.", "warning")
        return redirect(url_for('admin_bp.admin_alumnos'))
    if not _allowed_file_alumnos(file.filename):
        flash("❌ Solo .xlsx o .csv", "danger")
        return redirect(url_for('admin_bp.admin_alumnos'))

    filename = secure_filename(file.filename)
    tmp_path = os.path.join(tempfile.gettempdir(), filename)
    file.save(tmp_path)

    try:
        df = pd.read_excel(tmp_path) if filename.lower().endswith(".xlsx") else pd.read_csv(tmp_path)
        df.columns = [c.strip().lower() for c in df.columns]

        requeridas = {"nombre", "grado", "grupo", "nivel"}
        if not requeridas.issubset(set(df.columns)):
            faltan = ", ".join(sorted(requeridas - set(df.columns)))
            flash(f"❌ Faltan columnas requeridas: {faltan}", "danger")
            return redirect(url_for('admin_bp.admin_alumnos'))

        importados, existentes = 0, 0
        for _, row in df.iterrows():
            nombre = str(row["nombre"]).strip()
            grado = str(row["grado"]).strip()
            grupo = str(row["grupo"]).strip()
            nivel = str(row["nivel"]).strip()
            if not (nombre and grado and grupo and nivel):
                continue

            ya = Alumno.query.filter_by(
                nombre=nombre, grado=grado, grupo=grupo, ciclo_id=ciclo.id
            ).first()
            if ya:
                existentes += 1
                continue

            nuevo = Alumno(
                nombre=nombre,
                grado=grado,
                grupo=grupo,
                nivel=nivel,
                ciclo_id=ciclo.id,
                bloque_id=bloque.id
            )
            db.session.add(nuevo)
            importados += 1

        db.session.commit()
        flash(f"✅ {importados} alumnos importados a «{bloque.nombre}». {existentes} ya existían.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al importar: {e}", "danger")

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return redirect(url_for('admin_bp.admin_alumnos'))


# -------------------------------
# 🔹 Descargar plantilla Excel (alumnos por bloque)
# -------------------------------
@admin_bp.route('/alumnos/plantilla')
@login_required
def plantilla_alumnos_bloque():
    """Genera y descarga una plantilla Excel con columnas básicas"""
    try:
        # Crear DataFrame vacío con columnas correctas
        import pandas as pd
        from io import BytesIO

        columnas = ["nombre", "grado", "grupo", "nivel"]
        df = pd.DataFrame(columns=columnas)

        # Escribir en memoria (sin guardar en disco)
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="AlumnosPorBloque")
        output.seek(0)

        # Enviar al navegador como archivo descargable
        return send_file(
            output,
            as_attachment=True,
            download_name="Plantilla_alumnos_por_bloque.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        flash(f"❌ Error al generar la plantilla: {e}", "danger")
        return redirect(url_for('admin_bp.admin_alumnos'))


# -------------------------------
# 🔹 Editar alumno
# -------------------------------
@admin_bp.route('/alumnos/editar/<int:id>', methods=['POST'])
@login_required
def editar_alumno(id):
    if current_user.rol != 'admin':
        return jsonify({"error": "No autorizado"}), 403

    alumno = Alumno.query.get_or_404(id)
    data = request.get_json()

    alumno.nombre = data.get("nombre", alumno.nombre).title()
    alumno.grado = data.get("grado", alumno.grado)
    alumno.grupo = data.get("grupo", alumno.grupo).upper()
    alumno.nivel = data.get("nivel", alumno.nivel).capitalize()

    db.session.commit()
    return jsonify({"message": f"Alumno {alumno.nombre} actualizado con éxito."}), 200


# -------------------------------
# 🔹 Eliminar alumno
# -------------------------------
@admin_bp.route('/alumnos/eliminar/<int:id>', methods=['DELETE'])
@login_required
def eliminar_alumno(id):
    if current_user.rol != 'admin':
        return jsonify({"error": "No autorizado"}), 403

    alumno = Alumno.query.get_or_404(id)
    db.session.delete(alumno)
    db.session.commit()
    return jsonify({"message": f"Alumno {alumno.nombre} eliminado."}), 200


# -------------------------------
# 🔹 Decorador para rutas solo de administrador
# -------------------------------
from functools import wraps
from flask import abort

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            flash("🚫 Solo los administradores pueden acceder a esta sección.", "danger")
            return redirect(url_for('nom.principal'))
        return f(*args, **kwargs)
    return decorated_function


# -------------------------------
# 🔹 VALORES POR CICLO ESCOLAR
# -------------------------------
@admin_bp.route('/valores', methods=['GET'])
@login_required
def listar_valores():
    # Usar tu modelo correcto
    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo_activo:
        flash("⚠️ No hay ciclo activo.", "warning")
        return redirect(url_for('admin_bp.gestionar_ciclos'))

    valores = Valor.query.filter_by(ciclo_id=ciclo_activo.id).all()
    # 👇 Aquí corregimos la ruta del template
    return render_template('valores.html', valores=valores, ciclo=ciclo_activo)



@admin_bp.route('/valores/nuevo', methods=['POST'])
@login_required
def crear_valor():
    nombre = request.form.get('nombre', '').strip().title()
    descripcion = request.form.get('descripcion', '').strip()
    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()

    if not ciclo_activo:
        flash("⚠️ No hay ciclo activo.", "danger")
        return redirect(url_for('admin_bp.listar_valores'))

    if Valor.query.filter_by(nombre=nombre, ciclo_id=ciclo_activo.id).first():
        flash("⚠️ Ya existe un valor con ese nombre en este ciclo.", "warning")
        return redirect(url_for('admin_bp.listar_valores'))

    nuevo = Valor(nombre=nombre, descripcion=descripcion, ciclo_id=ciclo_activo.id)
    db.session.add(nuevo)
    db.session.commit()
    flash("✅ Valor agregado exitosamente.", "success")
    return redirect(url_for('admin_bp.listar_valores'))


@admin_bp.route('/valores/<int:id>/toggle', methods=['POST'])
@login_required
@admin_required
def alternar_valor(id):
    """Activa o desactiva un valor existente."""
    valor = Valor.query.get_or_404(id)
    valor.activo = not valor.activo
    db.session.commit()
    flash(f"🔁 Valor {'activado' if valor.activo else 'desactivado'}.", "info")
    return redirect(url_for('admin_bp.listar_valores'))


@admin_bp.route('/valores/<int:id>/eliminar', methods=['POST'])
@login_required
@admin_required
def eliminar_valor(id):
    """Elimina un valor del ciclo actual."""
    valor = Valor.query.get_or_404(id)
    db.session.delete(valor)
    db.session.commit()
    flash("🗑️ Valor eliminado correctamente.", "success")
    return redirect(url_for('admin_bp.listar_valores'))

@admin_bp.route('/nominaciones', methods=['GET'])
@login_required
@admin_required
def gestionar_nominaciones():
    """Vista de administración para revisar todas las nominaciones del ciclo activo"""
    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo_activo:
        flash("⚠️ No hay ciclo escolar activo.", "warning")
        return redirect(url_for('admin_bp.gestionar_ciclos'))

    # Traer todas las nominaciones ordenadas por fecha
    nominaciones = (
        Nominacion.query
        .filter_by(ciclo_id=ciclo_activo.id)
        .order_by(Nominacion.fecha.desc())
        .all()
    )

    # Dividir por tipo
    nominaciones_alumnos = [n for n in nominaciones if n.tipo == "alumno"]
    nominaciones_personal = [n for n in nominaciones if n.tipo == "personal"]

    return render_template(
        'admin_nominaciones.html',
        ciclo=ciclo_activo,
        nominaciones_alumnos=nominaciones_alumnos,
        nominaciones_personal=nominaciones_personal
    )



# Maestro nomina a alumnos
@nom.route('/nominaciones/alumno', methods=['GET', 'POST'])
@login_required
def nominar_alumno():
    # 1️⃣ Validar rol del usuario
    if current_user.rol != 'profesor':
        flash("🚫 Solo los profesores pueden registrar nominaciones.", "danger")
        return redirect(url_for('nom.principal'))

    # 2️⃣ Validar que haya ciclo activo
    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo_activo:
        flash("⚠️ No hay ciclo activo disponible.", "warning")
        return redirect(url_for('nom.principal'))

    # 3️⃣ Obtener maestro actual
    maestro = Maestro.query.filter_by(correo=current_user.email, ciclo_id=ciclo_activo.id).first()
    if not maestro:
        flash("⚠️ No se encontró tu registro como maestro en el ciclo activo.", "warning")
        return redirect(url_for('nom.principal'))

    # 4️⃣ Procesar envío del formulario
    if request.method == 'POST':
        valor_id = request.form.get('valor_id')
        alumno_ids = request.form.getlist('alumnos')  # permite varios
        comentario = request.form.get('comentario', '').strip()

        if not valor_id or not alumno_ids:
            flash("⚠️ Selecciona al menos un alumno y un valor.", "warning")
            return redirect(url_for('nom.nominar_alumno'))

        for alumno_id in alumno_ids:
            # Evita duplicados: mismo maestro, alumno y valor en el mismo ciclo
            existente = Nominacion.query.filter_by(
                alumno_id=alumno_id,
                maestro_id=maestro.id,
                valor_id=valor_id,
                ciclo_id=ciclo_activo.id
            ).first()
            if existente:
                continue

            nueva_nom = Nominacion(
                alumno_id=alumno_id,
                maestro_id=maestro.id,
                valor_id=valor_id,
                ciclo_id=ciclo_activo.id,
                comentario=comentario
            )
            db.session.add(nueva_nom)

        db.session.commit()
        flash(f"✅ Nominación registrada correctamente ({len(alumno_ids)} alumnos).", "success")
        return redirect(url_for('nom.nominar_alumno'))

    # 5️⃣ Cargar datos del formulario
    alumnos = Alumno.query.filter_by(ciclo_id=ciclo_activo.id).order_by(Alumno.grado, Alumno.grupo, Alumno.nombre).all()
    valores = Valor.query.filter_by(ciclo_id=ciclo_activo.id, activo=True).all()

    # 6️⃣ Mostrar también las nominaciones previas de este maestro
    nominaciones = Nominacion.query.filter_by(ciclo_id=ciclo_activo.id, maestro_id=maestro.id).order_by(Nominacion.fecha.desc()).all()

    return render_template('nominacion_alumno.html', alumnos=alumnos, valores=valores, nominaciones=nominaciones, ciclo=ciclo_activo)

@nom.route('/nominaciones/maestro', methods=['GET', 'POST'])
@login_required
def nominar_maestro():
    maestro = Maestro.query.filter_by(correo=current_user.email).first()
    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()

    if request.method == 'POST':
        valor_id = request.form.get('valor_id')
        maestros_ids = request.form.getlist('maestros')
        comentario = request.form.get('comentario', '').strip()

        if not valor_id or not maestros_ids:
            flash("⚠️ Selecciona al menos un maestro y un valor.", "warning")
            return redirect(url_for('nom.nominar_maestro'))

        for m_id in maestros_ids:
            nueva_nom = Nominacion(
                alumno_id=None,
                maestro_id=maestro.id,  # nominador
                valor_id=valor_id,
                ciclo_id=ciclo_activo.id,
                comentario=f"Nominación a maestro ID {m_id}: {comentario}"
            )
            db.session.add(nueva_nom)

        db.session.commit()
        flash(f"✅ Nominación registrada correctamente ({len(maestros_ids)} maestros).", "success")
        return redirect(url_for('nom.nominar_maestro'))

    maestros = Maestro.query.filter(
        Maestro.ciclo_id == ciclo_activo.id,
        Maestro.id != maestro.id
    ).all()
    valores = Valor.query.filter_by(ciclo_id=ciclo_activo.id, activo=True).all()
    return render_template('nominacion_personal.html', maestros=maestros, valores=valores, ciclo=ciclo_activo)


# Maestro nomina a otro maestro
@nom.route('/nominaciones/personal', methods=['GET', 'POST'])
@login_required
def nominar_personal():
    if current_user.rol != 'profesor':
        flash("🚫 Solo los profesores pueden registrar nominaciones.", "danger")
        return redirect(url_for('nom.principal'))

    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo_activo:
        flash("⚠️ No hay ciclo activo disponible.", "warning")
        return redirect(url_for('nom.principal'))

    maestro = Maestro.query.filter_by(correo=current_user.email, ciclo_id=ciclo_activo.id).first()
    if not maestro:
        flash("⚠️ No se encontró tu registro como maestro en el ciclo activo.", "warning")
        return redirect(url_for('nom.principal'))

    if request.method == 'POST':
        valor_id = request.form.get('valor_id')
        nominados = request.form.getlist('maestros')
        comentario = request.form.get('comentario', '').strip()

        if not valor_id or not nominados:
            flash("⚠️ Selecciona al menos un maestro y un valor.", "warning")
            return redirect(url_for('nom.nominar_personal'))

        for nominado_id in nominados:
            existente = Nominacion.query.filter_by(
                maestro_nominado_id=nominado_id,
                maestro_id=maestro.id,
                valor_id=valor_id,
                ciclo_id=ciclo_activo.id
            ).first()
            if existente:
                continue

            nueva_nom = Nominacion(
                maestro_nominado_id=nominado_id,
                maestro_id=maestro.id,
                valor_id=valor_id,
                ciclo_id=ciclo_activo.id,
                comentario=comentario
            )
            db.session.add(nueva_nom)

        db.session.commit()
        flash(f"✅ Nominación registrada correctamente ({len(nominados)} maestros).", "success")
        return redirect(url_for('nom.nominar_personal'))

    maestros = Maestro.query.filter(Maestro.id != maestro.id, Maestro.ciclo_id == ciclo_activo.id).all()
    valores = Valor.query.filter_by(ciclo_id=ciclo_activo.id, activo=True).all()
    nominaciones = Nominacion.query.filter_by(ciclo_id=ciclo_activo.id, maestro_id=maestro.id).order_by(Nominacion.fecha.desc()).all()

    return render_template('nominacion_personal.html', maestros=maestros, valores=valores, nominaciones=nominaciones, ciclo=ciclo_activo)


@nom.route('/admin/nominaciones/export', methods=['GET'])
@login_required
def exportar_nominaciones_excel():
    """
    Exporta nominaciones del ciclo activo a Excel.
    ?tipo=alumno|personal  (opcional; si no se envía, exporta todo)
    """
    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo_activo:
        return jsonify({"error": "No hay ciclo escolar activo."}), 400

    q = Nominacion.query.filter_by(ciclo_id=ciclo_activo.id)
    tipo = request.args.get('tipo')
    if tipo in ('alumno', 'personal'):
        q = q.filter(Nominacion.tipo == tipo)

    q = q.order_by(Nominacion.fecha.desc()).all()

    filas = []
    for n in q:
        filas.append({
            "Fecha": n.fecha.strftime("%Y-%m-%d %H:%M") if n.fecha else "",
            "Tipo": n.tipo or "",
            "Valor": n.valor.nombre if getattr(n, 'valor', None) else "",
            "Maestro (autor)": n.maestro.nombre if getattr(n, 'maestro', None) else "",
            "Alumno nominado": n.alumno.nombre if getattr(n, 'alumno', None) else "",
            "Personal nominado": n.maestro_nominado.nombre if getattr(n, 'maestro_nominado', None) else "",
            "Comentario": (n.comentario or n.razon) if hasattr(n, 'comentario') or hasattr(n, 'razon') else "",
        })

    df = pd.DataFrame(filas)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Nominaciones')
        ws = writer.sheets['Nominaciones']
        for i, col in enumerate(df.columns):
            width = 12
            if not df.empty:
                width = min(60, max(12, df[col].astype(str).map(len).max() + 2))
            ws.set_column(i, i, width)
    output.seek(0)

    nombre = f"nominaciones_{tipo or 'todas'}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=nombre,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
@nom.route('/admin/nominaciones/data', methods=['GET'])
@login_required
def obtener_nominaciones_data():
    """Devuelve nominaciones del ciclo activo filtradas por parámetros opcionales."""
    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo_activo:
        return jsonify({"items": [], "error": "No hay ciclo activo."})

    tipo = request.args.get('tipo')  # alumno | personal
    valor_id = request.args.get('valor_id', type=int)
    maestro_id = request.args.get('maestro_id', type=int)
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')

    q = Nominacion.query.filter(Nominacion.ciclo_id == ciclo_activo.id)

    if tipo in ('alumno', 'personal'):
        q = q.filter(Nominacion.tipo == tipo)
    if valor_id:
        q = q.filter(Nominacion.valor_id == valor_id)
    if maestro_id:
        q = q.filter(Nominacion.maestro_id == maestro_id)

    if fecha_desde:
        try:
            fd = datetime.strptime(fecha_desde, "%Y-%m-%d")
            q = q.filter(Nominacion.fecha >= fd)
        except ValueError:
            pass

    if fecha_hasta:
        try:
            fh = datetime.strptime(fecha_hasta, "%Y-%m-%d")
            fh = fh.replace(hour=23, minute=59, second=59)
            q = q.filter(Nominacion.fecha <= fh)
        except ValueError:
            pass

    nominaciones = q.order_by(Nominacion.fecha.desc()).all()

    datos = []
    for n in nominaciones:
        datos.append({
            "id": n.id,
            "fecha": n.fecha.strftime("%d/%m/%Y"),
            "tipo": n.tipo,
            "valor": n.valor.nombre if n.valor else "",
            "maestro": n.maestro.nombre if n.maestro else "",
            "alumno": n.alumno.nombre if getattr(n, 'alumno', None) else "",
            "maestro_nominado": n.maestro_nominado.nombre if getattr(n, 'maestro_nominado', None) else "",
            "comentario": n.comentario or "",
        })

    return jsonify({"items": datos, "total": len(datos)})

@nom.route('/admin/catalogo/valores')
@login_required
def catalogo_valores():
    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
    valores = Valor.query.filter_by(ciclo_id=ciclo_activo.id).order_by(Valor.nombre.asc()).all()
    return jsonify([{"id": v.id, "nombre": v.nombre} for v in valores])

@nom.route('/admin/catalogo/maestros')
@login_required
def catalogo_maestros():
    maestros = Maestro.query.order_by(Maestro.nombre.asc()).all()
    return jsonify([{"id": m.id, "nombre": m.nombre} for m in maestros])


@nom.route('/admin/usuarios/lista/alumnos')
@login_required
def lista_alumnos():
    """Devuelve JSON con alumnos del ciclo activo."""
    if current_user.rol != 'admin':
        return jsonify({"error": "No autorizado"}), 403

    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo_activo:
        return jsonify({"error": "No hay ciclo activo."}), 400

    alumnos = Alumno.query.filter_by(ciclo_id=ciclo_activo.id).order_by(
        Alumno.grado, Alumno.grupo, Alumno.nombre
    ).all()

    data = [
        {
            "id": a.id,
            "nombre": a.nombre,
            "grado": a.grado,
            "grupo": a.grupo,
            "nivel": a.nivel
        }
        for a in alumnos
    ]
    return jsonify(data)


# -------------------------------
# 🔹 Editar alumno (vista y actualización)
# -------------------------------
@admin_bp.route('/alumnos/editar/<int:id>', methods=['GET'])
@login_required
def editar_alumno_vista(id):
    if current_user.rol != 'admin':
        flash("🚫 Solo los administradores pueden acceder.", "danger")
        return redirect(url_for('nom.principal'))

    alumno = Alumno.query.get_or_404(id)
    return render_template('editar_alumno.html', alumno=alumno)


@admin_bp.route('/alumnos/editar/<int:id>', methods=['POST'])
@login_required
def actualizar_alumno(id):
    if current_user.rol != 'admin':
        flash("🚫 Solo los administradores pueden editar alumnos.", "danger")
        return redirect(url_for('nom.principal'))

    alumno = Alumno.query.get_or_404(id)
    alumno.nombre = request.form.get('nombre', alumno.nombre).strip().title()
    alumno.grado = request.form.get('grado', alumno.grado).strip()
    alumno.grupo = request.form.get('grupo', alumno.grupo).strip().upper()
    alumno.nivel = request.form.get('nivel', alumno.nivel).strip().capitalize()

    db.session.commit()
    flash(f"✅ Alumno {alumno.nombre} actualizado correctamente.", "success")
    return redirect(url_for('nom.panel_usuarios'))

# -------------------------------
# 🔹 Editar usuario (admin o profesor)
# -------------------------------
@nom.route('/admin/usuarios/editar/<int:id>', methods=['GET'])
@login_required
def editar_usuario_vista(id):
    if current_user.rol != 'admin':
        flash("🚫 Solo los administradores pueden acceder a esta sección.", "danger")
        return redirect(url_for('nom.principal'))

    usuario = Usuario.query.get_or_404(id)
    return render_template('editar_usuario.html', usuario=usuario)


@nom.route('/admin/usuarios/editar/<int:id>', methods=['POST'])
@login_required
def actualizar_usuario(id):
    if current_user.rol != 'admin':
        flash("🚫 No autorizado.", "danger")
        return redirect(url_for('nom.principal'))

    usuario = Usuario.query.get_or_404(id)
    usuario.nombre = request.form.get('nombre', usuario.nombre).strip().title()
    usuario.email = request.form.get('email', usuario.email).strip().lower()
    usuario.rol = request.form.get('rol', usuario.rol)

    db.session.commit()
    flash(f"✅ Usuario {usuario.nombre} actualizado correctamente.", "success")
    return redirect(url_for('nom.panel_usuarios'))


# -------------------------------
# 🔹 Editar profesor (vista + actualización)
# -------------------------------
# ============================================================
# ✏️ Editar PROFESOR (GET muestra formulario / POST guarda)
# ============================================================

@admin_bp.route('/maestros/lista')
@login_required
def lista_maestros_json():
    # Solo admin
    if current_user.rol != 'admin':
        return jsonify({"error": "No autorizado"}), 403

    ciclo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo:
        return jsonify([])

    maes = Maestro.query.filter_by(ciclo_id=ciclo.id).order_by(Maestro.nombre.asc()).all()
    data = [{"id": m.id, "nombre": m.nombre, "email": m.correo} for m in maes]
    return jsonify(data)

@admin_bp.route('/maestros/editar/<int:id>', methods=['GET'])
@login_required
def editar_maestro_vista(id):
    if current_user.rol != 'admin':
        flash("🚫 Solo los administradores.", "danger")
        return redirect(url_for('nom.panel_usuarios'))

    maestro = Maestro.query.get_or_404(id)
    return render_template('editar_profesor.html', maestro=maestro)

@admin_bp.route('/maestros/editar/<int:id>', methods=['POST'])
@login_required
def actualizar_maestro(id):
    if current_user.rol != 'admin':
        flash("🚫 Solo los administradores.", "danger")
        return redirect(url_for('nom.panel_usuarios'))

    maestro = Maestro.query.get_or_404(id)
    maestro.nombre = request.form.get('nombre', maestro.nombre).strip()
    maestro.correo = request.form.get('correo', maestro.correo).strip().lower()
    db.session.commit()
    flash("✅ Maestro actualizado correctamente.", "success")
    return redirect(url_for('nom.panel_usuarios'))

@admin_bp.route('/maestros/eliminar/<int:id>', methods=['DELETE'])
@login_required
def eliminar_maestro(id):
    if current_user.rol != 'admin':
        return jsonify({"message": "No autorizado"}), 403

    maestro = Maestro.query.get_or_404(id)
    db.session.delete(maestro)
    db.session.commit()

    return jsonify({"message": "✅ Maestro eliminado correctamente"})

