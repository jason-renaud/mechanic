# do not modify - generated code at UTC {{ timestamp }}


def init_api(api):
    # imports need to be inside this method call to ensure models and controller objects are properly created in the
    # 'api' object
    from app import config
    {% for tag in data -%}
    from controllers.{{ tag.name }}.controllers import {% for controller in tag.controllers %}{{ controller.controller_name }}Controller{{ "," if not loop.last }} {% endfor %}
    {% endfor %}
    {% for tag in data -%}
    # controllers for {{ tag.name }}
    {% for controller in tag.controllers -%}
    api.add_resource({{ controller.controller_name }}Controller, config["BASE_API_PATH"] + "{{ controller.uri }}")
    {% endfor -%}
    {%- endfor %}
