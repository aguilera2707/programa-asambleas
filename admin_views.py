from flask_admin.contrib.sqla import ModelView
from models import CicloEscolar
from extensions import db

class CicloEscolarAdmin(ModelView):
    def on_model_change(self, form, model, is_created):
        if model.activo:
            otros = CicloEscolar.query.filter(CicloEscolar.id != model.id).all()
            for otro in otros:
                otro.activo = False
            db.session.commit()
