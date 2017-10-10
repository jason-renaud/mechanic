# do not modify - generated code at UTC {{ timestamp }}


from flask_admin.contrib.sqla import ModelView
from flask_admin import Admin


def init_models(app, db):
    {% if admin -%}
    import models
    admin = Admin(app)
    {% for model_name, model_obj in data.items() -%}
    admin.add_view(ModelView(models.{{ model_name }}, db.session))
    {% endfor -%}
    {% else -%}
    pass
    {%- endif %}

