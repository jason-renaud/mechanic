# do not modify - generated code at UTC {{ timestamp }}
from app import api
from app import config
from base.controllers import *
from models import ({% for model in models %}{{ model }}{{ ", " if not loop.last }}{% endfor %})
from schemas import ({% for schema in schemas %}{{ schema }}{{ ", " if not loop.last }}{% endfor %})

{% for controller_name, controller in data.items() %}
class {{ controller_name }}({{ controller.base_controller }}):
    responses = {
        {%- for method_name, method in controller.methods.items() %}
        {%- if method.supported %}
        "{{ method_name }}": {
            "code": {{ method.response.success_code }},
            "model": {{ method.response.model or None }},
            "schema": {{ method.response.mschema or None }}
        }{{ "," if not loop.last }}
        {%- endif %}
        {%- endfor %}
    }
    requests = {
        {%- for method_name, method in controller.methods.items() %}
        {%- if method.supported %}
        "{{ method_name }}": {
            "model": {{ method.request.model or None }},
            "schema": {{ method.request.mschema or None }},
            "query_params": [
                {%- for param in  method.query_params %}
                "{{ param }}"{{ "," if not loop.last }}
                {%- endfor %}
            ]
        }{{ "," if not loop.last }}
        {%- endif %}
        {%- endfor %}
    }

{% endfor %}
