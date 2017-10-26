import os
import copy
import json

import yaml

default_options = {
    "APP_NAME": "app",
    "OPENAPI": None,
    "MODELS_PATH": "models/{{namespace}}.py",
    "SCHEMAS_PATH": "schemas/{{namespace}}.py",
    "CONTROLLERS_PATH": "controllers/{{namespace}}.py",
    "MODELS_NAME_PATTERN": "{{resource}}",
    "SCHEMAS_NAME_PATTERN": "{{resource}}Schema",
    "CONTROLLERS_NAME_PATTERN": "{{resource}}{{controller_type}}Controller",
    "BASE_API_PATH": "/api",
    "BASE_ITEM_CONTROLLER": "mechanic.base.controllers.BaseItemController",
    "BASE_COLLECTION_CONTROLLER": "mechanic.base.controllers.BaseCollectionController",
    "BASE_CONTROLLER": "mechanic.base.controllers.BaseController",
    "DEFAULT_NAMESPACE": "default",
    "INCLUDE": None,
    "OVERRIDE_BASE_CONTROLLER": None,
    "OVERRIDE_BASE_MODEL": None,
    "OVERRIDE_BASE_SCHEMA": None,
    "OVERRIDE_TABLE_NAME": None,
    "OVERRIDE_DB_SCHEMA_NAME": None
}


def read_mechanicfile(file_path):
    path = os.path.expanduser(file_path)
    custom_options = dict()

    with open(path, "r") as f:
        if file_path.endswith(".json"):
            custom_options = json.load(f)
        elif file_path.endswith(".yaml") or file_path.endswith(".yml"):
            custom_options = yaml.load(f)
        else:
            raise SyntaxError("mechanic file is not of correct format. Must either be json or yaml")

    options = copy.deepcopy(default_options)
    for key, val in custom_options.items():
        options[key] = val

    return options
