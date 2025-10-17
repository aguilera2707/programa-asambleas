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
from datetime import datetime
from utils import admin_required

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
    if current_user.rol == 'admin':
        return render_template('panel_admin.html')
    elif current_user.rol == 'profesor':
        return redirect(url_for('nom.panel_profesor'))
    else:
        return render_template('principal.html')  # si en el futuro hay alumnos



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


from werkzeug.security import generate_password_hash  # asegúrate de tenerlo arriba

@nom.route('/crear_usuario', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_usuario():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        password = request.form['password']
        rol = request.form.get('rol', 'admin')  # si no se envía, por defecto admin

        # Verificar si ya existe
        existente = Usuario.query.filter_by(email=correo).first()
        if existente:
            flash("⚠️ Ya existe un usuario con ese correo.", "warning")
            return redirect(url_for('nom.crear_usuario'))

        # ✅ Crear usuario correctamente
        nuevo = Usuario(nombre=nombre, email=correo, rol=rol)
        nuevo.set_password(password)
        db.session.add(nuevo)
        db.session.commit()

        flash(f"✅ Usuario '{nombre}' creado correctamente como {rol}.", "success")
        # 🔹 En lugar de redirigir a otra página, recargamos la misma
        return redirect(url_for('nom.crear_usuario'))

    # Para GET
    return render_template('crear_usuario.html', rol_predefinido='admin')

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
# -------------------------------
# 🔹 Importar maestros al ciclo activo (CSV o Excel)
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
        # ✅ Detección automática del tipo de archivo
        ext = filename.split('.')[-1].lower()

        if ext in ['xlsx', 'xls']:
            # Forzamos que lea contraseñas como texto
            df = pd.read_excel(filepath, dtype=str)
        elif ext in ['csv']:
            df = pd.read_csv(filepath, dtype=str, encoding='utf-8')
        else:
            flash("❌ Formato no soportado. Usa un archivo .xlsx o .csv", "danger")
            return redirect(url_for('admin_bp.maestros_ciclo'))

        # ✅ Normalizar columnas
        df.columns = df.columns.str.strip().str.lower()

        # Aceptar ambas versiones de 'contraseña' o 'contrasena'
        if 'contrasena' in df.columns and 'contraseña' not in df.columns:
            df.rename(columns={'contrasena': 'contraseña'}, inplace=True)

        columnas_requeridas = {'nombre', 'email', 'contraseña'}
        if not columnas_requeridas.issubset(df.columns):
            flash("❌ La plantilla debe contener las columnas: nombre, email y contraseña.", "danger")
            return redirect(url_for('admin_bp.maestros_ciclo'))

        # ✅ Obtener ciclo activo
        ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
        if not ciclo_activo:
            flash("⚠️ No hay ningún ciclo activo. Activa un ciclo primero.", "warning")
            return redirect(url_for('admin_bp.gestionar_ciclos'))

        importados, existentes = 0, 0

        # ✅ Iterar y limpiar datos
        for _, row in df.iterrows():
            nombre = str(row.get('nombre', '')).strip()
            correo = str(row.get('email', '')).strip().lower()
            raw_pass = row.get('contraseña', '')

            # 🔍 Convertir contraseñas numéricas a texto limpio
            if pd.isna(raw_pass):
                password = ''
            else:
                password = str(raw_pass).strip()
                # Si viene en formato "123456.0" → "123456"
                if password.endswith('.0'):
                    password = password[:-2]
                # Si viene como número grande sin comillas, asegúrate que sea string
                if password.isdigit():
                    password = password

            if not nombre or not correo:
                continue

            # Crear o actualizar usuario
            usuario = Usuario.query.filter_by(email=correo).first()
            if not usuario:
                usuario = Usuario(nombre=nombre, email=correo, rol='profesor')
                usuario.set_password(password if password else '123456')
                db.session.add(usuario)
            else:
                if password:
                    usuario.set_password(password)

            # Crear maestro solo si no existe ya
            existe_maestro = Maestro.query.filter_by(correo=correo, ciclo_id=ciclo_activo.id).first()
            if existe_maestro:
                existentes += 1
                continue

            maestro = Maestro(nombre=nombre, correo=correo, ciclo_id=ciclo_activo.id)
            db.session.add(maestro)
            importados += 1

        db.session.commit()
        flash(f"✅ {importados} maestros importados correctamente al ciclo {ciclo_activo.nombre}. {existentes} ya existían.", "success")

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

    # 🔹 Ordena los bloques numéricamente si se llaman "Bloque 1", "Bloque 2", etc.
    bloques = []
    if ciclo:
        bloques = (
            Bloque.query
            .filter_by(ciclo_id=ciclo.id)
            .order_by(
                db.cast(db.func.substr(Bloque.nombre, 8), db.Integer).asc()
            )
            .all()
        )

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
# ------------------------------------------------------------
# 🧩 Gestión completa de Bloques Académicos del Ciclo Activo
# ------------------------------------------------------------
@admin_bp.route('/bloques', methods=['GET', 'POST'])
@login_required
def bloques_ciclo():
    # ✅ Validar acceso solo para administradores
    if current_user.rol != 'admin':
        flash("🚫 Solo los administradores pueden acceder.", "danger")
        return redirect(url_for('nom.principal'))

    # ✅ Obtener ciclo activo
    ciclo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo:
        flash("⚠️ No hay un ciclo activo. Activa un ciclo antes de administrar bloques.", "warning")
        return redirect(url_for('admin_bp.gestionar_ciclos'))

    # ✅ Crear nuevo bloque
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        if not nombre:
            flash("⚠️ El nombre del bloque no puede estar vacío.", "warning")
            return redirect(url_for('admin_bp.bloques_ciclo'))

        existente = Bloque.query.filter_by(nombre=nombre, ciclo_id=ciclo.id).first()
        if existente:
            flash(f"🚫 El bloque '{nombre}' ya existe en este ciclo.", "danger")
        else:
            nuevo = Bloque(nombre=nombre, ciclo_id=ciclo.id)
            db.session.add(nuevo)
            db.session.commit()
            flash(f"✅ Bloque '{nombre}' creado exitosamente.", "success")

        return redirect(url_for('admin_bp.bloques_ciclo'))

    # ✅ Obtener lista de bloques del ciclo
    bloques = (
        db.session.query(Bloque)
        .filter_by(ciclo_id=ciclo.id)
        .order_by(Bloque.orden.asc())
        .all()
    )

    # ✅ Contar alumnos por bloque
    conteos = {b.id: Alumno.query.filter_by(bloque_id=b.id).count() for b in bloques}

    # ✅ Armar vista con grados y grupos por bloque
    data = []
    for bloque in bloques:
        alumnos = Alumno.query.filter_by(bloque_id=bloque.id).all()
        if alumnos:
            grados_dict = {}
            for a in alumnos:
                grados_dict.setdefault(a.grado, set()).add(a.grupo)
            grados = [{'grado': g, 'grupos': sorted(list(grs))} for g, grs in grados_dict.items()]
        else:
            grados = []
        data.append({'bloque': bloque, 'grados': grados})

    # ✅ Renderizar plantilla moderna unificada
    return render_template(
        'admin_bloques.html',
        ciclo=ciclo,
        bloques=bloques,
        conteos=conteos,
        data=data
    )


# -------------------------------
# 🔹 Alumnos del ciclo activo (vista + importación por BLOQUE)
# -------------------------------
ALLOWED_EXT_ALUMNOS = {"xlsx", "csv"}

def _allowed_file_alumnos(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT_ALUMNOS


@admin_bp.route('/administradores', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_administradores():
    return render_template('admin_administradores.html')

# -------------------------------
# 🟢 Importar alumnos al bloque seleccionado
# -------------------------------
@admin_bp.route('/alumnos/importar_bloque', methods=['POST'])
@login_required
def importar_alumnos_por_bloque():
    """Importa alumnos al ciclo activo según bloque seleccionado"""
    if current_user.rol != 'admin':
        flash("🚫 Solo los administradores pueden importar alumnos.", "danger")
        return redirect(url_for('nom.principal'))

    # ✅ Verificar ciclo activo
    ciclo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo:
        flash("⚠️ No hay un ciclo activo. Activa un ciclo primero.", "warning")
        return redirect(url_for('admin_bp.gestionar_ciclos'))

    # ✅ Verificar bloque seleccionado
    bloque_id = request.form.get("bloque_id", type=int)
    if not bloque_id:
        flash("⚠️ Selecciona un bloque para importar.", "warning")
        return redirect(url_for('admin_bp.alumnos_ciclo'))

    bloque = Bloque.query.filter_by(id=bloque_id, ciclo_id=ciclo.id).first()
    if not bloque:
        flash("❌ El bloque seleccionado no existe en el ciclo activo.", "danger")
        return redirect(url_for('admin_bp.alumnos_ciclo'))

    # ✅ Verificar archivo
    file = request.files.get("file")
    if not file or file.filename == "":
        flash("⚠️ No se seleccionó ningún archivo.", "warning")
        return redirect(url_for('admin_bp.alumnos_ciclo'))

    if not _allowed_file_alumnos(file.filename):
        flash("❌ Solo se permiten archivos .xlsx o .csv", "danger")
        return redirect(url_for('admin_bp.alumnos_ciclo'))

    # ✅ Guardar temporalmente el archivo
    filename = secure_filename(file.filename)
    tmp_path = os.path.join(tempfile.gettempdir(), filename)
    file.save(tmp_path)

    try:
        # Leer archivo
        df = pd.read_excel(tmp_path) if filename.lower().endswith(".xlsx") else pd.read_csv(tmp_path)
        df.columns = [c.strip().lower() for c in df.columns]

        # ✅ Validar columnas requeridas
        requeridas = {"nombre", "grado", "grupo", "nivel"}
        if not requeridas.issubset(set(df.columns)):
            faltan = ", ".join(sorted(requeridas - set(df.columns)))
            flash(f"❌ Faltan columnas requeridas: {faltan}", "danger")
            return redirect(url_for('admin_bp.alumnos_ciclo'))

        importados, existentes = 0, 0

        # ✅ Iterar e importar alumnos
        for _, row in df.iterrows():
            nombre = str(row.get("nombre", "")).strip()
            grado = str(row.get("grado", "")).strip()
            grupo = str(row.get("grupo", "")).strip()
            nivel = str(row.get("nivel", "")).strip()

            if not (nombre and grado and grupo and nivel):
                continue

            existente = Alumno.query.filter_by(
                nombre=nombre, grado=grado, grupo=grupo, ciclo_id=ciclo.id
            ).first()

            if existente:
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
        flash(f"❌ Error al importar: {str(e)}", "danger")

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return redirect(url_for('admin_bp.alumnos_ciclo'))


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



# Maestro nomina a alumnos (sin dependencia de bloque)
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

    # 4️⃣ Obtener evento activo del BLOQUE del maestro
    evento_abierto = (
        EventoAsamblea.query
        .filter_by(ciclo_id=ciclo_activo.id, activo=True)
        .order_by(EventoAsamblea.fecha_evento.asc())
        .first()
    )

    # 🔍 Validar que exista un evento activo y que esté en tiempo
    if not evento_abierto:
        flash("⚠️ No hay un evento activo configurado para tu bloque.", "warning")
        return redirect(url_for('nom.principal'))

    # 👉 Si el evento está marcado como activo pero su fecha de cierre ya pasó, se debe bloquear también
    if not evento_abierto.esta_abierto:
        # Desactivamos el evento automáticamente (opcional, pero útil)
        evento_abierto.activo = False
        db.session.commit()

        flash(
            f"🚫 El evento {evento_abierto.nombre_mes} ya cerró las nominaciones "
            f"(cierre: {evento_abierto.fecha_cierre_nominaciones.strftime('%d/%m/%Y %H:%M')}).",
            "danger"
        )
        return redirect(url_for('nom.principal'))


    # 5️⃣ Procesar envío del formulario
    if request.method == 'POST':
        valor_id = request.form.get('valor_id')
        alumno_ids = request.form.getlist('alumnos')
        comentario = request.form.get('comentario', '').strip()

        if not valor_id or not alumno_ids:
            flash("⚠️ Selecciona al menos un alumno y un valor.", "warning")
            return redirect(url_for('nom.nominar_alumno'))

        nuevas = 0
        for alumno_id in alumno_ids:
            # Evitar duplicados: mismo maestro, alumno y valor en el mismo ciclo
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
                comentario=comentario,
                evento_id=evento_abierto.id,
                tipo='alumno'
            )
            db.session.add(nueva_nom)
            nuevas += 1

        db.session.commit()
        flash(f"✅ Se registraron {nuevas} nominaciones al evento {evento_abierto.nombre_mes}.", "success")
        return redirect(url_for('nom.nominar_alumno'))

    # 6️⃣ Cargar datos para el formulario
    alumnos = (
        Alumno.query
        .filter_by(ciclo_id=ciclo_activo.id)
        .order_by(Alumno.grado, Alumno.grupo, Alumno.nombre)
        .all()
    )
    valores = Valor.query.filter_by(ciclo_id=ciclo_activo.id, activo=True).all()

    # 7️⃣ Mostrar también las nominaciones previas del maestro
    nominaciones = (
        Nominacion.query
        .filter_by(ciclo_id=ciclo_activo.id, maestro_id=maestro.id)
        .order_by(Nominacion.fecha.desc())
        .all()
    )

    return render_template(
        'nominacion_alumno.html',
        alumnos=alumnos,
        valores=valores,
        nominaciones=nominaciones,
        ciclo=ciclo_activo,
        evento=evento_abierto
    )

# Maestro nomina a otro maestro (sin bloque, solo requiere evento activo)
# Maestro nomina a otro maestro (sin bloque, solo requiere evento activo)
@nom.route('/nominaciones/personal', methods=['GET', 'POST'])
@login_required
def nominar_personal():
    # 1️⃣ Validar rol del usuario
    if current_user.rol != 'profesor':
        flash("🚫 Solo los profesores pueden registrar nominaciones.", "danger")
        return redirect(url_for('nom.principal'))

    # 2️⃣ Validar ciclo activo
    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo_activo:
        flash("⚠️ No hay ciclo activo disponible.", "warning")
        return redirect(url_for('nom.principal'))

    # 3️⃣ Obtener maestro actual
    maestro = Maestro.query.filter_by(correo=current_user.email, ciclo_id=ciclo_activo.id, activo=True).first()
    if not maestro:
        flash("⚠️ No se encontró tu registro como maestro activo en el ciclo actual.", "warning")
        return redirect(url_for('nom.principal'))

    # 4️⃣ Obtener evento activo del ciclo (sin bloque)
    evento_abierto = (
        EventoAsamblea.query
        .filter_by(ciclo_id=ciclo_activo.id, activo=True)
        .order_by(EventoAsamblea.fecha_evento.asc())
        .first()
    )

    if not evento_abierto or not evento_abierto.esta_abierto:
        flash("🚫 No hay un evento de asamblea abierto para nominaciones en este momento.", "warning")
        return redirect(url_for('nom.principal'))

    # 5️⃣ Procesar nominaciones
    if request.method == 'POST':
        valor_id = request.form.get('valor_id')
        nominados = request.form.getlist('maestros')
        comentario = request.form.get('comentario', '').strip()

        if not valor_id or not nominados:
            flash("⚠️ Selecciona al menos un maestro y un valor.", "warning")
            return redirect(url_for('nom.nominar_personal'))

        nuevas = 0
        for nominado_id in nominados:
            # Evitar duplicados en el mismo ciclo y valor
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
                comentario=comentario,
                evento_id=evento_abierto.id,
                tipo='personal'
            )
            db.session.add(nueva_nom)
            nuevas += 1

        db.session.commit()
        flash(f"✅ Se registraron {nuevas} nominaciones de personal al evento {evento_abierto.nombre_mes}.", "success")
        return redirect(url_for('nom.nominar_personal'))

    # 6️⃣ Datos para el formulario
    maestros = Maestro.query.filter(
        Maestro.ciclo_id == ciclo_activo.id,
        Maestro.id != maestro.id,
        Maestro.activo == True
    ).order_by(Maestro.nombre.asc()).all()

    valores = Valor.query.filter_by(ciclo_id=ciclo_activo.id, activo=True).all()
    nominaciones = Nominacion.query.filter_by(
        ciclo_id=ciclo_activo.id,
        maestro_id=maestro.id
    ).order_by(Nominacion.fecha.desc()).all()

    return render_template(
        'nominacion_personal.html',
        maestros=maestros,
        valores=valores,
        nominaciones=nominaciones,
        ciclo=ciclo_activo,
        evento=evento_abierto
    )



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

@admin_bp.route('/maestros/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_maestro(id):
    """Desactiva o reactiva un maestro sin eliminarlo."""
    if current_user.rol != 'admin':
        flash("🚫 Solo los administradores pueden realizar esta acción.", "danger")
        return redirect(url_for('nom.principal'))

    maestro = Maestro.query.get_or_404(id)

    # Alternar estado
    maestro.activo = not maestro.activo
    db.session.commit()

    estado = "activado" if maestro.activo else "desactivado"
    flash(f"✅ El maestro '{maestro.nombre}' ha sido {estado}.", "success")

    return redirect(url_for('admin_bp.maestros_ciclo'))

# --- DASHBOARD JSON ---
# -------------------------------
# 🔹 Dashboard del Administrador
# -------------------------------
@admin_bp.route('/dashboard')
@login_required
def admin_dashboard():
    if current_user.rol != 'admin':
        flash("🚫 Solo los administradores pueden acceder al dashboard.", "danger")
        return redirect(url_for('nom.principal'))
    return render_template('admin_dashboard.html')

# -------------------------------
# 🔹 Endpoints JSON para gráficas
# -------------------------------
@admin_bp.route('/dashboard/data/resumen')
@login_required
def dashboard_data_resumen():
    if current_user.rol != 'admin':
        return jsonify({"error": "Solo administradores"}), 403

    ciclo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo:
        return jsonify({"error": "No hay ciclo activo"}), 400

    total_maestros = Maestro.query.filter_by(ciclo_id=ciclo.id).count()
    total_alumnos = Alumno.query.filter_by(ciclo_id=ciclo.id).count()
    total_nom = Nominacion.query.filter_by(ciclo_id=ciclo.id).count()

    por_tipo = (
        db.session.query(Nominacion.tipo, db.func.count(Nominacion.id))
        .filter(Nominacion.ciclo_id == ciclo.id)
        .group_by(Nominacion.tipo)
        .all()
    )
    por_tipo_dict = {t: c for t, c in por_tipo}

    por_valor = (
        db.session.query(Valor.nombre, db.func.count(Nominacion.id))
        .join(Nominacion, Nominacion.valor_id == Valor.id)
        .filter(Nominacion.ciclo_id == ciclo.id)
        .group_by(Valor.nombre)
        .order_by(db.func.count(Nominacion.id).desc())
        .limit(10)
        .all()
    )

    por_dia = (
        db.session.query(db.func.date(Nominacion.fecha), db.func.count(Nominacion.id))
        .filter(Nominacion.ciclo_id == ciclo.id)
        .group_by(db.func.date(Nominacion.fecha))
        .order_by(db.func.date(Nominacion.fecha))
        .all()
    )

    return jsonify({
        "totales": {
            "maestros": total_maestros,
            "alumnos": total_alumnos,
            "nominaciones": total_nom
        },
        "por_tipo": por_tipo_dict,
        "por_valor": [{"valor": v, "n": n} for v, n in por_valor],
        "por_dia": [{"fecha": str(f), "n": n} for f, n in por_dia],
    })


# ===============================
# 🗓️ CALENDARIO DE EVENTOS
# ===============================
from models import EventoAsamblea, PlantillaInvitacion, Bloque, CicloEscolar

@admin_bp.route('/calendario', methods=['GET', 'POST'])
@login_required
@admin_required
def calendario_eventos():
    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo_activo:
        flash("⚠️ No hay un ciclo escolar activo.", "warning")
        return redirect(url_for('admin_bp.gestionar_ciclos'))

    bloques = (
    Bloque.query
    .filter_by(ciclo_id=ciclo_activo.id)
    .order_by(cast(func.substr(Bloque.nombre, 8), Integer).asc())
    .all()
    )
    plantillas = PlantillaInvitacion.query.filter_by(ciclo_id=ciclo_activo.id, activa=True).all()

    if request.method == 'POST':
        bloque_id = request.form.get('bloque_id')
        nombre_mes = request.form.get('nombre_mes')
        mes_ordinal = request.form.get('mes_ordinal', type=int)
        fecha_evento = request.form.get('fecha_evento')
        fecha_cierre = request.form.get('fecha_cierre_nominaciones')
        plantilla_id = request.form.get('plantilla_id') or None

        if not all([bloque_id, nombre_mes, mes_ordinal, fecha_evento, fecha_cierre]):
            flash("⚠️ Todos los campos son obligatorios.", "warning")
            return redirect(url_for('admin_bp.calendario_eventos'))

        evento = EventoAsamblea(
            ciclo_id=ciclo_activo.id,
            bloque_id=bloque_id,
            nombre_mes=nombre_mes.strip().capitalize(),
            mes_ordinal=mes_ordinal,
            fecha_evento=fecha_evento,
            fecha_cierre_nominaciones=fecha_cierre,
            plantilla_id=plantilla_id
        )
        db.session.add(evento)
        db.session.commit()
        flash("✅ Evento agregado exitosamente.", "success")
        return redirect(url_for('admin_bp.calendario_eventos'))

    # Mostrar todos los eventos existentes del ciclo actual
    eventos = (
        EventoAsamblea.query
        .filter_by(ciclo_id=ciclo_activo.id)
        .order_by(EventoAsamblea.mes_ordinal.asc(), EventoAsamblea.bloque_id.asc())
        .all()
    )
    return render_template(
    'admin_calendario.html',
    ciclo=ciclo_activo,
    bloques=bloques,
    plantillas=plantillas,
    eventos=eventos,
    datetime=datetime
)
# ===============================
# 🗑️ ELIMINAR EVENTO DE ASAMBLEA (AJAX)
# ===============================
@admin_bp.route('/calendario/eliminar/<int:evento_id>', methods=['DELETE'])
@login_required
@admin_required
def eliminar_evento(evento_id):
    evento = EventoAsamblea.query.get(evento_id)
    if not evento:
        return jsonify({'success': False, 'error': 'Evento no encontrado'}), 404

    db.session.delete(evento)
    db.session.commit()
    return jsonify({'success': True})
# ===============================
# 🔄 ACTIVAR / DESACTIVAR EVENTO
# ===============================
@admin_bp.route('/calendario/toggle/<int:evento_id>', methods=['POST'])
@login_required
@admin_required
def toggle_evento(evento_id):
    evento = EventoAsamblea.query.get(evento_id)
    if not evento:
        return jsonify({'success': False, 'error': 'Evento no encontrado'}), 404

    evento.activo = not evento.activo
    db.session.commit()
    return jsonify({'success': True, 'activo': evento.activo})

# ===============================
# 📊 MATRIZ MENSUAL (Datos JSON)
# ===============================
from models import Alumno, Nominacion, EventoAsamblea, Maestro, Valor, Bloque, CicloEscolar

@admin_bp.route('/matriz_data', methods=['GET'])
@login_required
@admin_required
def matriz_data():
    """Devuelve los datos estructurados de la matriz mensual."""
    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo_activo:
        return jsonify({"error": "No hay ciclo activo."}), 400

    bloque_id = request.args.get('bloque_id', type=int)
    grado = request.args.get('grado')
    grupo = request.args.get('grupo')

    # 1️⃣ Obtener eventos del ciclo ordenados por mes
    eventos = EventoAsamblea.query.filter_by(ciclo_id=ciclo_activo.id).order_by(EventoAsamblea.mes_ordinal.asc()).all()
    meses_data = [
        {
            "id": e.id,
            "nombre": e.nombre_mes,
            "mes_ordinal": e.mes_ordinal,
            "cierre": e.fecha_cierre_nominaciones.strftime("%Y-%m-%d %H:%M")
        }
        for e in eventos
    ]

    # 2️⃣ Filtrar alumnos según bloque / grado / grupo
    q = Alumno.query.filter_by(ciclo_id=ciclo_activo.id)
    if bloque_id:
        q = q.filter(Alumno.bloque_id == bloque_id)
    if grado:
        q = q.filter(Alumno.grado == grado)
    if grupo:
        q = q.filter(Alumno.grupo == grupo.upper())

    alumnos = q.order_by(Alumno.grado, Alumno.grupo, Alumno.nombre).all()

    # 3️⃣ Armar estructura de alumnos con sus nominaciones por mes
    resultado = []
    for alumno in alumnos:
        valores_por_mes = {str(e.mes_ordinal): [] for e in eventos}
        nominaciones = Nominacion.query.filter_by(alumno_id=alumno.id, ciclo_id=ciclo_activo.id).all()

        for n in nominaciones:
            if n.evento and n.evento.mes_ordinal:
                valores_por_mes[str(n.evento.mes_ordinal)].append({
                    "valor": n.valor.nombre if n.valor else "",
                    "maestro": n.maestro.nombre if n.maestro else "",
                    "fecha": n.fecha.strftime("%Y-%m-%d") if n.fecha else ""
                })

        sin_nominacion = all(len(v) == 0 for v in valores_por_mes.values())

        resultado.append({
            "id": alumno.id,
            "nombre": alumno.nombre,
            "grado": alumno.grado,
            "grupo": alumno.grupo,
            "valores_por_mes": valores_por_mes,
            "sin_nominacion": sin_nominacion
        })

    return jsonify({
        "ciclo": ciclo_activo.nombre,
        "bloque": Bloque.query.get(bloque_id).nombre if bloque_id else None,
        "meses": meses_data,
        "alumnos": resultado
    })

@admin_bp.route('/bloques_json')
@login_required
@admin_required
def bloques_json():
    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo_activo:
        return jsonify([])
    bloques = Bloque.query.filter_by(ciclo_id=ciclo_activo.id).order_by(Bloque.nombre.asc()).all()
    return jsonify([{"id": b.id, "nombre": b.nombre} for b in bloques])

@admin_bp.route('/matriz')
@login_required
@admin_required
def matriz_vista():
    """Vista HTML de la matriz mensual."""
    return render_template('admin_matriz.html')

# ===============================
# 👨‍🏫 PANEL DEL MAESTRO (vista previa tipo matriz)
# ===============================
from flask import jsonify
from models import Alumno, Nominacion, EventoAsamblea, CicloEscolar, Maestro, Valor

@nom.route('/panel_nominaciones')
@login_required
def panel_nominaciones():
    """Vista HTML del panel de nominaciones (para maestros)."""
    if current_user.rol != 'profesor':
        flash("🚫 Solo los profesores pueden acceder al panel de nominaciones.", "danger")
        return redirect(url_for('nom.principal'))
    return render_template('panel_maestro.html')


@nom.route('/panel_nominaciones_data')
@login_required
def panel_nominaciones_data():
    """Devuelve los datos para la matriz del maestro actual (con encabezado informativo)."""
    if current_user.rol != 'profesor':
        return jsonify({"error": "No autorizado."}), 403

    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo_activo:
        return jsonify({"error": "No hay ciclo activo."}), 400

    maestro = Maestro.query.filter_by(correo=current_user.email, ciclo_id=ciclo_activo.id).first()
    if not maestro:
        return jsonify({"error": "No se encontró tu registro de maestro."}), 404

    # --- Evento activo del ciclo (si hay)
    evento_activo = (
        EventoAsamblea.query
        .filter_by(ciclo_id=ciclo_activo.id, activo=True)
        .order_by(EventoAsamblea.fecha_evento.asc())
        .first()
    )

    # --- Lista de meses del ciclo
    eventos = EventoAsamblea.query.filter_by(ciclo_id=ciclo_activo.id).order_by(EventoAsamblea.mes_ordinal.asc()).all()
    meses = [{"id": e.id, "nombre": e.nombre_mes, "mes_ordinal": e.mes_ordinal} for e in eventos]

    # --- Detectar bloque actual a partir de los alumnos del ciclo
    primer_alumno = Alumno.query.filter_by(ciclo_id=ciclo_activo.id).first()
    bloque_id = primer_alumno.bloque_id if primer_alumno else None
    bloque_nombre = None
    grado_actual = primer_alumno.grado if primer_alumno else None
    grupo_actual = primer_alumno.grupo if primer_alumno else None

    if bloque_id:
        from models import Bloque
        bloque_obj = Bloque.query.get(bloque_id)
        bloque_nombre = bloque_obj.nombre if bloque_obj else None

    # --- Filtrar alumnos del mismo bloque / grado / grupo
    alumnos = (
        Alumno.query
        .filter_by(ciclo_id=ciclo_activo.id, bloque_id=bloque_id, grado=grado_actual, grupo=grupo_actual)
        .order_by(Alumno.nombre.asc())
        .all()
    )

    resultado = []
    for alumno in alumnos:
        valores_por_mes = {str(e.mes_ordinal): [] for e in eventos}
        nominaciones = Nominacion.query.filter_by(alumno_id=alumno.id, ciclo_id=ciclo_activo.id).all()

        for n in nominaciones:
            if n.evento and n.evento.mes_ordinal:
                valores_por_mes[str(n.evento.mes_ordinal)].append({
                    "valor": n.valor.nombre if n.valor else "",
                    "maestro": n.maestro.nombre if n.maestro else "",
                    "fecha": n.fecha.strftime("%Y-%m-%d") if n.fecha else ""
                })

        sin_nominacion = all(len(v) == 0 for v in valores_por_mes.values())

        resultado.append({
            "id": alumno.id,
            "nombre": alumno.nombre,
            "grado": alumno.grado,
            "grupo": alumno.grupo,
            "valores_por_mes": valores_por_mes,
            "sin_nominacion": sin_nominacion
        })

    # Detectar bloque automáticamente a partir de los alumnos cargados
    bloque_nombre = None
    if alumnos:
        primer_alumno = alumnos[0]
        if primer_alumno.bloque_id:
            from models import Bloque
            bloque_obj = Bloque.query.get(primer_alumno.bloque_id)
            bloque_nombre = bloque_obj.nombre if bloque_obj else None

    return jsonify({
        "bloque": bloque_nombre or "Sin bloque",
        "grado": alumnos[0].grado if alumnos else "—",
        "grupo": alumnos[0].grupo if alumnos else "—",
        "ciclo": ciclo_activo.nombre,
        "evento_activo": evento_activo.nombre_mes if evento_activo else None,
        "cierre_evento": evento_activo.fecha_cierre_nominaciones.strftime("%d/%m/%Y %H:%M") if evento_activo else None,
        "meses": meses,
        "alumnos": resultado
    })

# ===============================
# 🧾 NOMINACIÓN INDIVIDUAL DE ALUMNO
# ===============================
from datetime import datetime

@nom.route('/nominacion_alumno/<int:alumno_id>', methods=['GET', 'POST'])
@login_required
def nominar_alumno_individual(alumno_id):
    """Vista individual donde el maestro puede nominar a un alumno."""
    if current_user.rol != 'profesor':
        flash("🚫 Solo los profesores pueden registrar nominaciones.", "danger")
        return redirect(url_for('nom.principal'))

    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo_activo:
        flash("⚠️ No hay ciclo activo disponible.", "warning")
        return redirect(url_for('nom.panel_nominaciones'))

    maestro = Maestro.query.filter_by(correo=current_user.email, ciclo_id=ciclo_activo.id).first()
    alumno = Alumno.query.get_or_404(alumno_id)

    # Valores activos del ciclo
    valores = Valor.query.filter_by(ciclo_id=ciclo_activo.id, activo=True).all()

    # Detectar el evento actual (mes abierto)
    evento_abierto = (
        EventoAsamblea.query
        .filter_by(ciclo_id=ciclo_activo.id, bloque_id=alumno.bloque_id, activo=True)
        .order_by(EventoAsamblea.fecha_evento.asc())
        .first()
    )

    # Si hay evento activo, filtrar nominaciones solo de ese evento (mismo mes)
    if evento_abierto:
        nominaciones_previas = (
            Nominacion.query
            .filter_by(alumno_id=alumno.id, ciclo_id=ciclo_activo.id, evento_id=evento_abierto.id)
            .all()
        )
    else:
        nominaciones_previas = []

    # Obtener valores ya usados en el mes actual
    valores_asignados = [n.valor_id for n in nominaciones_previas]

    # Filtrar valores que aún puede recibir este mes
    valores_disponibles = [v for v in valores if v.id not in valores_asignados]

    # Evento activo del bloque del alumno
    evento_abierto = (
        EventoAsamblea.query
        .filter_by(ciclo_id=ciclo_activo.id, bloque_id=alumno.bloque_id, activo=True)
        .order_by(EventoAsamblea.fecha_evento.asc())
        .first()
    )

    if request.method == 'POST':
        valor_id = request.form.get('valor_id')
        comentario = request.form.get('comentario', '').strip()

        if not valor_id:
            flash("⚠️ Debes seleccionar un valor.", "warning")
            return redirect(request.url)

        nueva_nom = Nominacion(
            alumno_id=alumno.id,
            maestro_id=maestro.id,
            valor_id=valor_id,
            ciclo_id=ciclo_activo.id,
            comentario=comentario,
            evento_id=evento_abierto.id if evento_abierto else None,
            tipo='alumno',
            fecha=datetime.utcnow()
        )
        db.session.add(nueva_nom)
        db.session.commit()

        flash(f"✅ Nominación registrada para {alumno.nombre}.", "success")
        return redirect(url_for(
            'nom.matriz_grupo_maestro',
            bloque_id=alumno.bloque_id,
            grado=alumno.grado,
            grupo=alumno.grupo
        ))

    return render_template(
        'nominacion_individual.html',
        alumno=alumno,
        valores_disponibles=valores_disponibles,
        valores_asignados=nominaciones_previas
    )


# ===============================
# 🧭 PANEL PRINCIPAL DEL PROFESOR
# ===============================
@nom.route('/panel_profesor')
@login_required
def panel_profesor():
    """Panel principal con accesos rápidos para el profesor."""
    if current_user.rol != 'profesor':
        flash("🚫 Solo los profesores pueden acceder a este panel.", "danger")
        return redirect(url_for('nom.principal'))

    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
    return render_template('panel_profesor.html', ciclo=ciclo_activo)


# =======================================
# 👨‍🏫 VISTA "MIS GRUPOS" (profesor)
# =======================================
@nom.route('/mis_grupos')
@login_required
def mis_grupos():
    """Muestra los grupos y alumnos organizados por grado y grupo."""
    if current_user.rol != 'profesor':
        flash("🚫 Solo los profesores pueden acceder a esta vista.", "danger")
        return redirect(url_for('nom.principal'))

    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo_activo:
        flash("⚠️ No hay ciclo escolar activo.", "warning")
        return redirect(url_for('nom.panel_profesor'))

    # Obtener alumnos del ciclo agrupados por grado y grupo
    alumnos = Alumno.query.filter_by(ciclo_id=ciclo_activo.id).order_by(Alumno.grado, Alumno.grupo, Alumno.nombre).all()

    # Organizar los alumnos en un diccionario: { "1A": [alumnos], "1B": [...], etc. }
    grupos = {}
    for alumno in alumnos:
        clave = f"{alumno.grado}°{alumno.grupo}"
        if clave not in grupos:
            grupos[clave] = []
        grupos[clave].append(alumno)

    return render_template('mis_grupos.html', grupos=grupos, ciclo=ciclo_activo)


@nom.route('/seleccionar_bloque')
@login_required
def seleccionar_bloque():
    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()

    # 🔹 Ordenar por número si el nombre contiene un número (Bloque 1, Bloque 2, etc.)
    bloques = (
        Bloque.query
        .filter_by(ciclo_id=ciclo_activo.id)
        .order_by(db.cast(db.func.substr(Bloque.nombre, 8), db.Integer))  # Ordena por el número después de "Bloque "
        .all()
    )

    return render_template('seleccionar_bloque.html', bloques=bloques, ciclo=ciclo_activo)

# -------------------------------
# 🔹 Seleccionar grado dentro del bloque
# -------------------------------
@nom.route('/bloque/<int:bloque_id>/grados')
@login_required
def seleccionar_grado(bloque_id):
    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
    bloque = Bloque.query.get_or_404(bloque_id)

    # 🔍 Obtener los grados únicos dentro del bloque
    grados = (
        db.session.query(Alumno.grado)
        .filter_by(bloque_id=bloque.id, ciclo_id=ciclo_activo.id)
        .distinct()
        .order_by(Alumno.grado)
        .all()
    )
    grados = [g[0] for g in grados]  # Convierte [(1,), (2,), (3,)] → [1,2,3]

    return render_template('seleccionar_grado.html', bloque=bloque, grados=grados, ciclo=ciclo_activo)


# -------------------------------
# 🔹 Panel de gestión de usuarios
# -------------------------------


@admin_bp.route('/admin/maestros')
@login_required
@admin_required
def admin_maestros():
    return redirect(url_for('admin_bp.alumnos_maestros'))  # si ya existe el template o ruta
    # o bien:
    # return render_template('admin_maestros.html')

@admin_bp.route('/usuarios/<rol>')
@login_required
@admin_required
def admin_usuarios_por_rol(rol):
    """Muestra usuarios filtrados por rol (admin, profesor, estudiante)"""
    roles_validos = ['admin', 'profesor', 'estudiante']
    if rol not in roles_validos:
        flash("Rol no válido.", "danger")
        return redirect(url_for('nom.principal'))

    # Filtrar usuarios según el rol
    usuarios = Usuario.query.filter_by(rol=rol).all()
    return render_template('admin_usuarios.html', usuarios=usuarios, rol_actual=rol)

# =========================================================
# 🗑️ ELIMINAR USUARIO (ADMIN, PROFESOR O ESTUDIANTE)
# =========================================================
@admin_bp.route('/usuarios/eliminar/<int:id>', methods=['POST'])
@login_required
@admin_required
def eliminar_usuario(id):
    usuario = Usuario.query.get_or_404(id)

    # 🚫 Evita eliminar el admin principal (puedes añadir más correos si quieres protegerlos)
    if usuario.email.lower() in ["admin@cela.edu.mx", "admin@colegio.edu.mx"]:
        return jsonify({
            "success": False,
            "message": "⚠️ No puedes eliminar el administrador principal."
        }), 400

    db.session.delete(usuario)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"🗑️ Usuario '{usuario.nombre}' eliminado correctamente."
    }), 200


# ============================================================
# 🔹 GESTIÓN DE MAESTROS
# ============================================================
@admin_bp.route('/maestros', methods=['GET'])
@login_required
@admin_required
def gestionar_maestros():
    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo_activo:
        flash("⚠️ No hay ciclo escolar activo.", "warning")
        return redirect(url_for('admin_bp.gestionar_ciclos'))
    
    maestros = Maestro.query.filter_by(ciclo_id=ciclo_activo.id, activo=True).all()
    return render_template('admin_maestros.html', maestros=maestros)


# ------------------------------------------------------------
# 🟢 Crear maestro manualmente (con rol profesor y contraseña)
# ------------------------------------------------------------
@admin_bp.route('/maestros/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuevo_maestro():
    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo_activo:
        flash("⚠️ No hay un ciclo activo para registrar maestros.", "warning")
        return redirect(url_for('admin_bp.maestros_ciclo'))

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        correo = request.form.get('correo', '').strip().lower()
        password = request.form.get('password', '').strip()

        # Validar campos obligatorios
        if not nombre or not correo or not password:
            flash("⚠️ Todos los campos son obligatorios.", "warning")
            return redirect(url_for('admin_bp.nuevo_maestro'))

        # Verificar si ya existe un usuario con ese correo
        usuario_existente = Usuario.query.filter_by(email=correo).first()
        if usuario_existente:
            flash("❌ Ya existe un usuario con ese correo electrónico.", "danger")
            return redirect(url_for('admin_bp.maestros_ciclo'))

        # Crear usuario con rol profesor
        nuevo_usuario = Usuario(nombre=nombre, email=correo, rol='profesor')
        nuevo_usuario.set_password(password)
        db.session.add(nuevo_usuario)

        # Crear registro en tabla maestros
        nuevo_maestro = Maestro(
            nombre=nombre,
            correo=correo,
            ciclo_id=ciclo_activo.id,
            activo=True
        )
        db.session.add(nuevo_maestro)

        db.session.commit()
        flash(f"✅ Maestro '{nombre}' creado correctamente con rol 'profesor'.", "success")
        return redirect(url_for('admin_bp.maestros_ciclo'))

    return render_template('crear_maestro.html')


@admin_bp.route('/alumnos/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_alumno_manual():
    ciclo = CicloEscolar.query.filter_by(activo=True).first()
    bloques = Bloque.query.filter_by(ciclo_id=ciclo.id).all() if ciclo else []

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        grado = request.form.get('grado')
        grupo = request.form.get('grupo')
        nivel = request.form.get('nivel')
        bloque_id = request.form.get('bloque_id')

        if not all([nombre, grado, grupo, nivel, bloque_id]):
            flash("⚠️ Todos los campos son obligatorios.", "warning")
            return redirect(url_for('admin_bp.crear_alumno_manual'))

        nuevo = Alumno(
            nombre=nombre,
            grado=grado,
            grupo=grupo,
            nivel=nivel,
            bloque_id=bloque_id,
            ciclo_id=ciclo.id
        )
        db.session.add(nuevo)
        db.session.commit()
        flash(f"✅ Alumno {nombre} registrado correctamente.", "success")
        return redirect(url_for('admin_bp.maestros_ciclo'))

    return render_template('crear_alumno.html', ciclo=ciclo, bloques=bloques)


# Muestra los grupos disponibles dentro de un grado
@nom.route('/bloque/<int:bloque_id>/grado/<grado>')
@login_required
def grupos_por_grado(bloque_id, grado):
    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo_activo:
        flash("⚠️ No hay ciclo activo.", "warning")
        return redirect(url_for('nom.principal'))

    grupos = (
        db.session.query(Alumno.grupo)
        .filter_by(ciclo_id=ciclo_activo.id, bloque_id=bloque_id, grado=grado)
        .distinct()
        .order_by(Alumno.grupo.asc())
        .all()
    )
    grupos = [g[0] for g in grupos]
    bloque = Bloque.query.get_or_404(bloque_id)
    return render_template('grupos_por_grado.html', bloque=bloque, grado=grado, grupos=grupos)

# Vista temporal para mostrar alumnos de ese grupo
@nom.route('/bloque/<int:bloque_id>/grado/<grado>/grupo/<grupo>')
@login_required
def lista_alumnos_grupo(bloque_id, grado, grupo):
    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
    alumnos = (
        Alumno.query
        .filter_by(ciclo_id=ciclo_activo.id, bloque_id=bloque_id, grado=grado, grupo=grupo)
        .order_by(Alumno.nombre.asc())
        .all()
    )
    bloque = Bloque.query.get_or_404(bloque_id)
    return render_template('lista_alumnos.html', alumnos=alumnos, bloque=bloque, grado=grado, grupo=grupo)

# ===========================
# 🔹 MATRIZ DE NOMINACIÓN POR GRUPO (MAESTRO)
# ===========================
# 🔹 MATRIZ DE NOMINACIÓN POR GRUPO (MAESTRO)
# ===========================
from datetime import datetime

@nom.route('/bloque/<int:bloque_id>/grado/<grado>/grupo/<grupo>/nominaciones')
@login_required
def matriz_grupo_maestro(bloque_id, grado, grupo):
    if current_user.rol != 'profesor':
        flash("🚫 Solo los profesores pueden acceder a esta vista.", "danger")
        return redirect(url_for('nom.principal'))

    hoy = datetime.now().date()
    ciclo = CicloEscolar.query.filter_by(activo=True).first()
    bloque = Bloque.query.get_or_404(bloque_id)

    # 🔹 Buscar evento vigente (activo y dentro de fechas válidas)
    evento_abierto = (
        EventoAsamblea.query
        .filter(
            EventoAsamblea.ciclo_id == ciclo.id,
            EventoAsamblea.bloque_id == bloque.id,
            EventoAsamblea.activo == True,
            EventoAsamblea.fecha_evento >= hoy  # aún no ha pasado
        )
        .order_by(EventoAsamblea.fecha_evento.asc())
        .first()
    )

    # Si no hay futuros, usar el último pasado (el más reciente)
    if not evento_abierto:
        evento_abierto = (
            EventoAsamblea.query
            .filter_by(ciclo_id=ciclo.id, bloque_id=bloque.id)
            .order_by(EventoAsamblea.fecha_evento.desc())
            .first()
        )

    mes_actual = evento_abierto.mes_ordinal if evento_abierto else None

    # 🔹 Cargar todos los eventos del ciclo del bloque
    eventos = (
        EventoAsamblea.query
        .filter_by(ciclo_id=ciclo.id, bloque_id=bloque.id)
        .order_by(EventoAsamblea.mes_ordinal.asc())
        .all()
    )

    # 🔹 Agrupar por mes
    eventos_por_mes = {}
    for e in eventos:
        if e.mes_ordinal not in eventos_por_mes:
            eventos_por_mes[e.mes_ordinal] = e

    # 🔹 Cargar alumnos del grupo
    alumnos = (
        Alumno.query
        .filter_by(ciclo_id=ciclo.id, bloque_id=bloque.id, grado=grado, grupo=grupo)
        .order_by(Alumno.nombre.asc())
        .all()
    )

    data = []
    for a in alumnos:
        nominaciones = (
            Nominacion.query
            .filter_by(alumno_id=a.id, ciclo_id=ciclo.id, tipo='alumno')
            .join(EventoAsamblea, Nominacion.evento_id == EventoAsamblea.id)
            .add_entity(EventoAsamblea)
            .all()
        )

        valores_por_mes = {str(e.mes_ordinal): [] for e in eventos_por_mes.values()}

        for n, evento in nominaciones:
            if evento and evento.mes_ordinal:
                valores_por_mes[str(evento.mes_ordinal)].append({
                    "valor": n.valor.nombre if n.valor else "",
                    "maestro": n.maestro.nombre if n.maestro else "",
                    "fecha": n.fecha.strftime("%Y-%m-%d") if n.fecha else ""
                })

        tiene_nominaciones = any(len(v) > 0 for v in valores_por_mes.values())
        sin_nominacion_total = not tiene_nominaciones

        data.append({
            "alumno": a,
            "valores": valores_por_mes,
            "sin_nominacion_total": sin_nominacion_total
        })

    return render_template(
        "matriz_grupo_maestro.html",
        ciclo=ciclo,
        bloque=bloque,
        grado=grado,
        grupo=grupo,
        eventos=list(eventos_por_mes.values()),
        alumnos=data,
        mes_actual=mes_actual,
        evento_abierto=evento_abierto
    )


@nom.route('/mis_nominaciones')
@login_required
def mis_nominaciones():
    """Muestra las nominaciones realizadas por el maestro actual"""
    if current_user.rol != 'profesor':
        flash("🚫 Solo los profesores pueden acceder a esta vista.", "danger")
        return redirect(url_for('nom.principal'))

    ciclo_activo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo_activo:
        flash("⚠️ No hay ciclo escolar activo.", "warning")
        return redirect(url_for('nom.panel_profesor'))

    # 🧑‍🏫 Buscar al maestro logueado
    maestro = Maestro.query.filter_by(correo=current_user.email, ciclo_id=ciclo_activo.id).first()
    if not maestro:
        flash("⚠️ No se encontró tu registro como maestro en el ciclo activo.", "warning")
        return redirect(url_for('nom.panel_profesor'))

    # 🔍 Buscar nominaciones hechas por este maestro
    nominaciones = (
        Nominacion.query
        .filter_by(maestro_id=maestro.id, ciclo_id=ciclo_activo.id)
        .order_by(Nominacion.fecha.desc())
        .all()
    )

    return render_template(
        'mis_nominaciones.html',
        maestro=maestro,
        nominaciones=nominaciones,
        ciclo=ciclo_activo
    )



from sqlalchemy import cast, Integer, func
# ===========================
# 🔹 Nueva vista visual de bloques
# ===========================
@nom.route('/admin/bloques_vista', methods=['GET'])
@login_required
def admin_bloques_vista():
    if current_user.rol != 'admin':
        flash("🚫 Solo los administradores pueden ver esta sección.", "danger")
        return redirect(url_for('nom.principal'))

    ciclo = CicloEscolar.query.filter_by(activo=True).first()
    if not ciclo:
        flash("⚠️ No hay ciclo escolar activo.", "warning")
        return redirect(url_for('nom.principal'))

    bloques = (
    Bloque.query
    .filter_by(ciclo_id=ciclo.id)
    .order_by(cast(func.substr(Bloque.nombre, 8), Integer).asc())
    .all()
    )

    data = []
    for b in bloques:
        grados_raw = db.session.query(Alumno.grado).filter(
            Alumno.ciclo_id == ciclo.id,
            Alumno.bloque_id == b.id
        ).distinct().all()
        grados = [g[0] for g in grados_raw]

        grados_info = []
        for g in grados:
            grupos_raw = db.session.query(Alumno.grupo).filter(
                Alumno.ciclo_id == ciclo.id,
                Alumno.bloque_id == b.id,
                Alumno.grado == g
            ).distinct().all()
            grupos = [x[0] for x in grupos_raw]
            grados_info.append({"grado": g, "grupos": grupos})

        data.append({"bloque": b, "grados": grados_info})

    return render_template('admin_bloques_vista.html', ciclo=ciclo, data=data)

import io
import pandas as pd
from flask import send_file, jsonify

@admin_bp.route('/maestros/plantilla', methods=['GET'])
@login_required
@admin_required
def descargar_plantilla_maestros():
    # Define columnas esperadas
    columnas = ['Nombre', 'Email', "contraseña"]
    df = pd.DataFrame(columns=columnas)

    # Crear archivo Excel en memoria
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Plantilla')
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name='Plantilla_Maestros.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    
    # ------------------------------------------------------------
# 🔄 Actualizar orden del bloque
# ------------------------------------------------------------
@admin_bp.route('/bloques/<int:id>/orden', methods=['POST'])
@login_required
def actualizar_orden_bloque(id):
    if current_user.rol != 'admin':
        flash("🚫 Solo los administradores pueden realizar esta acción.", "danger")
        return redirect(url_for('nom.principal'))

    bloque = Bloque.query.get_or_404(id)
    nuevo_orden = request.form.get('orden', type=int)

    if nuevo_orden is None:
        flash("⚠️ El valor de orden no es válido.", "warning")
    else:
        bloque.orden = nuevo_orden
        db.session.commit()
        flash(f"✅ Orden del bloque '{bloque.nombre}' actualizado a {nuevo_orden}.", "success")

    return redirect(url_for('admin_bp.bloques_ciclo'))


# ------------------------------------------------------------
# 🗑️ Eliminar bloque (solo si no tiene alumnos)
# ------------------------------------------------------------
@admin_bp.route('/bloques/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_bloque(id):
    if current_user.rol != 'admin':
        flash("🚫 Solo los administradores pueden realizar esta acción.", "danger")
        return redirect(url_for('nom.principal'))

    bloque = Bloque.query.get_or_404(id)
    alumnos_asociados = Alumno.query.filter_by(bloque_id=bloque.id).count()

    if alumnos_asociados > 0:
        flash(f"⚠️ No se puede eliminar el bloque '{bloque.nombre}' porque tiene alumnos asociados.", "warning")
    else:
        db.session.delete(bloque)
        db.session.commit()
        flash(f"🗑️ Bloque '{bloque.nombre}' eliminado correctamente.", "success")

    return redirect(url_for('admin_bp.bloques_ciclo'))
