# do not modify - generated code at UTC {{ timestamp }}
import uuid

from werkzeug.routing import BuildError
from flask import url_for
from sqlalchemy.exc import DataError
from sqlalchemy.ext.hybrid import hybrid_property

from app import db


def random_uuid():
    return str(uuid.uuid4())


def get_uri(context):
    try:
        return str(url_for(context.current_parameters["controller"], resource_id=context.current_parameters["identifier"]))
    except Exception:
        return None

{%- for many_to_many_name, many_to_many in data.many_to_many_models.items() %}
{{ many_to_many_name }} = db.Table("{{ many_to_many_name }}",
    {%- for ref in many_to_many.models %}
    db.Column("{{ ref.name }}", db.{{ ref.type }}{% if ref.maxLength %}({{ ref.maxLength }}){% endif %}, db.ForeignKey("{{ ref.fkey }}")),
    {%- endfor %}
    schema="{{ many_to_many.namespace }}"
)
{%- endfor %}

{% for model_name, model in data.models.items() %}
class {{ model_name }}(db.Model):
    __tablename__ = "{{ model.db_table_name }}"
    __table_args__ = {"schema": "{{ model.namespace }}"}

    identifier = db.Column(db.String(36), primary_key=True, nullable=False, default=random_uuid)
    created = db.Column(db.DateTime)
    last_modified = db.Column(db.DateTime)
    etag = db.Column(db.String(36), default=random_uuid)
    controller = db.Column(db.String, default="{{ model.resource.lower() }}itemcontroller")
    uri = db.Column(db.String, default=get_uri, onupdate=get_uri)

    {%- if fkeys.model_name %}
        {%- for fkey_name, fkey in fkeys.model_name.items() %}
    {{ fkey_name }} = db.Column(db.{{ fkey.type }}({%- if fkey.maxLength %}{{ fkey.maxLength }}{% endif %}, db.ForeignKey("{{ fkey.foreign_key }}")
        {%- endfor %}
    {%- endif %}
{# #}
    {%- for prop_name, prop in model.properties.items() %}
        {%- if not prop.reference and not prop.oneOf and prop.type %}
        {#- these are normal properties of native data types #}
    {{ prop_name }} = db.Column(db.{{ prop.type }}
                                {%- if prop.maxLength %}({{ prop.maxLength }}){% endif %}
                                {%- if prop.required == True %}, nullable=False{% endif %}
                                {%- if prop.foreign_key %}, db.ForeignKey("{{ prop.foreign_key }}"){%- endif %})
        {%- elif prop.reference %}
            {#- these are properties with references #}
    {{ prop_name }} = db.relationship("{{ prop.reference.model }}"
                                        {%- if prop.reference.backref %}, backref=db.backref("{{ prop.reference.backref }}"){%- endif %}
                                        {%- if prop.reference.back_populates and prop.reference.model != model_name %}, back_populates="{{ prop.reference.back_populates }}"{%- endif -%}
                                        , uselist={{ prop.reference.uselist }}
                                        {%- if prop.reference.remote_side %}, remote_side={{ prop.reference.remote_side }}{%- endif %}
                                        {%- if prop.reference.foreign_keys %}, foreign_keys="{{ prop.reference.foreign_keys }}"{% endif %})
        {%- endif %}
        {%- for item in prop.oneOf %}
            {%- if item.reference %}
    {{ item.attr_name }} = db.relationship("{{ item.reference.model }}"
                                        {%- if item.reference.backref %}, backref=db.backref("{{ item.reference.backref }}"){%- endif %}
                                        {%- if item.reference.back_populates and item.reference and item.reference.model != model_name %}, back_populates="{{ item.reference.back_populates }}"{%- endif -%}
                                        , uselist={{ item.reference.uselist }})
            {%- else %}
    {{ item.attr_name }} = db.Column(db.{{ item.type }}
                                {%- if item.maxLength %}({{ item.maxLength }}){% endif %}
                                {%- if item.required == True %}, nullable=False{% endif %}
                                {%- if item.foreign_key %}, db.ForeignKey("{{ item.foreign_key }}"){%- endif %})
            {%- endif %}
        {%- endfor %}

        {%- if prop.oneOf %}

    @hybrid_property
    def {{ prop_name }}(self):
        return {% for item in prop.oneOf -%}
                {%- if item.reference -%}
                self.{{ item.attr_name }}{%- if not loop.last %} or {% endif %}
                {%- else -%}
                self.{{ item.attr_name }}{%- if not loop.last %} or {% endif %}
                {%- endif -%}
            {%- endfor %}

    @{{ prop_name }}.setter
    def {{ prop_name }}(self, val):
            {%- for item in prop.oneOf %}
                {%- if item.reference %}
        {% if loop.first -%}if{%- else %}elif {%- endif %} isinstance(val, {{ item.reference.model }}):
            self.{{ item.attr_name }} = val
                {%- else %}
        {% if loop.first -%}if{%- else %}elif {%- endif %} isinstance(val, {{ item.pytype }}):
            self.{{ item.attr_name }} = val
                {%- endif %}
            {%- endfor %}
        else:
            raise DataError("Attribute is not of one of the possible types.", None, None)
{# #}
        {%- endif %}
    {%- endfor %}
    {#- properties that have relationships to other models #}
    {%- for rel in model.relationships %}
        {%- if rel.type == "one_to_one" %}
            {%- if rel.model_name %}

            {% endif %}
        {%- endif %}
    {%- endfor %}
{% endfor %}
