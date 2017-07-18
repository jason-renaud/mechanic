"""mechanic OpenAPI 3.0 file converter

Usage:
    mechanic.py convert <INPUT_FILE> [<OUTPUT_FILE>]
    mechanic.py generate <INPUT_MECHANIC_FILE> <OUTPUT_DIRECTORY> [--skip-starter-files] [--exclude <TYPE>]...
    mechanic.py update-base <OUTPUT_DIRECTORY> [--all --controllers --exceptions --schemas --services --tests]

Arguments:
    INPUT_FILE              OpenAPI 3.0 specification file
    OUTPUT_FILE             File to save mechanic formatted file
    INPUT_MECHANIC_FILE     mechanic formatted file. Typically same file as OUTPUT_FILE from convert command.
    OUTPUT_DIRECTORY        Directory to place generated files.
    TYPE                    Type of resource, can be one of "models", "controllers", "schemas", "apis".

Options:
    -h --help                   Show this screen.
    -v --version                Show version.
    -e --exclude=RESOURCES      One of "models", "controllers", "schemas", "apis". Option can be called multiple times
                                to exclude multiple types.
"""
import os
import sys
import json
import re
import inflect
import pprint
import shutil
import errno
import jinja2
import datetime
import random

from enum import Enum
from docopt import docopt

engine = inflect.engine()
pp = pprint.PrettyPrinter(indent=4)
CONTENT_TYPE = "application/json"
HTTP_METHODS = ["get", "put", "post", "delete", "options", "head", "patch", "trace"]
MECHANIC_SUPPORTED_HTTP_METHODS = ["get", "put", "post", "delete"]
EXTENSION_NAMESPACE = "x-mechanic-namespace"
EXTENSION_EXTERNAL_RESOURCE = "x-mechanic-external-resource"

data_map = {
    "integer": "Integer",
    "string": "String",
}


class ControllerType(Enum):
    COLLECTION_COMMAND = '/(.*)/all/(.*)*', "BaseCommandController"
    COMMAND = '/(.*)/{id}/(.*)', "BaseCommandController"
    ITEM = '/(.*)/{id}*', "BaseController"
    COLLECTION = '/(.*)', "BaseCollectionController"


def parse_resource_name_segments_from_path(path_uri):
    naming = dict()
    n = path_uri.split("/{id}")[0].split("/all/")[0].split("/")[-1]
    naming["resource"] = engine.singular_noun(n.title()) or n.title()
    naming["command"] = ""
    naming["all"] = ""

    if "/{id}/" in path_uri or "/all/" in path_uri:
        naming["command"] = path_uri.split("/{id}/")[-1].split("/all/")[-1]
        naming["all"] = "All" if len(path_uri.split("/all/")) > 1 else ""

    names = dict()
    names["controller"] = naming["resource"].replace("-", "") + naming["command"].title() + naming["all"]

    if naming["command"] != "":
        names["controller"] = names["controller"] + "Command"
    elif not path_uri.endswith("{id}") and not path_uri.endswith("{id}/"):
        names["controller"] = names["controller"] + "Collection"

    names["controller"] = names["controller"] + "Controller"
    names["resource"] = naming["resource"].replace("-", "")
    names["service"] = naming["resource"].replace("-", "") + naming["command"].title() + "Service"
    names["model"] = naming["resource"].replace("-", "") + "Model"
    names["schema"] = naming["resource"].replace("-", "") + "Schema"
    names["command_name"] = naming["resource"].replace("-", "") + naming["command"].title() if naming["command"] != "" else ""
    names["command_parameters"] = naming["resource"].replace("-", "") + naming["command"].title() if naming["command"] != "" else ""
    return names


def follow_reference_link(current_file_json, ref, current_dir=""):
    is_link_in_current_file = True if ref.startswith("#/") else False

    if is_link_in_current_file:
        section = ref.split("/")[-3]
        object_type = ref.split("/")[-2]
        resource_name = ref.split("/")[-1]
        return current_file_json[section][object_type][resource_name], current_dir
    else:
        current_dir = current_dir + "/" if not current_dir.endswith("/") and current_dir is not "" else current_dir
        external_file_path = current_dir + ref.split("#")[0]

        with open(external_file_path) as f:
            external_data = json.load(f)

            object_name = ref.split("#")[-1].split("/")[-1]
        current_dir = "/".join(os.path.abspath(external_file_path).split("/")[:-1])
        return external_data[object_name], current_dir


def parse_response_from_method_responses(current_file_json, response_obj, current_dir, no_model=False):
    response = dict()
    response_2xx = response_obj.get("200") or response_obj.get("201") or response_obj.get("202")

    if response_2xx is None:
        if response_obj.get("204"):
            response["success_code"] = "204"
            response["schema"] = None
            response["model"] = None
            return response
        else:
            raise SyntaxError("No 200, 201, or 202 response is defined for method.")

    schema = response_2xx.get("content").get(CONTENT_TYPE).get("schema")
    schema_ref = schema.get("$ref") or schema.get("items").get("$ref")
    obj, curr_dir = follow_reference_link(current_file_json, schema_ref, current_dir=current_dir)

    if obj.get("title") is None:
        raise SyntaxError("No 'title' defined for the schema.")

    response["schema"] = obj.get("title") + "Schema"
    response["model"] = obj.get("title") + "Model" if not no_model else None

    code = None
    for key in response_obj.keys():
        if key.startswith("2"):
            code = int(key)

    response["success_code"] = code
    return response


def parse_request_from_requestBody(current_file_json, request_obj, current_dir, command=False):
    if request_obj is None:
        return None, {}

    request = dict()

    schema = request_obj.get("content").get(CONTENT_TYPE).get("schema")
    schema_ref = schema.get("$ref") or schema.get("items").get("$ref")
    obj, curr_dir = follow_reference_link(current_file_json, schema_ref, current_dir=current_dir)

    if obj.get("title") is None:
        raise SyntaxError("No 'title' defined for the schema.")
    request["schema"] = obj.get("title") + "Schema" if not command else obj.get("title")
    request["model"] = obj.get("title") + "Model" if not command else ""
    return request, obj


def parse_method_from_path_method(current_file_json, method_name, method_obj, current_dir, command=False):
    method = dict()
    method["name"] = method_name
    method["async"] = False
    method["query_params"] = []
    if method_obj.get("parameters"):
        method["query_params"] = [p["name"] for p in method_obj.get("parameters")]

    method["response"] = parse_response_from_method_responses(current_file_json, method_obj["responses"], current_dir)
    request, props = parse_request_from_requestBody(current_file_json, method_obj.get("requestBody"), current_dir, command=command)
    method["request"] = request or {
        "model": "",
        "schema": ""
    }
    method["supported"] = True
    return method


def build_models_from_reference_link(current_file_json, reference, namespace, models, current_dir):
    """
    Recursive method that returns a list of models from following the reference link paths.

    :param current_file_json:
    :param reference:
    :param namespace:
    :param models:
    :param current_dir:
    :return: list of models
    """
    schema, curr_dir = follow_reference_link(current_file_json, reference, current_dir=current_dir)

    if schema.get("title") is None:
        raise SyntaxError("No 'title' defined for the schema.")

    model = dict()
    model["class_name"] = schema.get("title") + "Model"
    model["resource_name"] = schema.get("title")
    model["db_table_name"] = engine.plural_noun(schema.get("title").replace("-", "").replace("_", "")).lower()
    model["db_schema_name"] = namespace
    model["namespace"] = namespace
    model["properties"] = []

    if schema.get("properties") is None:
        raise SyntaxError(
            "mechanic only supports schema 'properties' being defined at the top level of the object. "
            "I.e., properties objects embedded within allOf, anyOf, etc. is not supported.")
    for prop in schema["properties"].items():
        new_prop = dict()
        new_prop["name"] = prop[0].replace("-", "_")
        new_prop["type"] = data_map.get(prop[1]["type"]) or prop[1].get("type")
        new_prop["required"] = prop[0] in schema.get("required", [])
        new_prop["maxLength"] = prop[1].get("maxLength")

        property_object = prop[1]
        if property_object.get("type") == "array" and property_object.get("items", {}).get(
                "type") == "string":
            # We want to leave this out of the model definition, this is a list of items which would not be stored
            # in the DB. Therefore, don't do anything here.
            pass
        else:
            # First, see if there is a direct reference
            ref = property_object.get("$ref")
            if ref is not None:
                schema_ref, curr_dir = follow_reference_link(current_file_json, ref, current_dir=curr_dir)
                new_prop["model_ref"] = schema_ref.get("title") + "Model"

            # Next, see if there is an array of references
            ref = property_object.get("items", {}).get("$ref")
            if ref is not None:
                schema_ref, curr_dir = follow_reference_link(current_file_json, ref, current_dir=curr_dir)
                new_prop["model_ref"] = schema_ref.get("title") + "Model"

                # create model from nested references
                if schema_ref is not None:
                    build_models_from_reference_link(current_file_json, ref, namespace, models, curr_dir)

            model["properties"].append(new_prop)
    models.append(model)
    return models


def parse_response_models_from_path_method(current_file_json, method_obj, namespace, current_dir):
    response_obj = method_obj["responses"]
    response_2xx = response_obj.get("200") or response_obj.get("201") or response_obj.get("202")
    models = []

    if response_2xx is None:
        if response_obj.get("204"):
            return models
        else:
            raise SyntaxError("No 200, 201, or 202 response is defined for method.")

    schema = response_2xx.get("content").get(CONTENT_TYPE).get("schema")
    schema_ref = schema.get("$ref") or schema.get("items").get("$ref")

    models = build_models_from_reference_link(current_file_json, schema_ref, namespace, [], current_dir)
    return models


def parse_schemas_from_path_method(current_file_json, method_obj, namespace, current_dir, command=False):
    schemas = []
    response_schemas = parse_response_models_from_path_method(current_file_json, method_obj, namespace, current_dir)

    for item in response_schemas:
        schema = dict()
        schema["class_name"] = item["resource_name"] + "Schema"
        schema["model"] = item["class_name"]
        schema["namespace"] = namespace

        # this is populated at the end, when relationships are configured between resources
        schema["additional_fields"] = []

        if not any(item["class_name"] == schema["class_name"] for item in schemas):
            schemas.append(schema)

    request_schema, req_props = parse_request_from_requestBody(current_file_json, method_obj.get("requestBody"),
                                                               current_dir, command=command)

    if request_schema is not None:
        req_schema = dict()
        req_schema["class_name"] = request_schema["schema"]
        req_schema["model"] = request_schema["model"] if not command else None
        req_schema["namespace"] = namespace

        # this is also populated at the end for nested schemas, when relationships are configured between resources
        req_schema["additional_fields"] = []
        if command:
            for prop in req_props["properties"].items():
                req_schema["additional_fields"].append({
                    "name": prop[0],
                    "type": data_map.get(prop[1]["type"]) or prop[1].get("type"),
                    "required": prop[0] in req_props["required"]
                })

        if not any(item["class_name"] == req_schema["class_name"] for item in schemas):
            schemas.append(req_schema)

    return schemas


def build_controller_models_schemas_from_path(current_file_json, path_uri, path_obj, current_dir):
    controller = dict()
    names = parse_resource_name_segments_from_path(path_uri)
    controller["class_name"] = names["controller"]
    controller["service_class"] = names["service"]
    is_command = False
    models = []
    schemas = []

    namespace = path_obj.get(EXTENSION_NAMESPACE)
    if namespace is None:
        raise SyntaxError("Each path object must have x-mechanic-namespace defined.")

    if re.fullmatch(ControllerType.COLLECTION_COMMAND.value[0], path_uri):
        controller_type = ControllerType.COLLECTION_COMMAND
        is_command = True
    elif re.fullmatch(ControllerType.COMMAND.value[0], path_uri):
        controller_type = ControllerType.COMMAND
        is_command = True
    elif re.fullmatch(ControllerType.ITEM.value[0], path_uri):
        controller_type = ControllerType.ITEM
    elif re.fullmatch(ControllerType.COLLECTION.value[0], path_uri):
        controller_type = ControllerType.COLLECTION
    else:
        raise SyntaxError("path uri does not match proper uri formatting. See mechanic documentation for details")

    controller["controller_type"] = controller_type.name
    controller["base_controller"] = controller_type.value[1]
    controller["methods"] = []
    controller["namespace"] = namespace
    controller["uri"] = path_uri


    if is_command:
        # randomly gets a url from the base servers list as default
        resource_host = random.choice(current_file_json.get("servers")).get("url")

        # see if there is a different url specified than the default
        if path_obj.get("servers"):
            servers_with_extension = list(filter(lambda x: x.get(EXTENSION_EXTERNAL_RESOURCE), path_obj.get("servers")))

            if len(servers_with_extension) > 0:
                resource_host = random.choice(servers_with_extension).get("url")

        controller["resource_host_url"] = resource_host
        # e.g. if uri = /storage/aggregates/{id}/createvolume, resource_uri will be /storage/aggregates
        controller["resource_uri"] = "".join(path_uri.split("{id}")[0]) if is_command else None

    http_methods = [method for method in path_obj.items() if method[0] in HTTP_METHODS]
    for method in HTTP_METHODS:
        # all other methods are by default not supported, so no need to explicitly mark it
        if method in MECHANIC_SUPPORTED_HTTP_METHODS:
            controller["methods"].append({
                "name": method,
                "supported": False
            })

    for method in http_methods:
        if method[0] in MECHANIC_SUPPORTED_HTTP_METHODS:
            # get controller methods
            item = parse_method_from_path_method(current_file_json, method[0], method[1], current_dir,
                                                 command=is_command)
            _replace_or_append_dict_with_key_value_in_list(controller["methods"], "name", method[0], item)

            # get models
            response_models = parse_response_models_from_path_method(current_file_json, method[1], namespace,
                                                                     current_dir)

            # get only unique models for each path
            for rmodel in response_models:
                if not any(item["class_name"] == rmodel["class_name"] for item in models):
                    models.append(rmodel)

            schemas.extend(parse_schemas_from_path_method(current_file_json, method[1], namespace, current_dir,
                                                          command=is_command))
        else:
            raise SyntaxError("HTTP method is not supported by mechanic.")

    controller["referenced_models"] = [x["class_name"] for x in models]
    controller["referenced_schemas"] = list(set([x["class_name"] for x in schemas]))
    return controller, models, schemas


def _replace_or_append_dict_with_key_value_in_list(dict_list, key, value, new_dict):
    swapped = False
    for index, d in enumerate(dict_list):
        if d.get(key) and d.get(key) == value:
            dict_list[index] = new_dict
            swapped = True

    if not swapped:
        dict_list.append(new_dict)


def configure_resource_relationships(models, schemas):
    for origin_model in models:
        for origin_prop in origin_model["properties"]:
            if origin_prop.get("model_ref"):
                # we know there is only 1 model in list with resource_name, so get first item in list
                target_model = list(filter(lambda x: x["class_name"] == origin_prop.get("model_ref"), models))[0]

                fkey = dict()
                fkey["name"] = origin_model["resource_name"].lower() + "_id"
                fkey["type"] = "String"
                fkey["maxLength"] = 36
                fkey["fkey"] = origin_model["db_schema_name"] + "." + origin_model["db_table_name"] + ".identifier"
                target_model["properties"].append(fkey)

    # nested schemas
    for model in models:
        for prop in model["properties"]:
            if prop.get("model_ref"):
                origin_schema = list(filter(lambda x: x["model"] == model["class_name"], schemas))
                target_schema = list(filter(lambda x: x["model"] == prop.get("model_ref"), schemas))

                if len(target_schema) > 0:
                    # we need to add a nested schema
                    origin_schema[0]["additional_fields"].append({
                        "name": prop["name"],
                        "type": prop["type"],
                        "schema_ref": prop["model_ref"].replace("Model", "Schema"),
                        "required": prop["required"]
                    })

    return models, schemas


def convert(input, output):
    current_dir = ""

    if os.path.isfile(input):
        current_dir = "/".join(input.split("/")[:-1])
        with open(input) as f:
            oapi = json.load(f)
    else:
        oapi = json.loads(input)

    version = oapi.get("openapi")
    if version is None or not version.startswith("3"):
        raise SyntaxError("openapi version must be 3 or greater")

    if oapi.get("paths") is None:
        raise SyntaxError("'paths' object must be defined.")

    controllers = []
    models = []
    schemas = []

    for path in oapi.get("paths").items():
        parsed_path = build_controller_models_schemas_from_path(oapi, path[0], path[1], current_dir)
        controllers.append(parsed_path[0])

        for rmodel in parsed_path[1]:
            if not any(item["class_name"] == rmodel["class_name"] for item in models):
                models.append(rmodel)

        for rschema in parsed_path[2]:
            if not any(sitem["class_name"] == rschema["class_name"] for sitem in schemas):
                schemas.append(rschema)

    # setup foreign keys or nested schemas/ define schemas for resources that don't have a model (no DB)
    models, schemas = configure_resource_relationships(models, schemas)
    files = attach_resources_to_files(controllers, models, schemas)

    # write mechanic spec to file
    with open(output, "w") as f:
        f.write(json.dumps(files, sort_keys=True, indent=4, separators=(",", ": ")))


def attach_resources_to_files(controllers, models, schemas):
    files = {}

    for model in models:
        namespace = model["namespace"]
        namespace_models_key = "models/" + namespace + "/models.py"

        if namespace_models_key not in files.keys():
            files[namespace_models_key] = {}
            files[namespace_models_key]["models"] = []

        files[namespace_models_key]["models"].append(model)

    for schema in schemas:
        namespace = schema["namespace"]
        namespace_schemas_key = "schemas/" + namespace + "/schemas.py"
        namespace_models_package = "models." + namespace + ".models"

        if namespace_schemas_key not in files.keys():
            files[namespace_schemas_key] = {}
            files[namespace_schemas_key]["schemas"] = []
            files[namespace_schemas_key]["models_to_import"] = {
                namespace_models_package: []
            }

        files[namespace_schemas_key]["schemas"].append(schema)

        if schema["model"] != "" and schema["model"] is not None:
            files[namespace_schemas_key]["models_to_import"][namespace_models_package].append(schema["model"])

    files["app/api.py"] = {}
    files["app/api.py"]["config_module"] = "app"
    files["app/api.py"]["config_name"] = "config"

    # apis and controllers
    for controller in controllers:
        namespace = controller["namespace"]
        namespace_controllers_key = "controllers/" + namespace + "/controllers.py"
        namespace_models_package = "models." + namespace + ".models"
        namespace_schemas_package = "schemas." + namespace + ".schemas"
        namespace_services_package = "services." + namespace + ".services"
        namespace_controllers_package = "controllers." + namespace + ".controllers"

        # append controller name to api
        if namespace_controllers_package not in files["app/api.py"]:
            files["app/api.py"][namespace_controllers_package] = []

        new_dict = {
            "class_name": controller["class_name"],
            "uri": controller["uri"].replace("{id}", "<string:resource_id>")
        }
        _replace_or_append_dict_with_key_value_in_list(files["app/api.py"][namespace_controllers_package], "class_name", controller["class_name"], new_dict)

        # update controllers files
        if namespace_controllers_key not in files.keys():
            files[namespace_controllers_key] = {}
            files[namespace_controllers_key]["base_controllers_to_import"] = {
                "base.controllers": {
                    "modules": []
                }
            }
            files[namespace_controllers_key]["models_to_import"] = {
                namespace_models_package: {
                    "modules": []
                }
            }
            files[namespace_controllers_key]["schemas_to_import"] = {
                namespace_schemas_package: {
                    "modules": []
                }
            }
            files[namespace_controllers_key]["services_to_import"] = {
                namespace_services_package: {
                    "modules": []
                }
            }

            files[namespace_controllers_key]["controllers"] = []

        if controller["base_controller"] not in \
                files[namespace_controllers_key]["base_controllers_to_import"]["base.controllers"]["modules"]:
            files[namespace_controllers_key]["base_controllers_to_import"]["base.controllers"]["modules"].append(
                controller["base_controller"])

        if controller["service_class"] not in \
                files[namespace_controllers_key]["services_to_import"][namespace_services_package]["modules"]:
            files[namespace_controllers_key]["services_to_import"][namespace_services_package]["modules"].append(
                controller["service_class"])

        # add referenced models, and then remove duplicates by converting to set, then back to a list
        files[namespace_controllers_key]["models_to_import"][namespace_models_package]["modules"].extend(
            controller["referenced_models"])
        files[namespace_controllers_key]["models_to_import"][namespace_models_package]["modules"] = list(
            set(files[namespace_controllers_key]["models_to_import"][namespace_models_package]["modules"]))

        # add referenced schemas, and then remove duplicates by converting to set, then back to a list
        files[namespace_controllers_key]["schemas_to_import"][namespace_schemas_package]["modules"].extend(
            controller["referenced_schemas"])
        files[namespace_controllers_key]["schemas_to_import"][namespace_schemas_package]["modules"] = list(
            set(files[namespace_controllers_key]["schemas_to_import"][namespace_schemas_package]["modules"]))

        # append the controller to this file
        files[namespace_controllers_key]["controllers"].append(controller)
    return files


def mkdir_p_with_file(path, make_py_packages=False):
    try:
        if path.endswith(".py"):
            path = "/".join(path.split("/")[:-1])

        os.makedirs(path)

        if make_py_packages:
            with open(path + "/__init__.py", "w") as f:
                pass

    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def generate(input, output_dir, exclude=[], skip_starter_files=False):
    """
    :param input:
    :param output_dir:
    :return:
    """
    with open(input) as f:
        in_data = json.load(f)

    mkdir_p_with_file(output_dir)

    # generate starter files
    filename = os.path.abspath(sys.argv[0])
    basedir = "/".join(filename.split("/")[:-1])

    if not skip_starter_files:
        try:
            shutil.copytree(basedir + "/starter_files/base/", output_dir + "/base/")
        except FileExistsError as e:
            print("WARNING: file exists " + e.filename)
        try:
            shutil.copytree(basedir + "/starter_files/app/", output_dir + "/app/")
        except FileExistsError as e:
            print("WARNING: file exists " + e.filename)
        try:
            shutil.copytree(basedir + "/starter_files/tests/", output_dir + "/tests/")
        except FileExistsError as e:
            print("WARNING: file exists " + e.filename)

        shutil.copy(basedir + "/starter_files/requirements.txt", output_dir)
        shutil.copy(basedir + "/starter_files/run.py", output_dir)

    for file_path, file_obj in in_data.items():
        path = output_dir + "/" + file_path
        mkdir_p_with_file(output_dir + "/" + file_path, make_py_packages=True)

        with open(path, "w") as f:
            if file_path.startswith("controllers") and "controllers" not in exclude:
                create_file_from_template("templates/v2/controllers.tpl", path, file_obj)
            elif file_path.startswith("models") and "models" not in exclude:
                create_file_from_template("templates/v2/models.tpl", path, file_obj)
            elif file_path.startswith("schemas") and "schemas" not in exclude:
                create_file_from_template("templates/v2/schemas.tpl", path, file_obj)
            elif file_path.startswith("app") and "apis" not in exclude:
                create_file_from_template("templates/v2/api.tpl", path, file_obj)


def update_base(output_dir, update_all=False, controllers=False, exceptions=False, schemas=False, services=False, tests=False):
    filename = os.path.abspath(sys.argv[0])
    basedir = "/".join(filename.split("/")[:-1])

    if update_all:
        controllers = True
        exceptions = True
        schemas = True
        services = True
        tests = True

    if controllers:
        shutil.copy(basedir + "/starter_files/base/controllers.py", output_dir + "/base/controllers.py")
    if exceptions:
        shutil.copy(basedir + "/starter_files/base/exceptions.py", output_dir + "/base/exceptions.py")
    if schemas:
        shutil.copy(basedir + "/starter_files/base/schemas.py", output_dir + "/base/schemas.py")
    if services:
        shutil.copy(basedir + "/starter_files/base/services.py", output_dir + "/base/services.py")
    if tests:
        shutil.copy(basedir + "/starter_files/tests/test_base.py", output_dir + "/tests/test_base.py")


def create_file_from_template(template_path, output_path, file_data):
    result = render(template_path, {"data": file_data, "timestamp": datetime.datetime.utcnow()})

    with open(output_path, "w") as f:
        f.write(result)


def render(tpl_path, context):
    path, filename = os.path.split(tpl_path)
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(path or './')
    ).get_template(filename).render(context)

if __name__ == "__main__":
    arguments = docopt(__doc__, version="1.0")

    if arguments["convert"]:
        # default file
        output_file = "mechanic.json"

        if arguments["<OUTPUT_FILE>"] is not None:
            # user specified an output file
            output_file = arguments["<OUTPUT_FILE>"]

        input_file = arguments["<INPUT_FILE>"]
        convert(input_file, output_file)
    elif arguments["generate"]:
        generate(arguments["<INPUT_MECHANIC_FILE>"], arguments["<OUTPUT_DIRECTORY>"], exclude=arguments["--exclude"],
                 skip_starter_files=arguments["--skip-starter-files"])
    elif arguments["update-base"]:
        update_base(arguments["<OUTPUT_DIRECTORY>"], update_all=arguments["--all"],
                    controllers=arguments["--controllers"], exceptions=arguments["--exceptions"],
                    schemas=arguments["--schemas"], services=arguments["--services"], tests=arguments["--tests"])
