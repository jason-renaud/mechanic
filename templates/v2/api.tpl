# do not modify - generated code at UTC {{ timestamp }}


def init_api(api):
    # imports need to be inside this method call to ensure models and controller objects are properly created in the
    # 'api' object
    from {{ data.config_module }} import {{ data.config_name }}
    {%- for key, value in data.items() %}
    {%- if key != "config_module" and key != "config_name" %}
    from {{ key }} import {% for item in value %}{{ item.class_name }}{{ ", " if not loop.last }}{% endfor %}
    {%- endif %}
    {%- endfor %}
{% for key, value in data.items() %}
    {%- if key != "config_module" and key != "config_name" %}

        {%- for item in value %}
    api.add_resource({{ item.class_name }}, config["BASE_API_PATH"] + "{{ item.uri }}")
        {%- endfor %}
    {%- endif %}
    {%- endfor %}