# do not modify - generated code at UTC {{ timestamp }}
import uuid
import datetime

from flask import url_for

from {{ app_name }} import db
from mechanic.base.models import MechanicBaseModelMixin

{%- for base_model_path, base_model_names in base_models.items() %}
{%- if base_model_path != "mechanic.base.models" %}
from {{ base_model_path }} import ({% for name in base_model_names %}{{ name }}, {% endfor %})
{%- endif %}
{%- endfor %}
{# #}

def get_uri(context):
    try:
        return str(url_for(context.current_parameters["controller"], resource_id=context.current_parameters["identifier"]))
    except Exception:
        return None
{% for m2m_key, m2m in many_to_many.items() %}
{{ m2m_key }} = db.Table("{{ m2m_key }}",
                        {%- for k, v in m2m.fkeys.items() %}
                       db.Column("{{ k }}", db.String(36), db.ForeignKey("{{ v }}", ondelete="SET NULL")),
                        {%- endfor %}
                       schema="{{ m2m.db_schema }}"
)
{%- endfor %}
{%- for model_name, model in models.items() %}
{# #}
{# #}
class {{ model_name }}({{ model.base_model_name }}, db.Model):
    {%- if model.comment %}
    """
    {{ model.comment }}
    """
    {%- endif %}
    __tablename__ = "{{ model.db_tablename }}"
    __table_args__ = {"schema": "{{ model.db_schema }}"}
    {# #}
    controller = db.Column(db.String(), default="{{ model.controller }}")
    uri = db.Column(db.String, default=get_uri)
    {#- Columns -#}
    {%- for col_name, col_obj in model.columns.items() %}
    {{ col_name }} = db.Column(db.{{ col_obj.type }}({{ col_obj.maxLength }}),{%- if col_obj.foreign_key %} db.ForeignKey("{{ col_obj.foreign_key }}"),{%- endif %} nullable={{ col_obj.nullable }},)
    {%- endfor %}
    {#- Relationships -#}
    {%- for rel_name, rel_obj in model.relationships.items() %}
    {{ rel_name }} = db.relationship("{{ rel_obj.model }}", {% if rel_obj.backref %}backref="{{ rel_obj.backref }}",{% endif %}{% if rel_obj.back_populates %} back_populates="{{ rel_obj.backref }}",{% endif %} uselist={{ rel_obj.uselist }},{% if rel_obj.foreign_keys %} foreign_keys={{ rel_obj.foreign_keys }},{% endif -%}{% if rel_obj.secondary %} secondary={{ rel_obj.secondary }},{% endif -%})
    {%- endfor -%}
{%- endfor %}
