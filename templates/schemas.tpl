# do not modify - generated code at UTC {{ timestamp }}

from marshmallow import fields

from base.schemas import BaseSchema
from {{ models_path }} import {% for item in data %}{{ item.model_name }}Model{{ "," if not loop.last }} {% endfor %}

{% for item in data %}
class {{ item.model_name }}Schema(BaseSchema):
    {%- for prop in item.properties %}
    {%- if prop.type == "array" and prop.ref %}
    {{ prop.name }} = fields.Nested("{{ prop.ref }}Schema", many=True)
    {%- endif %}
    {%- endfor %}

    class Meta:
        model = {{ item.model_name }}Model
        strict = True

{% endfor %}