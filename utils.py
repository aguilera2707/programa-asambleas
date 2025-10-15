import os, platform
from extensions import db
from models import CicloEscolar

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
    os.makedirs(output_dir, exist_ok=True)

    if platform.system() == "Windows":
        # Usar Word en local
        template_docx = os.path.join("docx_templates", "formato_asamblea.docx")
        doc = DocxTemplate(template_docx)
        doc.render(context)

        tmp_docx = os.path.join(output_dir, f"{filename}.docx")
        doc.save(tmp_docx)

        output_pdf = os.path.join(output_dir, f"{filename}.pdf")

        word = win32com.client.DispatchEx('Word.Application')
        word.Visible = False
        word.DisplayAlerts = 0
        docx = word.Documents.Open(tmp_docx, ReadOnly=1)
        docx.SaveAs(output_pdf, FileFormat=17)
        docx.Close(False)
        word.Quit()

        os.remove(tmp_docx)
        return output_pdf
    else:
        # Usar WeasyPrint en Render
        html_content = render_template(template_name, **context)
        output_pdf = os.path.join(output_dir, f"{filename}.pdf")
        HTML(string=html_content).write_pdf(output_pdf)
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