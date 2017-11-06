# do not modify - generated code at UTC {{ timestamp }}
"""
import uuid
import datetime

from flask import url_for
from sqlalchemy.ext.hybrid import hybrid_property

from mechanic import utils
from {{ app_name }} import db

from mechanic.base.models import MechanicBaseModelMixin
"""

import datetime

from flask import url_for
from sqlalchemy import Column, String, Integer, ForeignKey, Float, DateTime, create_engine, MetaData
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base

from mechanic.starter.base import utils

engine = create_engine("sqlite:///:memory:", echo=False)
metadata = MetaData()

Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()


def get_uri(context):
    try:
        return str(url_for(context.current_parameters["controller"], resource_id=context.current_parameters["identifier"]))
    except Exception:
        return None


class MechanicBaseModelMixin(object):
    identifier = Column(String(36), primary_key=True, nullable=False, default=utils.random_uuid)
    created = Column(DateTime, default=datetime.datetime.utcnow)
    last_modified = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    etag = Column(String(36), default=utils.random_uuid, onupdate=utils.random_uuid)
    controller = Column(String, default="orgcontactitemcontroller")
    uri = Column(String, default=get_uri)

"""
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
"""

{# Primitive model - no references and just plan data types #}
{%- for model_name, model in models.items() %}
class {{ model_name }}({{ model.base_model_name }}, Base):
    {%- if model.comment %}
    """
    {{ model.comment }}
    """
    {%- endif %}
    __tablename__ = "{{ model.db_tablename }}"
    #__table_args__ = {"schema": "{{ model.db_schema }}"}
    {# #}
    {%- for col_name, col_obj in model.columns.items() %}
    {{ col_name }} = Column({{ col_obj.type }}({{ col_obj.maxLength }}),{%- if col_obj.foreign_key %} ForeignKey("{{ col_obj.foreign_key }}"),{%- endif %} nullable={{ col_obj.nullable }},)
    {%- endfor %}

    {%- for rel_name, rel_obj in model.relationships.items() %}
    {{ rel_name }} = relationship("{{ rel_obj.model }}", {% if rel_obj.backref %}backref="{{ rel_obj.backref }}",{% endif %}{% if rel_obj.back_populates %} back_populates="{{ rel_obj.backref }}",{% endif %} uselist={{ rel_obj.uselist }},{% if rel_obj.foreign_keys %} foreign_keys={{ rel_obj.foreign_keys }},{% endif -%})
    {%- endfor %}

    {# }
    {% for hprop, hprop_obj in model.hybrid_properties.items() %}
    {% endfor %}
{ #}
{%- endfor %}

Base.metadata.create_all(engine)
e1 = Employee(name="John", employeeid="123", age=32)
print(e1.name, e1.employeeid, e1.age, e1.store)
s = Store(name="ab", employees=[e1])
print(s.name)
print(s.employees)
print(e1.store)