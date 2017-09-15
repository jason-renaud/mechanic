# do not modify - generated code at UTC {{ timestamp }}

from marshmallow import fields
from marshmallow_sqlalchemy import field_for

from base.schemas import BaseSchema, BaseModelSchema
from base.fields import OneOf
{% if data.items() -%}
from models import {% for schema_name, schema in data.items() %}{% if schema.model %}{{ schema.model }}{% if not loop.last %}, {% endif %}{% endif %}{% endfor %}
{%- endif %}
{% for schema_name, schema in data.items() %}
    {%- if schema.model %}
{# #}
class {{ schema_name }}(BaseModelSchema):
        {%- for prop_name, prop in schema.properties.items() %}
            {%- if prop.nested %}
    {{ prop_name }} = fields.Nested("{{ prop.nested }}", many={{ prop.many }}, required={{ prop.required }})
            {%- elif prop.oneOf %}

    {{ prop_name }} = OneOf(field_types=[
                                        {%- for item in prop.oneOf -%}
                                            {%- if item.nested %}
                                    fields.Nested("{{ item.nested }}", exclude=({%- for exc in item.exclude %}"{{ exc }}",{%- endfor %})),
                                            {%- else %}
                                    fields.{{ item.type }}(required={{ prop.required }}, {%- if prop.maxLength %}{{ prop.maxLength }}{%- endif %}),
                                            {%- endif %}
                                        {%- endfor %}
                                ], required={{ prop.required }})

    {%- for item in prop.oneOf %}
    {{ item.attr_name }} = field_for({{ schema.model }}, "{{ item.attr_name }}", dump_only=True, load_only=True)
    {%- endfor %}
{# #}
            {%- endif %}

        {%- endfor %}

    class Meta(BaseModelSchema.Meta):
        model = {{ schema.model }}
    {%- else %}
{# #}
{# #}
class {{ schema_name }}(BaseSchema):
    pass
    {#
    {%- for prop_name, prop in schema.properties.items() %}
        {%- if prop.references %}
            {%- for ref in  prop.references.oneOf %}
                {%- for key, val in ref.items() %}
    {{ prop_name }} = Expandable(
                        nested_schema=fields.Nested("{{ key }}"{% if val == "MANY" %}, many=True{% endif %}, exclude=("{{ key }}",)),
                        nested_model={{ prop.model_ref }})
                {% endfor %}
            {% endfor %}
        {%- else %}

    {{ prop_name }} = fields.{{ prop.type }}({% if prop.required %}required=True, {% endif %}{% if prop.maxLength %}max_length={{ prop.maxLength }}, {% endif %}{% if prop.enum_validate %}validate=validate.OneOf({{ prop.enum_validate }}), {% endif %}{% if prop.regex_validate %}validate=validate.Regexp(r"{{ prop.regex_validate }}"){% endif %})

        {%- endif %}
    {%- endfor %}

    class Meta:
        strict = True
    #}
    {%- endif %}
{% endfor %}