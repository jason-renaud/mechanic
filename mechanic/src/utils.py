import json
import re

import yaml
import jinja2

SUPPORTED_VARS = ["version", "namespace"]

def deserialize_file(file_path):
    """
    Deserializes a file from either json or yaml and converts it to a dictionary structure to operate on.
    :param oapi_file:
    :return: dictionary representation of the OpenAPI file
    """
    if file_path.endswith(".json"):
        with open(file_path) as f:
            mechanic_obj = json.load(f)
    elif file_path.endswith(".yaml") or file_path.endswith(".yml"):
        with open(file_path) as f:
            mechanic_obj = yaml.load(f)
    else:
        raise SyntaxError("File is not of correct format. Must be either json or yaml (and filename extension must "
                          "be one of those too).")
    return mechanic_obj


def replace_template_var(s, **kwargs):
    return jinja2.Template(s).render(**kwargs)
