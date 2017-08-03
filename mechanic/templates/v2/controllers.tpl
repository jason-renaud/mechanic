# do not modify - generated code at UTC {{ timestamp }}

from werkzeug.exceptions import MethodNotAllowed
{% for package in data.base_controllers_to_import.keys() %}
from {{ package }} import {% for item in data.base_controllers_to_import[package]["modules"] %}{{ item }}{{ ", " if not loop.last }}{% endfor %}
{%- endfor %}
{%- for package in data.models_to_import.keys() %}
from {{ package }} import {% for item in data.models_to_import[package]["modules"] %}{{ item }}{{ ", " if not loop.last }}{% endfor %}
{%- endfor %}
{%- for package in data.schemas_to_import.keys() %}
from {{ package }} import {% for item in data.schemas_to_import[package]["modules"] %}{{ item }}{{ ", " if not loop.last }}{% endfor %}
{%- endfor %}
{%- for package in data.services_to_import.keys() %}
from {{ package }} import {% for item in data.services_to_import[package]["modules"] %}{{ item }}{{ ", " if not loop.last }}{% endfor %}
{%- endfor %}


# All supported HTTP methods are already implemented in Base(Collection|Command)Controller
{%- for controller in data.controllers %}
class {{ controller.class_name }}({{ controller.base_controller }}):
    service_class = {{ controller.service_class }}
    {%- if controller.controller_type == "COMMAND" %}
    # the url of the server to retrieve the resource from
    resource_host_url = "{{ controller.resource_host_url }}"
    # the uri of the base resource
    resource_uri = "{{ controller.resource_uri }}"
    {%- endif %}
    responses = {
        {%- for method in controller.methods %}
        {%- if method.supported %}
        "{{ method.name }}": {
            "code": {{ method.response.success_code }},
            "model": {% if method.response.model != "" %}{{ method.response.model }}{% else %}None{% endif %},
            "schema": {% if method.response.schema != "" %}{{ method.response.schema }}{% else %}None{% endif %},
            "async": {{ method.async }}
        }{{ "," if not loop.last }}
        {%- endif %}
        {%- endfor %}
    }
    requests = {
        {%- for method in controller.methods %}
        {%- if method.supported %}
        "{{ method.name }}": {
            "model": {% if method.request.model != "" %}{{ method.request.model }}{% else %}None{% endif %},
            "schema": {% if method.request.schema != "" %}{{ method.request.schema }}{% else %}None{% endif %},
            "query_params": [
                {%- for param in  method.query_params %}
                "{{ param }}"{{ "," if not loop.last }}
                {%- endfor %}]
        }{{ "," if not loop.last }}
        {%- endif %}
        {%- endfor %}
    }

    {%- for method in controller.methods %}
    {%- if not method.supported %}

    def {{ method.name }}(self):
        raise MethodNotAllowed()
    {%- endif %}
    {%- endfor %}

{% endfor %}
