import os

default_options = {
    "APP_NAME": "app",
    "OPENAPI": None,
    "MODELS_PATH": "models/{{namespace}}.py",
    "SCHEMAS_PATH": "schemas/{{namespace}}.py",
    "CONTROLLERS_PATH": "controllers/{{namespace}}.py",
    "MODELS_NAME_PATTERN": "{{resource}}Model",
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

    with open(path, "r") as f:
        content = f.readlines()

    options = dict()
    for line in content:
        if line.split():
            options[line.split()[0]] = "".join(line.split(maxsplit=1)[1].strip())

    print()
    print(options)
    return options