# do not modify - generated code at UTC {{ timestamp }}
import uuid

from app import db


def random_uuid():
    return str(uuid.uuid4())

{% for rel_name, rel_obj in data.m2m_relationships.items() %}
{{ rel_name }} = db.Table("{{ rel_name }}",
    {%- for ref in rel_obj.model_refs %}
    db.Column("{{ ref.name }}", db.{{ ref.type }}{% if ref.maxLength %}({{ ref.maxLength }}){% endif %}, db.ForeignKey("{{ ref.fkey }}")),
    {%- endfor %}
    schema="{{ rel_obj.db_schema_name }}"
)
{%- endfor %}

{% for item in data.models %}
class {{ item.class_name }}(db.Model):
    __tablename__ = "{{ item.db_table_name }}"
    __table_args__ = {"schema": "{{ item.db_schema_name }}"}

    identifier = db.Column(db.String(36), primary_key=True, nullable=False, default=random_uuid)
    created = db.Column(db.DateTime)
    last_modified = db.Column(db.DateTime)
    locked = db.Column(db.Boolean, default=False)
    etag = db.Column(db.String(36), default=random_uuid)
    {%- for prop in item.properties %}

    {#- self-referencing one-to-one -#}
    {%- if prop.model_ref == item.path %}
    {{ prop.name }} = db.relationship("{{ prop.model_ref }}", remote_side=[identifier])

    {#- many-to-many -#}
    {%- elif prop.model_ref and prop.rel_type == "m2m" and prop.m2m_db_name %}
    {{ prop.name }} = db.relationship("{{ prop.model_ref }}"{% if prop.backref_name %}, backref=db.backref("{{ prop.backref_name }}"){% endif %}, secondary={{ prop.m2m_db_name }})

    {#- one-to-many -#}
    {%- elif prop.model_ref and prop.type == "array" and prop.rel_type != "m2m" %}
    {{ prop.name }} = db.relationship("{{ prop.model_ref }}"{% if prop.backref_name %}, backref=db.backref("{{ prop.backref_name }}"){% endif %})

    {#- one-to-one -#}
    {%- elif prop.model_ref and prop.type == "object" %}
    {{ prop.name }} = db.relationship("{{ prop.model_ref }}"{% if prop.backref_name %}, backref=db.backref("{{ prop.backref_name }}"){% endif %}, uselist=False)

    {#- regular property -#}
    {%- elif prop.rel_type != "m2m" %}
    {{ prop.name }} = db.Column(db.{{ prop.type }}{% if prop.maxLength %}({{ prop.maxLength }}){% endif %}{% if prop.required == True %}, nullable=False{% endif %}{% if prop.fkey %}, db.ForeignKey("{{ prop.fkey }}"){% endif %})
    {%- endif %}
    {%- endfor %}

{% endfor %}