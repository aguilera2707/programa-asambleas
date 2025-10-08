# admin_views.py
from flask_admin.contrib.sqla import ModelView
from extensions import db
from models import CicloEscolar

class CicloEscolarAdmin(ModelView):
    column_list = ('nombre', 'activo', 'fecha_inicio', 'fecha_fin')
    form_columns = ('nombre', 'activo', 'fecha_inicio', 'fecha_fin', 'observaciones')
    can_delete = True
    can_create = True

    def on_model_change(self, form, model, is_created):
        # Si se activa este ciclo, desactivar los demás
        if model.activo:
            otros = CicloEscolar.query.filter(CicloEscolar.id != model.id).all()
            for otro in otros:
                otro.activo = False
            db.session.commit()
