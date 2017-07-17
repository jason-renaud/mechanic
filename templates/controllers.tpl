# do not modify - generated code at UTC {{ timestamp }}

from werkzeug.exceptions import MethodNotAllowed

from base.controllers import BaseCollectionController, BaseCommandController, BaseController
from {{ models_path }} import {% for model in models %}{{ model }}Model{{ "," if not loop.last }} {% endfor %}
from {{ schemas_path }} import {% for model in models %}{{ model }}Schema{{ "," if not loop.last }} {% endfor %}
from {{ services_path }} import {% for service in services %}{{ service }}Service{{ "," if not loop.last }} {% endfor %}


# All supported HTTP methods are already implemented in Base(Collection|Command)Controller
{%- for path in data %}
class {{ path.controller_name }}Controller(Base{% if "Collection" in path.controller_name %}Collection{% elif path.is_command_api %}Command{% endif %}Controller):
    service_class = {% if path.service_name %}{{path.service_name}}Service{% else %}{{ path.resource_name }}Service{% endif %}
    operand_host = "{{ path.operand_host }}"
    operand_resource_uri = "{{ path.operand_resource_uri }}"
    responses = {
        {%- for method in path.methods %}
        {%- if method.supported %}
        "{{ method.name }}": {
            "code": {{ method.success_response_code }},
            "response_model": {% if method.response_model %}{{ method.response_model }}Model{% else %}None{% endif %},
            "task_schema": {% if method.response_model %}{{ method.response_model }}Schema{% else %}None{% endif %},
            "request_schema": {% if method.request_model %}{{ method.request_model }}Schema{% else %}None{% endif %},
            "query_params": [
                {%- for param in  method.query_params %}
                "{{ param }}"{{ "," if not loop.last }}
                {%- endfor %}
            ],
            "async": {{ method.async }}
        }{{ "," if not loop.last }}
        {%- endif %}
        {%- endfor %}
    }

    {%- for method in path.methods %}
    {%- if method.supported == False %}

    def {{ method.name }}(self):
        raise MethodNotAllowed()
    {%- endif %}
    {%- endfor %}

{% endfor %}