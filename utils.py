import os
from flask import render_template
from weasyprint import HTML
from extensions import db
from models import CicloEscolar

def generar_pdf_html(template_name: str, context: dict, output_dir: str, filename: str):
    os.makedirs(output_dir, exist_ok=True)

    # Renderizamos la plantilla HTML con Flask
    html_content = render_template(template_name, **context)

    # Convertimos a PDF
    output_pdf = os.path.join(output_dir, f"{filename}.pdf")
    HTML(string=html_content).write_pdf(output_pdf)

    return output_pdf

def ciclo_actual():
    return db.session.query(CicloEscolar).filter_by(activo=True).first()
