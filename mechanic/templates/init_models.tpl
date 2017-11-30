{%- for k, v in module_paths.items() %}
from {{ k }} import ({% for name in v %}{{ name }}, {% endfor %})
{%- endfor %}