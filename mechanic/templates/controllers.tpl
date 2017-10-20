# do not modify - generated code at UTC {{ timestamp }}
from app import api
from app import config
{%- for key, val in base_controllers.items() %}
from {{ key }} import ({% for item in val %}{{ item}}{{ ", " if not loop.last }}{% endfor %})
{%- endfor %}
from models import ({% for model in models %}{{ model }}{{ ", " if not loop.last }}{% endfor %})
from schemas import ({% for schema in schemas %}{{ schema }}{{ ", " if not loop.last }}{% endfor %})

{% for controller_name, controller in data.items() %}
class {{ controller_name }}({{ controller.base_controller }}):
    responses = {
        {%- for method_name, method in controller.methods.items() %}
        {%- if method.supported %}
        "{{ method_name }}": {
            "code": {{ method.response.success_code }},
            "model": {% if method.response.model in models %}{{ method.response.model or None }}{% else %}None{% endif %},
            "schema": {{ method.response.mschema or None }}
        }{{ "," if not loop.last }}
        {%- endif %}
        {%- endfor %}
    }
    requests = {
        {%- for method_name, method in controller.methods.items() %}
        {%- if method.supported %}
        "{{ method_name }}": {
            "model": {% if method.request.model in models %}{{ method.request.model or None }}{% else %}None{% endif %},
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
