# do not modify - generated code at UTC {{ timestamp }}


def init_api(api):
    # imports need to be inside this method call to ensure models and controller objects are properly created in the
    # 'api' object
    {%- for controller_path, controller_names in dependent_controllers.items() %}
    from {{ controller_path }} import ({% for name in controller_names %}{{ name}}, {% endfor %})
    {%- endfor %}
    {%- for c in controllers %}
    api.add_resource({{ c.name }}, "{{ base_api_path }}{{ c.uri }}")
    {%- endfor %}