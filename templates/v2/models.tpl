# do not modify - generated code at UTC {{ timestamp }}
import uuid

from app import db

def random_uuid():
    return str(uuid.uuid4())

{% for item in data.models %}
class {{ item.class_name }}(db.Model):
    __tablename__ = "{{ item.db_table_name }}"
    __table_args__ = {"schema": "{{ item.db_schema_name }}"}

    identifier = db.Column(db.String(36), primary_key=True, nullable=False, default=random_uuid)
    {%- for prop in item.properties %}
    {%- if prop.model_ref and prop.type == "array" %}
    {{ prop.name }} = db.relationship("{{ prop.model_ref.split(":")[1] }}", backref=db.backref("{{ item.resource_name.lower() }}"))
    {% elif prop.model_ref and prop.type == "object" %}
    {{ prop.name }} = db.relationship("{{ prop.model_ref.split(":")[1] }}", backref=db.backref("{{ item.resource_name.lower() }}"), uselist=False)
    {%- else %}
    {{ prop.name }} = db.Column(db.{{ prop.type }}{% if prop.maxLength %}({{ prop.maxLength }}){% endif %}{% if prop.required == True %}, nullable=False{% endif %}{% if prop.fkey %}, db.ForeignKey("{{ prop.fkey }}"){% endif %})
    {%- endif %}
    {%- endfor %}

{% endfor %}