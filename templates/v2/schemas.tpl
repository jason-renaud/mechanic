# do not modify - generated code at UTC {{ timestamp }}

from marshmallow import fields

from base.schemas import BaseSchema
{% for package in data.models_to_import.keys() %}
from {{ package }} import {% for item in data.models_to_import[package] %}{{ item }}{{ ", " if not loop.last }}{% endfor %}
{%- endfor %}

{% for item in data.schemas %}
class {{ item.class_name }}(BaseSchema):
    {%- for prop in item.additional_fields %}
    {%- if prop.schema_ref %}
    {{ prop.name }} = fields.Nested("{{ prop.schema_ref }}"{% if prop.type == "array" %}, many=True{% endif %})
    {%- else %}
    {{ prop.name }} = fields.{{ prop.type }}()
    {%- endif %}
    {%- endfor %}

    class Meta:
        model = {{ item.model }}
        strict = True

{% endfor %}