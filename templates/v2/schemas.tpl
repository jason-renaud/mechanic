# do not modify - generated code at UTC {{ timestamp }}
import re

from marshmallow import fields, validate
from base.schemas import BaseModelSchema, BaseSchema
{% for package in data.models_to_import.keys() %}
from {{ package }} import {% for item in data.models_to_import[package] %}{{ item }}{{ ", " if not loop.last }}{% endfor %}
{%- endfor %}

{% for item in data.schemas %}
{%- if item.model %}
class {{ item.class_name }}(BaseModelSchema):
    {%- for prop in item.additional_fields %}
    {%- if prop.schema_ref %}
    {{ prop.name }} = fields.Nested("{{ prop.schema_ref }}"{% if prop.type == "array" %}, many=True{% endif %})
    {%- else %}
    {{ prop.name }} = fields.{{ prop.type }}({% if prop.required %}required=True, {% endif %}{% if prop.maxLength %}max_length={{ prop.maxLength }}, {% endif %}{% if prop.enum_validate %}validate=validate.OneOf({{ prop.enum_validate }}), {% endif %}{% if prop.regex_validate %}validate=validate.Regexp(r"{{ prop.regex_validate }}"){% endif %})
    {%- endif %}
    {%- endfor %}

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