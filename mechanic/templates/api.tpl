# do not modify - generated code at UTC {{ timestamp }}


def init_api(api):
    # imports need to be inside this method call to ensure models and controller objects are properly created in the
    # 'api' object
    from app import config
    from controllers import {% for controller_name, controller in data.items() %}{{ controller_name }}{{ ", " if not loop.last }}{% endfor %}

    {%- for controller_name, controller in data.items() %}
    api.add_resource({{ controller_name }}, config["BASE_API_PATH"] + "{{ controller.uri.replace("{id}", "<string:resource_id>") }}")
    {%- endfor %}