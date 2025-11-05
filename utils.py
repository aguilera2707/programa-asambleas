import os, platform
from extensions import db
from models import CicloEscolar, EventoAsamblea  # 👈 agregamos EventoAsamblea aquí
from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

if platform.system() == "Windows":
    import win32com.client
    from docxtpl import DocxTemplate
else:
    from weasyprint import HTML
    from flask import render_template

def generar_pdf(template_name: str, context: dict, output_dir: str, filename: str):
    import platform, os, tempfile
    from pathlib import Path

    os.makedirs(output_dir, exist_ok=True)

    if platform.system() == "Windows":
        from docxtpl import DocxTemplate
        import win32com.client

        # 🔹 Ruta absoluta a la plantilla
        plantilla_path = Path.cwd() / "docx_templates" / template_name
        if not plantilla_path.exists():
            raise FileNotFoundError(f"No se encontró la plantilla: {plantilla_path}")

        # 🔹 Nombre seguro sin acentos ni espacios raros
        safe_name = ''.join(c if c.isalnum() or c in '_.-' else '_' for c in filename)
        temp_docx = Path(tempfile.gettempdir()) / f"{safe_name}.docx"
        output_pdf = Path(output_dir).resolve() / f"{safe_name}.pdf"

        # 🔹 Renderizar plantilla
        doc = DocxTemplate(str(plantilla_path))
        doc.render(context)
        doc.save(str(temp_docx))

        # 🔹 Convertir usando Word COM
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        try:
            docx = word.Documents.Open(str(temp_docx))
            # Guardar como PDF (FileFormat=17)
            docx.SaveAs(str(output_pdf), FileFormat=17)
            docx.Close(False)
        except Exception as e:
            # Reintento alternativo: usar ExportAsFixedFormat
            try:
                docx.ExportAsFixedFormat(
                    OutputFileName=str(output_pdf),
                    ExportFormat=17,  # PDF
                    OpenAfterExport=False,
                    OptimizeFor=0,  # calidad estándar
                    CreateBookmarks=0,
                    DocStructureTags=True,
                    BitmapMissingFonts=True,
                    UseISO19005_1=False
                )
            except Exception as e2:
                raise RuntimeError(f"Error al exportar PDF: {e2}")
        finally:
            word.Quit()

        # 🔹 Limpiar temporal
        if temp_docx.exists():
            temp_docx.unlink(missing_ok=True)

        return str(output_pdf)

    else:
        # Linux (Render)
        from weasyprint import HTML
        from flask import render_template
        html_content = render_template(template_name, **context)
        output_pdf = os.path.join(output_dir, f"{filename}.pdf")
        HTML(string=html_content, base_url=".").write_pdf(
            output_pdf, optimize_size=('images',)
        )
        return output_pdf


def ciclo_actual():
    return db.session.query(CicloEscolar).filter_by(activo=True).first()

# 🔹 Decorador para restringir acceso solo a administradores
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("⚠️ Debes iniciar sesión para acceder a esta página.", "warning")
            return redirect(url_for('nom.login'))

        if current_user.rol != 'admin':
            flash("🚫 No tienes permisos para acceder a esta sección.", "danger")
            return redirect(url_for('nom.principal'))

        return f(*args, **kwargs)
    return decorated_function


# ======================================
# 🔹 Cierre automático de eventos vencidos
# ======================================
from datetime import datetime

def cerrar_eventos_vencidos():
    """Desactiva automáticamente los eventos cuya fecha de cierre ya pasó, 
    pero respeta si el administrador los reactivó manualmente."""
    ahora = datetime.now()

    eventos = EventoAsamblea.query.all()
    for evento in eventos:
        # Si el admin lo activó manualmente, no lo tocamos
        if evento.activo:
            continue

        # Si ya pasó su fecha de cierre y sigue marcado activo, lo cerramos
        if evento.fecha_cierre_nominaciones and evento.fecha_cierre_nominaciones <= ahora:
            evento.activo = False

    db.session.commit()
