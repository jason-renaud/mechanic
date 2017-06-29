# do not modify - generated code at UTC {{ timestamp }}

from werkzeug.exceptions import MethodNotAllowed

from base.controllers import BaseCollectionController, BaseController
from {{ models_path }} import {% for model in  models%}{{ model }}Model{{ "," if not loop.last }} {% endfor %}
from {{ schemas_path }} import {% for model in models %}{{ model }}Schema{{ "," if not loop.last }} {% endfor %}
from {{ services_path }} import {% for model in models %}{{ model }}Service{{ "," if not loop.last }} {% endfor %}


# All supported HTTP methods are already implemented in Base(Collection)Controller
{%- for path in data %}
class {{ path.controller_name }}(Base{% if "Collection" in path.controller_name %}Collection{% endif %}Controller):
    model = {{ path.model_name }}Model
    schema = {{ path.model_name }}Schema
    service_class = {{ path.model_name }}Service

    {%- for method in path.methods %}
    {%- if method.supported == False %}

    def {{ method.name }}(self):
        raise MethodNotAllowed()
    {%- endif %}
    {%- endfor %}

{% endfor %}