# do not modify - generated code at UTC {{ timestamp }}

from app import db

{% for item in data %}
{%- if item.table_name %}
class {{ item.model_name }}Model(db.Model):
    __tablename__ = "{{ item.table_name }}"
    __table_args__ = {"schema": "{{ db_schema }}"}

    identifier = db.Column(db.String(36), primary_key=True, nullable=False)
    {%- for prop in item.properties %}
    {%- if prop.ref %}
    {{ prop.name }} = db.relationship("{{ prop.ref }}Model", backref=db.backref("{{ item.model_name.lower() }}"))
    {%- else %}
    {{ prop.name }} = db.Column(db.{{ prop.type }}{% if prop.maxLength %}({{ prop.maxLength }}){% endif %}{% if prop.required == True %}, nullable=False{% endif %}{% if prop.foreign_key %}, db.ForeignKey("{{ prop.foreign_key }}"){% endif %})
    {%- endif %}
    {%- endfor %}
{%- endif %}
{% endfor %}