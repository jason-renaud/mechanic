# do not modify - generated code at UTC {{ timestamp }}
from marshmallow import fields
from marshmallow.validate import OneOf, Regexp

from {{ app_name }} import db
{% for path, names in dependent_models.items() -%}
from {{ path }} import ({% for name in names %}{{ name }}, {% endfor %})
{%- endfor %}
from mechanic.base.schemas import MechanicBaseModelSchema, MechanicBaseSchema
from mechanic.base.fields import MechanicEmbeddable

{%- for base_schema_path, base_schema_names in base_schemas.items() %}
{%- if base_schema_path != "mechanic.base.schemas" %}
from {{ base_schema_path }} import ({% for name in base_schema_names %}{{ name }}, {% endfor %})
{%- endif %}
{%- endfor %}

{% for schema_name, schema in schemas.items() %}
class {{ schema_name }}({{ schema.base_schema_name }}):
    {%- if schema.comment %}
    """
    {{ schema.comment }}
    """
    {%- endif -%}
    {#- Model schemas -#}
    {%- if schema.model %}
        {%- for prop_name, embed_schema in schema.embeddable.items() %}
    {{ prop_name }} = MechanicEmbeddable("{{ embed_schema }}", deserialize_key="identifier", column=["uri", "identifier", "name"])
        {%- endfor %}
        {%- for prop_name, nested_schema in schema.nested.items() %}
    {{ prop_name }} = fields.Nested("{{ nested_schema.schema }}", many={{ nested_schema.many }})
        {%- endfor %}
        {# additional fields that have things such as enum or pattern #}
        {%- for field_name, field in schema.fields.items() %}
    {{ field_name }} = fields.{{ field.type }}(required={{ field.required }}, maxLength={{ field.maxLength }}, load_only={{ field.load_only }}, dump_only={{ field.dump_only }}, validate={% if field.enum %}OneOf({{ field.enum }}){% elif field.pattern %}Regexp("{{ field.pattern}}"){% else %}None{% endif %})
        {%- endfor %}
{# #}
    class Meta:
        model = {{ schema.model }}
        strict = {{ schema.strict }}

    {# Not model schemas #}
    {%- else -%}
        {%- for field_name, field in schema.fields.items() %}
    {{ field_name }} = fields.{{ field.type }}(required={{ field.required }}, maxLength={{ field.maxLength }}, load_only={{ field.load_only }}, dump_only={{ field.dump_only }}, validate={% if field.enum %}OneOf({{ field.enum }}){% elif field.pattern %}Regexp("{{ field.pattern}}"){% else %}None{% endif %})
        {%- endfor %}
    {%- endif -%}
{% endfor %}