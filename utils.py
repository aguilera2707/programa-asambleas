import os
from docxtpl import DocxTemplate
import win32com.client
from extensions import db
from models import CicloEscolar

def convertir_docx_a_pdf_com(input_docx: str, output_pdf: str):
    word = win32com.client.DispatchEx('Word.Application')
    word.Visible = False
    word.DisplayAlerts = 0

    doc = word.Documents.Open(input_docx, ReadOnly=1)
    doc.SaveAs(output_pdf, FileFormat=17)  # 17 = PDF
    doc.Close(False)
    word.Quit()

def generar_pdf(template_docx: str, output_dir: str, context: dict, filename: str):
    os.makedirs(output_dir, exist_ok=True)

    doc = DocxTemplate(template_docx)
    doc.render(context)

    tmp_docx = os.path.join(output_dir, f"{filename}.docx")
    doc.save(tmp_docx)

    output_pdf = os.path.join(output_dir, f"{filename}.pdf")
    convertir_docx_a_pdf_com(tmp_docx, output_pdf)

    os.remove(tmp_docx)  # limpiar el DOCX intermedio
    return output_pdf

def ciclo_actual():
    return db.session.query(CicloEscolar).filter_by(activo=True).first()
