# do not modify - generated code at UTC {{ timestamp }}

import copy

from marshmallow import fields, pre_load, pre_dump, post_dump, post_load, ValidationError
from marshmallow_sqlalchemy import field_for
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from app import db
{% for package, modules in imports.base_schema_imports.items() %}
from {{ package }} import ({% for mod in modules %}{{ mod }},{% endfor %})
{% endfor %}
from base.fields import OneOf
{% if data.items() -%}
from models import ({% for schema_name, schema in data.items() %}{% if schema.model %}{{ schema.model }}{% if not loop.last %}, {% endif %}{% endif %}{% endfor %})
{%- endif %}
{% for schema_name, schema in data.items() %}
    {%- if schema.model %}
{# #}
class {{ schema_name }}({{ schema.base_schema }}):
        {%- for prop_name, prop in schema.properties.items() %}
            {%- if prop.embeddable %}
    {{ prop_name }} = fields.Nested("{{ prop.oneOf[1].nested }}", exclude=({%- for exc in prop.oneOf[1].exclude %}"{{ exc }}",{%- endfor %}), dump_only=True, load_only=True)
    {{ prop.oneOf[1].attr_name }} = field_for({{ schema.model }}, "{{ prop.oneOf[1].attr_name }}", load_only=True)
            {%- elif prop.nested %}
    {{ prop_name }} = fields.Nested("{{ prop.nested }}", many={{ prop.many }}, required={{ prop.required }})
            {%- elif prop.oneOf %}
    {{ prop_name }} = OneOf(field_types=[
                                            {#- otherwise, just have each field type in the order given #}
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

    @pre_load
    def preload(self, value):
        {%- for prop_name, prop in schema.properties.items() %}
            {%- if prop.embeddable %}
        if value.get("{{ prop_name }}") and isinstance(value["{{ prop_name }}"], str):
            self.context["{{ prop_name }}_uri"] = value["{{ prop_name }}"]
        elif value.get("{{ prop_name }}") and isinstance(value["{{ prop_name }}"], dict):
            value["{{ prop.oneOf[1].attr_name }}"] = copy.deepcopy(value["{{ prop_name }}"])
        elif value.get("{{ prop_name }}"):
            raise ValidationError("Invalid data type.", field_names=["{{ prop_name }}"])

        if value.get("{{ prop_name }}"):
            value.pop("{{ prop_name }}")
            {%- endif %}
        {%- endfor %}
        return value

    @post_load
    def postload(self, value):
        {%- for prop_name, prop in schema.properties.items() %}
            {%- if prop.embeddable %}
        if self.context.get("{{ prop_name }}_uri"):
            try:
                obj = {{ prop.oneOf[1].nested.split("Schema", 1)[0] }}Model.query.filter_by(uri=self.context["{{ prop_name }}_uri"]).one()
                value.{{ prop.oneOf[1].attr_name }} = obj
            except (NoResultFound, MultipleResultsFound) as e:
                raise ValidationError("Resource with given uri not found.", field_names=["{{ prop_name }}"])
            {%- endif %}
        {%- endfor %}
        return value

    @pre_dump
    def predump(self, value):
        if hasattr(value, "identifier"):
            ident = value.identifier
        else:
            ident = ""
        self.context[ident] = dict()
        {%- for prop_name, prop in schema.properties.items() %}
            {%- if prop.embeddable %}
        if isinstance(value, {{ schema.model }}):
            if "{{ prop_name }}" in self.context.get("embed", []):
                self.context[ident]["{{ prop_name }}"] = {{ prop.oneOf[1].nested }}().dump(value.{{ prop.oneOf[1].attr_name }}).data
            else:
                self.context[ident]["{{ prop_name }}"] = value.{{ prop.oneOf[0].attr_name }}
            {%- endif %}
        {%- endfor %}
        return value

    @post_dump
    def postdump(self, value):
        ident = value.get("identifier")
        {%- for prop_name, prop in schema.properties.items() %}
            {%- if prop.embeddable %}
                {%- if loop.first %}
        if self.context.get(ident):
                {%- endif %}
            value["{{ prop_name }}"] = self.context[ident].get("{{ prop_name }}")
            {%- endif %}
        {%- endfor %}
        return value

    class Meta({{ schema.base_schema }}.Meta):
        model = {{ schema.model }}
    {%- else %}
{# #}
{# #}
class {{ schema_name }}({{ schema.base_schema }}):
        {%- for prop_name, prop in schema.properties.items() %}
            {%- if prop.references %}
                {%- if prop.oneOf %}
    {{ prop_name }} = OneOf(field_types=[
                                            {#- otherwise, just have each field type in the order given #}
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
                {%- endif %}
            {%- elif prop.type == "list" %}
    {{ prop_name }} = fields.List(fields.{{ prop.items }}, {% if prop.required %}required=True, {% endif %})
            {%- else %}
    {{ prop_name }} = fields.{{ prop.type }}({% if prop.required %}required=True, {% endif %}{% if prop.maxLength %}max_length={{ prop.maxLength }}, {% endif %}{% if prop.enum_validate %}validate=validate.OneOf({{ prop.enum_validate }}), {% endif %}{% if prop.regex_validate %}validate=validate.Regexp(r"{{ prop.regex_validate }}"){% endif %})
            {%- endif %}
        {%- endfor %}

    class Meta({{ schema.base_schema }}.Meta):
        strict = True
    {%- endif %}
{% endfor %}