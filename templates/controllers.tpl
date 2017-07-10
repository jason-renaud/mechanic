# do not modify - generated code at UTC {{ timestamp }}

from werkzeug.exceptions import MethodNotAllowed

from base.controllers import BaseCollectionController, BaseController
from {{ models_path }} import {% for model in models %}{{ model }}Model{{ "," if not loop.last }} {% endfor %}
from {{ schemas_path }} import {% for model in models %}{{ model }}Schema{{ "," if not loop.last }} {% endfor %}
from {{ services_path }} import {% for model in models %}{{ model }}Service{{ "," if not loop.last }} {% endfor %}


# All supported HTTP methods are already implemented in Base(Collection)Controller
{%- for path in data %}
class {{ path.controller_name }}Controller(Base{% if "Collection" in path.controller_name %}Collection{% endif %}Controller):
    service_class = {{ path.resource_name }}Service
    responses = {
        {%- for method in path.methods %}
        {%- if method.supported %}
        "{{ method.name }}": {
            "code": {{ method.success_response_code }},
            "model": {% if method.response_model %}{{ method.response_model }}Model{% else %}None{% endif %},
            "schema": {% if method.response_model %}{{ method.response_model }}Schema{% else %}None{% endif %},
            "query_params": [
                {%- for param in  method.query_params %}
                "{{ param }}"{{ "," if not loop.last }}
                {%- endfor %}
            ]
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