import os
import json
import argparse
import logging
import logmatic
import inflect
import re
import jinja2
import datetime

from mapping.maps import data_type_map

logger = logging.getLogger("codegen")
handler = logging.StreamHandler()
handler.setFormatter(logmatic.JsonFormatter())

logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
engine = inflect.engine()

EXTENSION_NAMESPACE = "X-mechanic-namespace"
EXTENSION_ASYNC = "X-mechanic-async"
OAPI_PATH_FIXED_FIELDS = ["summary", "description", "servers", "parameters"]
OAPI_PATH_SUPPORTED_HTTP_METHODS = ["get", "post", "put", "delete", "options", "head", "patch", "trace"]
MECHANIC_SUPPORTED_HTTP_METHODS = ["get", "post", "put", "delete"]
CONTENT_TYPE = "application/json"
PROJECT_DIR = None

# This is the formatted data that the templates can read
formatted_data = {
    # tags are what groups APIs together. The models/controllers/schemas are separated into different packages
    # based on the tag name.
    "namespaces": []
}

# Dictionary to keep track of foreign key references need to be added after all models are created
foreign_keys = []


def render(tpl_path, context):
    path, filename = os.path.split(tpl_path)
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(path or './')
    ).get_template(filename).render(context)


def _find_existing_namespace(name):
    for item in formatted_data["namespaces"]:
        if item["name"] == name:
            return item


def _replace_obj_by_name(item_list, obj):
    index = 0
    # remove if already exists
    for namespace in item_list:
        if namespace["name"] == obj["name"]:
            item_list.pop(index)
        index = index + 1
    item_list.append(obj)


def _get_schema_from_ref(json_data, ref, curr_dir=None):
    if curr_dir is None:
        curr_dir = PROJECT_DIR + "/resources/"
    schema_ref = ref.get("$ref") or ref.get("items").get("$ref")

    p = re.compile('(.*)#\/components/schemas\/(.*)')
    filepath = re.sub(p, r'\1', str(schema_ref))
    schema_name = re.sub(p, r'\2', str(schema_ref))

    #base_dir = PROJECT_DIR + "/resources/" + curr_dir + "/"
    base_dir = curr_dir
    if filepath is not "":
        path_segments = filepath.split("/")
        if path_segments[0] is '':
            print("ERROR: mechanic does not support absolute path references. Use a relative path instead.")
        else:
            for index, item in enumerate(path_segments):
                if index != len(path_segments)-1:
                    if not curr_dir.endswith("/"):
                        curr_dir = curr_dir + "/" + item + "/"
                    else:
                        curr_dir = curr_dir + item + "/"

        resource_file = os.path.abspath(base_dir + filepath)
        with open(resource_file, "r") as file:
            data = json.load(file)
    else:
        data = json_data["components"]["schemas"].copy()
    return data[schema_name], curr_dir


def _get_resource_name_from_path(json_data, responses):
    for response in responses:
        if response[0] == "get":
            if response[1].get("responses") is not None:
                # There must be a 200 response defined for a GET in order for the pathing to work.
                resource_schema = response[1].get("responses").get("200").get("content").get(CONTENT_TYPE).get("schema")
                schema, curr_dir = _get_schema_from_ref(json_data, resource_schema)
                return schema["title"]


def _build_controller_for_path(json_data, path_uri, namespace_name, supported_methods):
    new_controller = dict()
    new_controller["uri"] = path_uri.replace("{id}", "<string:resource_id>")
    new_controller["controller_name"] = _get_resource_name_from_path(json_data, supported_methods)
    new_controller["resource_name"] = _get_resource_name_from_path(json_data, supported_methods)

    if not path_uri.endswith("{id}"):
        new_controller["controller_name"] = new_controller["controller_name"] + "Collection"

    new_controller["package"] = namespace_name
    new_controller["methods"] = [{"name": method, "supported": False} for method in MECHANIC_SUPPORTED_HTTP_METHODS ]

    for method in supported_methods:
        new_method = dict()
        new_method["async"] = False
        new_method["name"] = method[0]
        new_method["supported"] = True
        new_method["query_params"] = []

        if method[1].get("parameters"):
            for param in method[1].get("parameters"):
                if param.get("in") == "query":
                    new_method["query_params"].append(param.get("name"))

        for item in method[1].get("responses").items():
            if item[0].startswith("2"):

                new_method["success_response_code"] = item[0]

                # 204 returns nothing, can't get ref of nothing
                if item[0] != "204":
                    ref, curr_dir = _get_schema_from_ref(json_data, item[1].get("content").get(CONTENT_TYPE).get("schema"))
                    new_method["response_model"] = ref.get("title")

        _replace_obj_by_name(new_controller["methods"], new_method)
    return new_controller


def _build_model_from_ref(json_data, schema, namespace_name, models, curr_dir=None):
    new_model = dict()
    new_model["properties"] = []
    new_model["package"] = namespace_name
    new_model["model_name"] = schema.get("title")
    new_model["table_name"] = engine.plural_noun(new_model["model_name"]).lower()

    for prop in schema["properties"].items():
        new_prop = dict()
        new_prop["name"] = prop[0].replace("-", "_")
        new_prop["type"] = data_type_map.get(prop[1]["type"]) or prop[1].get("type")
        new_prop["required"] = True if prop[0] in schema.get("required", []) else False
        new_prop["maxLength"] = prop[1].get("maxLength")
        _replace_obj_by_name(new_model["properties"], new_prop)

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
                schema_ref, curr_dir = _get_schema_from_ref(json_data, property_object, curr_dir=curr_dir)
                new_prop["ref"] = schema_ref.get("title")

            # Next, see if there is an array of references
            ref = property_object.get("items", {}).get("$ref")
            if ref is not None:
                schema_ref, curr_dir = _get_schema_from_ref(json_data, property_object, curr_dir=curr_dir)
                new_prop["ref"] = schema_ref.get("title")

                # create foreign key object, to be added to the models later
                foreign_key_prop = {
                    "model_name": new_prop["ref"],
                    "model_ref_name": new_model["model_name"],
                    "tag": namespace_name,
                    "name": new_model["model_name"].lower() + "_id",
                    "type": "String(36)",
                    "foreign_key": namespace_name + "." + new_model["table_name"] + ".identifier",
                }

                if not _is_foreign_key_in_list(foreign_key_prop):
                    foreign_keys.append(foreign_key_prop)

                    # create model from nested references
                if schema_ref is not None:
                    _build_model_from_ref(json_data, schema_ref, namespace_name, models, curr_dir=curr_dir)

    if _find_model_in_list(models, new_model["model_name"]) is None:
        models.append(new_model)


def _build_models_for_path(json_data, path_uri, namespace_name, supported_methods, models):
    for method in supported_methods:
        for item in method[1].get("responses").items():
            if item[0].startswith("2"):
                if item[0] != "204":
                    ref, curr_dir = _get_schema_from_ref(json_data, item[1].get("content").get(CONTENT_TYPE).get("schema"))
                    _build_model_from_ref(json_data, ref, namespace_name, models, curr_dir=curr_dir)
    return models


def _find_model_in_list(model_list, model_name):
    for item in model_list:
        if item["model_name"] == model_name:
            return item


def _is_foreign_key_in_list(foreign_key_obj):
    for item in foreign_keys:
        if item.get("model_name") == foreign_key_obj["model_name"] \
                and item.get("name") == foreign_key_obj["name"] \
                and item.get("model_ref_name") == foreign_key_obj["model_ref_name"]:
            return True
    return False


def _parse_data_from_path(json_data, path_uri, path_obj):
    # just ignores HTTP methods not supported
    supported_methods = list(filter(lambda method: method[0] in MECHANIC_SUPPORTED_HTTP_METHODS, path_obj.items()))
    valid_tags = list(map(lambda method: method[1].get("tags"), supported_methods))

    if not all(tag == valid_tags[0] for tag in valid_tags):
        print("ERROR: Some HTTP methods in path %s have mismatched %s attributes.", path_uri, EXTENSION_NAMESPACE)
        return False

    namespace_name = valid_tags[0][0].replace(EXTENSION_NAMESPACE + "=", "")
    namespace = _find_existing_namespace(namespace_name)

    if namespace is None:
        namespace = dict()
        namespace["models"] = []
        namespace["controllers"] = []
        namespace["unique_models_for_controller"] = []

    namespace["name"] = namespace_name
    controller = _build_controller_for_path(json_data, path_uri, namespace_name, supported_methods)

    if controller["resource_name"] not in namespace["unique_models_for_controller"]:
        namespace["unique_models_for_controller"].append(controller["resource_name"])

    namespace["controllers"].append(controller)
    _build_models_for_path(json_data, path_uri, namespace_name, supported_methods, namespace["models"])

    _replace_obj_by_name(formatted_data["namespaces"], namespace)
    #_find_schema_from_method_responses(list(map(lambda method: method[1]["responses"], supported_methods)))
    return True


def _parse_spec(json_data):
    # verify openapi version 3.0
    if not json_data.get("openapi").startswith("3"):
        print("ERROR: Invalid openapi version. If using Swagger 2.0, use generate-resources.py instead.")
        return False

    # loop through each path item
    for path_key, path_object in data["paths"].items():
        success = _parse_data_from_path(json_data, path_key, path_object)

        if not success:
            return False

    # add all foreign keys after models have been built
    for f_key in foreign_keys:
        for namespace in formatted_data["namespaces"]:
            model_item = _find_model_in_list(namespace["models"], f_key["model_name"])

            if model_item is not None:
                model_item["properties"].append({
                    "name": f_key["name"],
                    "type": f_key["type"],
                    "foreign_key": f_key["foreign_key"]
                })
    return True


def _generate_models(namespace_obj, filepath):
    models_result = render("templates/models.tpl",
                           {
                               "data": namespace_obj["models"],
                               "db_schema": namespace_obj["name"],
                               "timestamp": datetime.datetime.utcnow()
                           })

    f = open(filepath, "w")
    f.write(models_result)
    f.close()


def _generate_controllers(namespace_obj, filepath):
    controllers_result = render("templates/controllers.tpl",
                                {
                                    "data": namespace_obj["controllers"],
                                    "models": namespace_obj["unique_models_for_controller"],
                                    "models_path": "models." + namespace_obj["name"] + ".models",
                                    "schemas_path": "schemas." + namespace_obj["name"] + ".schemas",
                                    "services_path": "services." + namespace_obj["name"] + ".services",
                                    "timestamp": datetime.datetime.utcnow()
                                })

    f = open(filepath, "w")
    f.write(controllers_result)
    f.close()


def _generate_schemas(namespace_obj, filepath):
    schemas_result = render("templates/schemas.tpl",
                            {
                                "data": namespace_obj["models"],
                                "models_path": "models." + namespace_obj["name"] + ".models",
                                "timestamp": datetime.datetime.utcnow()
                            })

    f = open(filepath, "w")
    f.write(schemas_result)
    f.close()


def _generate_api(filepath):
    api_result = render("templates/api.tpl",
                           {
                               "data": formatted_data["namespaces"],
                               "timestamp": datetime.datetime.utcnow()
                           })

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    f = open(filepath, "w")
    f.write(api_result)
    f.close()


def _create_package(project_dir, package_name):
    folders = ["controllers", "schemas", "models", "services"]
    for folder in folders:
        file_path = project_dir + "/" + folder + "/__init__.py"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        f = open(file_path, "w")
        f.close()

        file_path = project_dir + "/" + folder + "/" + package_name + "/__init__.py"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        f = open(file_path, "w")
        f.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("openapi3.0-spec-file")
    parser.add_argument("project-directory")
    parser.add_argument("--debug", action="store_true")
    args = vars(parser.parse_args())

    PROJECT_DIR = os.path.expanduser(args["project-directory"])

    with open(args["openapi3.0-spec-file"]) as data_file:
        data = json.load(data_file)

    success = _parse_spec(data)

    if not success:
        print("ERROR: Failed to parse spec file.")
        exit()

    if args.get("debug"):
        print("DEBUG: Debug enabled, not generating code files but instead creating debug.json file with "
              "parsed data that mechanic would have used to generate the code files.")
        file = open("debug.json", "w")
        file.write(str(formatted_data))
        file.close()
        exit()

    for namespace in formatted_data["namespaces"]:
        _create_package(args["project-directory"], namespace["name"])
        _generate_models(namespace, args["project-directory"] + "/models/" + namespace["name"] + "/models.py")
        _generate_schemas(namespace, args["project-directory"] + "/schemas/" + namespace["name"] + "/schemas.py")
        _generate_controllers(namespace, args["project-directory"] + "/controllers/" + namespace["name"] +
                              "/controllers.py")

    _generate_api(args["project-directory"] + "/app/api.py")
