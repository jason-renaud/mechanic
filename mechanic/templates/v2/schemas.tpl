# do not modify - generated code at UTC {{ timestamp }}
import re

from werkzeug.routing import BuildError
from marshmallow import fields, validate, post_dump
from flask import url_for
from flask_marshmallow.fields import URLFor
from base.schemas import BaseSchema
{% for package in data.models_to_import.keys() %}
from {{ package }} import {% for item in data.models_to_import[package] %}{{ item }}{{ ", " if not loop.last }}{% endfor %}
{%- endfor %}

{% for item in data.schemas %}
{%- if item.model %}
class {{ item.class_name }}(BaseSchema):
    uri = fields.Method("uri_or_none")

    {%- for prop in item.additional_fields %}
    {%- if prop.schema_ref %}
    {{ prop.name }} = fields.Nested("{{ prop.schema_ref }}"{% if prop.type == "array" %}, many=True{% endif %})
    {%- else %}
    {{ prop.name }} = fields.{{ prop.type }}({% if prop.required %}required=True, {% endif %}{% if prop.maxLength %}max_length={{ prop.maxLength }}, {% endif %}{% if prop.enum_validate %}validate=validate.OneOf({{ prop.enum_validate }}), {% endif %}{% if prop.regex_validate %}validate=validate.Regexp(r"{{ prop.regex_validate }}"){% endif %})
    {%- endif %}
    {%- endfor %}


    # attempts to build a uri for the object, if there is no controller, return None
    def uri_or_none(self, obj):
        try:
            return url_for("{{ item.class_name.replace("Schema", "Controller").lower() }}", resource_id=obj.identifier)
        except BuildError:
            return None

    class Meta:
        model = {{ item.model }}
        strict = True
{% else %}
class {{ item.class_name }}(BaseSchema):
    {%- for prop in item.additional_fields %}
    {{ prop.name }} = fields.{{ prop.type }}({% if prop.required %}required=True, {% endif %}{% if prop.maxLength %}validate=[validate.Length(min=0, max={{ prop.maxLength }})]{% endif %})
    {%- endfor %}

    class Meta:
        strict = True
{% endif %}
{% endfor %}