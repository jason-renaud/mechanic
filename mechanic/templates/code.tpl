# mechanic save - safe to modify below #
from marshmallow import fields
from marshmallow.validate import OneOf, Regexp
from flask import url_for

from mechanic.base.schemas import MechanicBaseModelSchema
from mechanic.base.fields import MechanicEmbeddable

from mechanic.base.models import MechanicBaseModelMixin

def get_uri(context):
    try:
        return str(url_for(context.current_parameters['controller'], resource_id=context.current_parameters['identifier']))
    except Exception:
        return None
# END mechanic save #


# avoid modifying below - generated code at UTC {{ timestamp }} #
{%- for cb in codeblocks %}
    {%- if cb.type == 'table' %}
{{ cb.table_name }} = db.Table('{{ cb.table_name }}',
                                {%- for col_name, col_obj in cb.oapi.columns.items() %}
                        db.Column('{{ col_name }}', db.{{ col_obj.type.title() }}({%- if col_obj.maxLength %}{{ col_obj.maxLength }}{% endif %}),
                                                            {%- if col_obj.foreign_key %} db.ForeignKey('{{ col_obj.foreign_key.key }}',
                                                                {%- if col_obj.foreign_key.ondelete %} ondelete='{{ col_obj.foreign_key.ondelete }}',{%- endif %}
                                                                {%- if col_obj.foreign_key.onupdate %} onupdate='{{ col_obj.foreign_key.onupdate }}',{%- endif %})
                                                            {%- endif %}),
                                {%- endfor %}
                        {% if cb.oapi.schema %}schema='{{ cb.oapi.schema }}',{%- endif %})
    {%- elif cb.type == 'schema' %}
class {{ cb.class_name }}({{ cb.base_class_name }}):
        {%- if cb.oapi.description %}
    """
    {{ cb.oapi.description }}
    """
        {%- endif %}
        {%- for prop_name, prop_obj in cb.oapi.properties.items() %}
            {%- if not prop_obj['x-mechanic-db'] or not prop_obj['x-mechanic-db'].model_only %}
                {%- if prop_obj['x-mechanic-embeddable'] %}
    {{ prop_name }} = MechanicEmbeddable('{{ prop_obj['x-mechanic-embeddable'] }}', deserialize_key='identifier', column=['uri', 'identifier', 'name'])
                {%- else %}
    {{ prop_name }} = fields.{{ prop_obj.type.title() }}({%- if prop_name in cb.oapi.required %}required=True,{% endif %}
                                                 {%- if prop_obj.maxLength %} maxLength={{ prop_obj.maxLength }},{% endif %}
                                                 {%- if prop_obj.readOnly %} load_only={{ prop_obj.readOnly }},{% endif %}
                                                 {%- if prop_obj.writeOnly %} dump_only={{ prop_obj.writeOnly }},{% endif %}
                                                 {%- if prop_obj.enum %} validate=OneOf({{ prop_obj.enum }}),{% endif %}
                                                 {%- if prop_obj.pattern %}validate=Regexp('{{ prop_obj.pattern}}'),{% endif %})
                {%- endif %}
            {%- endif %}
        {%- endfor %}
{# #}
    class Meta:
        fields = ('identifier', 'uri', {%- for prop_name, prop_obj in cb.oapi.properties.items() %} '{{ prop_name }}',{%- endfor %})
        strict = True
        {% if cb.oapi['x-mechanic-model'] -%}model = {{ cb.oapi['x-mechanic-model'] }}{%- endif %}
    {%- elif cb.type == 'model' %}
class {{ cb.class_name }}({{ cb.base_class_name }}, db.Model):
        {%- if cb.oapi.description %}
    """
    {{ cb.oapi.description }}
    """
        {%- endif %}
    __tablename__ = '{%- if cb.oapi['x-mechanic-db'] -%}
                        {{ cb.oapi['x-mechanic-db'].__tablename__ }}
                     {%- endif -%}'
    __table_args__ = ({%- if cb.oapi['x-mechanic-db'] and cb.oapi['x-mechanic-db'].__table_args__.uniqueConstraint -%}
                                    db.UniqueConstraint({%- for item in cb.oapi['x-mechanic-db'].__table_args__.uniqueConstraint %}'{{ item }}', {% endfor %}),
                      {% endif -%}
                                    {'schema': '{%- if cb.oapi['x-mechanic-db'] -%}{{ cb.oapi['x-mechanic-db'].__table_args__.schema }}{%- endif -%}'})
    {# #}
    controller = db.Column(db.String, default='{{ cb.oapi['x-mechanic-controller'] }}')
    uri = db.Column(db.String, default=get_uri)
        {%- for prop_name, prop_obj in cb.oapi.properties.items() %}
            {%- if prop_obj['x-mechanic-db'] %}
                {%- if prop_obj['x-mechanic-db'].column %}
    {{ prop_name }} = db.Column(db.{{ prop_obj.type.title() }}({%- if prop_obj.maxLength %}{{ prop_obj.maxLength }}{% endif %}),
                                {%- if prop_obj['x-mechanic-db'].column.nullable %} nullable={{ prop_obj['x-mechanic-db'].column.nullable }},{%- endif %}
                                {%- if prop_obj['x-mechanic-db'].column.default %} default={{ prop_obj['x-mechanic-db'].column.default }},{%- endif %}
                                {%- if prop_obj['x-mechanic-db'].column.server_default %} server_default={{ prop_obj['x-mechanic-db'].column.server_default }},{%- endif %})

                {%- elif prop_obj['x-mechanic-db'].foreign_key %}
    {{ prop_name }} = db.Column(db.String(36), db.ForeignKey('{{ prop_obj['x-mechanic-db'].foreign_key.key }}'),
                                                                {%- if prop_obj['x-mechanic-db'].foreign_key.primary_key %} primary_key={{ prop_obj['x-mechanic-db'].foreign_key.primary_key }}{% endif %})
                {%- elif prop_obj['x-mechanic-db'].relationship %}
    {{ prop_name }} = db.relationship('{{ prop_obj['x-mechanic-db'].relationship.model }}',
                                        {%- if prop_obj['x-mechanic-db'].relationship.backref %} backref='{{ prop_obj['x-mechanic-db'].relationship.backref }}',{%- endif %}
                                        {%- if prop_obj['x-mechanic-db'].relationship.back_populates %} back_populates='{{ prop_obj['x-mechanic-db'].relationship.backref }}',{%- endif %}
                                        {%- if prop_obj['x-mechanic-db'].relationship.uselist != None %} uselist={{ prop_obj['x-mechanic-db'].relationship.uselist }},{% endif %}
                                        {%- if prop_obj['x-mechanic-db'].relationship.foreign_keys %} foreign_keys={{ prop_obj['x-mechanic-db'].relationship.foreign_keys }},{%- endif -%}
                                        {%- if prop_obj['x-mechanic-db'].relationship.secondary %} secondary={{ prop_obj['x-mechanic-db'].relationship.secondary }},{% endif -%})
                {%- endif %}
            {%- endif %}
        {%- endfor %}
    {%- elif cb.type == 'controller' %}
class {{ cb.class_name }}({{ cb.base_class_name }}):
        {%- if cb.oapi.description %}
    """
    {{ cb.oapi.description }}
    """
        {%- endif %}
    responses = {
        {%- for method_attr_name, method_attr in cb.oapi['x-mechanic-controller']['responses'].items() %}
        '{{ method_attr_name }}': {
            'code': {{ method_attr.code }},
            'model': {{ method_attr.model }},
        },
        {%- endfor %}
    }
    requests = {
        {%- for method_attr_name, method_attr in cb.oapi['x-mechanic-controller']['requests'].items() %}
        '{{ method_attr_name }}': {
            'model': {{ method_attr.model }},
        },
        {%- endfor %}
    }
    {%- elif cb.type == 'versions' %}
VERSIONS = {
    {%- for controller in cb.controllers %}
    '{{ controller.class_name }}': {
        {%- if controller.versions %}
            {%- for version_num, version in controller.versions.items() %}
        '{{ version_num }}': {
            'schema': {{ version.schema }}
        },
            {%- endfor %}
        {%- else %}
        '{{ cb.version }}': {
            'schema': {{ controller.schema }}
        },
        {%- endif %}
    },
    {%- endfor %}
}
    {%- endif %}
{# #}
{% endfor %}