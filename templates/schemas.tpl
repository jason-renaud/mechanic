# do not modify - generated code at UTC {{ timestamp }}

from marshmallow import fields

from base.schemas import BaseSchema
from {{ models_path }} import {% for item in models %}{{ item }}Model{{ ", " if not loop.last }}{% endfor %}

{% for item in data %}
{%- if item.table_name %}
class {{ item.model_name }}Schema(BaseSchema):
    {%- for prop in item.properties %}
    {%- if prop.type == "array" and prop.ref %}
    {{ prop.name }} = fields.Nested("{{ prop.ref }}Schema", many=True)
    {%- endif %}
    {%- endfor %}

    class Meta:
        model = {{ item.model_name }}Model
        strict = True
{%- else %}

class {{ item.model_name }}Schema(BaseSchema):
    {%- for prop in item.properties %}
    {{ prop.name }} = fields.{{ prop.type }}()
    {%- endfor %}

    class Meta:
        fields = ({% for prop in item.properties %}"{{ prop.name }}"{{ ", " if not loop.last }}{% endfor %})
        strict = True
{%- endif %}
{% endfor %}