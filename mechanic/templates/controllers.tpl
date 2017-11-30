# do not modify - generated code at UTC {{ timestamp }}

from mechanic.base.controllers import MechanicBaseController, MechanicBaseItemController, MechanicBaseCollectionController

{%- for base_controller_path, base_controller_names in base_controllers.items() %}
{%- if base_controller_path != "mechanic.base.controllers" %}
from {{ base_controller_path }} import ({% for name in base_controller_names %}{{ name }}, {% endfor %})
{%- endif %}
{%- endfor %}

{% for path, names in dependent_models.items() -%}
from {{ path }} import ({% for name in names %}{{ name }}, {% endfor %})
{%- endfor %}

{% for path, names in dependent_schemas.items() -%}
from {{ path }} import ({% for name in names %}{{ name }}, {% endfor %})
{%- endfor %}

{% for controller_name, controller in controllers.items() %}
class {{ controller_name }}({{ controller.base_controller_name }}):
    responses = {
        {%- for method_name, method in controller.responses.items() %}
        "{{ method_name }}": {
            "code": {{ method.code }},
            "model": {{ method.model }},
            "schema": {{ method.schema }}
        },
        {%- endfor %}
    }
    requests = {
        {%- for method_name, method in controller.requests.items() %}
        "{{ method_name }}": {
            "model": {{ method.model }},
            "schema": {{ method.schema }}
        },
        {%- endfor %}
    }
{% endfor %}