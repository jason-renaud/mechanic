import os
import jinja2
import json
import re
import argparse
import datetime
import inflect
import logmatic
import logging
import shutil

from mapping.maps import data_type_map

"""
This file reads an OpenAPI 2.0 specification and generates code from the spec. See README.md for more details and the
assumptions being made.
"""

logger = logging.getLogger("codegen")
handler = logging.StreamHandler()
handler.setFormatter(logmatic.JsonFormatter())

logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
engine = inflect.engine()

SUPPORTED_HTTP_METHODS = ["get", "post", "put", "delete"]
EXTENSION_NAMESPACE = "x-faction-namespace"


def render(tpl_path, context):
    path, filename = os.path.split(tpl_path)
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(path or './')
    ).get_template(filename).render(context)


def get_definition_from_ref(definitions, ref):
    p = re.compile('#\/definitions\/(.*)')
    definition_name = re.sub(p, r'\1', str(ref))

    return definitions[definition_name]


def find_dict_in_list(item_list, dict_key, dict_val=None):
    for item in item_list:
        if item.get(dict_key) and dict_val is None:
            return item
        if item.get(dict_key) == dict_val:
            return item
    return None


def is_dict_in_list(item_list, dict_key, dict_val):
    for item in item_list:
        if item.get(dict_key) == dict_val:
            return True
    return False


def parse_model_name_from_path(uri):
    resource_name = uri.rsplit("/")[-1]
    if resource_name == "{id}":
        resource_name = uri.rsplit("/")[-2]

    resource_singular = engine.singular_noun(resource_name)

    # resource_name is already singular
    if not resource_singular:
        resource_singular = resource_name

    return resource_singular.title().replace("-", "")


def find_tag(data, tag_name):
    for tag_obj in data["tags"]:
        if tag_obj["name"] == tag_name:
                return tag_obj


def parse_spec_v2(data):
    # This is the formatted data that the templates can read
    formatted_data = {
        # tags are what groups APIs together. The models/controllers/schemas are separated into different packages
        # based on the tag name.
        "namespaces": []
    }

    # Dictionary to keep track of foreign key references need to be added after all models are created
    foreign_keys = []

    # loop through each path item
    for path_uri, path_object in data["paths"].items():
        # get http methods from spec that are supported and that have tag(s) defined
        supported_methods_with_tags = list(
            filter(lambda method: method[0] in SUPPORTED_HTTP_METHODS and method[1].get("tags"), path_object.items()))

        # get the tag names
        method_tags = list(map(lambda method: method[1].get("tags"), supported_methods_with_tags))
        method_tags_with_extension = list(filter(lambda tag_name: tag_name.startswith(EXTENSION_NAMESPACE), method_tags[0]))

        if len(method_tags_with_extension) > 1:
            logger.error("You have defined more than one tag with the suffix: " + EXTENSION_NAMESPACE)
            return
        elif len(method_tags_with_extension) < 1:
            logger.error("You have not defined a tag with the suffix %s in %s", EXTENSION_NAMESPACE, path_uri)
            return

        tag_name = method_tags_with_extension[0]
        tag_name_without_extension = tag_name.replace(EXTENSION_NAMESPACE + "=", "")

        responses = list(map(lambda response: response[1]["responses"], supported_methods_with_tags))
        responses_2xx = list(
            map(lambda response: next(val for key, val in response.items() if key.startswith("2")), responses))

        if len(responses_2xx) is []:
            logger.error("No 2xx response defined for api endpoint %s. Processing will not continue.", path_uri)
            return

        ref = find_definition_ref_from_responses(responses_2xx)
        spec_definition = get_definition_from_ref(data["definitions"], ref)

        if spec_definition is not None:
            new_namespace = get_existing_namespace(formatted_data, tag_name_without_extension)

            if new_namespace is None:
                new_namespace = {}
                new_namespace["models"] = []
                new_namespace["controllers"] = []
                new_namespace["unique_models_for_controller"] = []

            new_namespace["name"] = tag_name_without_extension

            # Model will probably be referenced several times in each path, only add it once
            if not is_dict_in_list(new_namespace["models"], "model_name", spec_definition.get("title")):
                create_model_from_definition(spec_definition, new_namespace["models"], new_namespace["name"], foreign_keys)

            new_namespace["controllers"].append(
                create_controller_from_path(path_uri, supported_methods_with_tags, new_namespace))

            if get_existing_namespace(formatted_data, new_namespace["name"]) is None:
                formatted_data["namespaces"].append(new_namespace)

    for f_key in foreign_keys:
        tag_item = find_dict_in_list(formatted_data["namespaces"], "name", f_key["tag"])
        model_item = find_dict_in_list(tag_item["models"], "model_name", f_key["model_name"])

        model_item["properties"].append({
            "name": f_key["name"],
            "type": f_key["type"],
            "foreign_key": f_key["foreign_key"]
        })
    return formatted_data


def get_existing_namespace(data, tag_name):
    for tag_item in data["namespaces"]:
        if tag_item["name"] == tag_name:
            return tag_item


def find_definition_ref_from_responses(responses):
    responses_with_schema = list(filter(lambda x: x.get("schema") is not None or x.get("schema").get("$ref") or x.get("schema").get("items").get("$ref"), responses))
    schema = responses_with_schema[0]["schema"]
    ref = schema.get("$ref")

    if ref is None:
        ref = schema.get("items")

        if ref is None:
            ref = schema.get("items")
        else:
            ref = schema.get("items").get("$ref")
    return ref


def create_model_from_definition(definition, model_list, tag_name, foreign_keys):
    if is_dict_in_list(model_list, "model_name", definition.get("title")):
        # if model has already been created, don't worry about it
        return

    model = {}
    model["model_name"] = definition.get("title")
    model["table_name"] = engine.plural(model["model_name"]).lower()

    if model.get("properties") is None:
        model["properties"] = []

    model["package"] = tag_name

    # loop through the properties associated with this model
    for property_name, property_object in definition.get("properties").items():
        prop_obj = {}
        prop_obj["name"] = property_name.replace("-", "_")

        # look up the value in the data type map from OpenAPI to SQLAlchemy
        prop_obj["type"] = data_type_map.get(property_object.get("type")) or property_object.get("type")
        prop_obj["required"] = True if property_name in definition.get("required", []) else False
        prop_obj["maxLength"] = property_object.get("maxLength") if property_object.get("maxLength") is not None else None

        if property_object.get("type") == "array" and property_object.get("items", {}).get("type") == "string":
            # We want to leave this out of the model definition, this is a list of items which would not be stored
            # in the DB. Therefore, don't do anything here.
            pass
        else:
            definition_ref = None
            # First, see if there is a direct reference
            ref = property_object.get("$ref")
            if ref is not None:
                definition_ref = get_definition_from_ref(data["definitions"], ref)
                prop_obj["ref"] = definition_ref.get("title")

            # Next, see if there is an array of references
            ref = property_object.get("items", {}).get("$ref")
            if ref is not None:
                definition_ref = get_definition_from_ref(data["definitions"], ref)
                prop_obj["ref"] = definition_ref.get("title")

                # create foreign key object, to be added to the models later
                foreign_key_prop = {
                    "model_name": prop_obj["ref"],
                    "tag": tag_name,
                    "name": model["model_name"].lower() + "_id",
                    "type": "String(36)",
                    "foreign_key": tag_name + "." + model["table_name"] + ".identifier",
                }
                if not is_dict_in_list(foreign_keys, "model_name", foreign_key_prop["model_name"]):
                   foreign_keys.append(foreign_key_prop)
            # create model from nest references
            if definition_ref is not None:
                create_model_from_definition(definition_ref, model_list, tag_name, foreign_keys)

        model["properties"].append(prop_obj)

    model_list.append(model)
    return model


def create_controller_from_path(path_uri, path_object, tag_obj):
    controller = {}
    controller["uri"] = path_uri.replace("{id}", "<string:resource_id>")
    controller["model_name"] = parse_model_name_from_path(path_uri)

    if path_uri.endswith("{id}"):
        controller["controller_name"] = controller["model_name"] + "Controller"
    else:
        controller["controller_name"] = controller["model_name"] + "CollectionController"

    controller["package"] = tag_obj["name"]

    # start with marking each method as False, then loop through and mark each APIs supported one as True
    controller["methods"] = [{"name": method, "supported": False} for method in SUPPORTED_HTTP_METHODS ]

    for item in controller["methods"]:
        for path in path_object:
            if path[0] == item["name"]:
                item["supported"] = True

    if controller["model_name"] not in tag_obj["unique_models_for_controller"]:
        tag_obj["unique_models_for_controller"].append(controller["model_name"])
    return controller


def create_package(project_dir, package_name):
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


def create_models_file(namespace_obj, filepath):
    models_result = render("templates/models.tpl",
                           {
                               "data": namespace_obj["models"],
                               "db_schema": namespace_obj["name"],
                               "timestamp": datetime.datetime.utcnow()
                           })

    f = open(filepath, "w")
    f.write(models_result)
    f.close()


def create_controllers_file(namespace_obj, filepath):
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


def create_schemas_file(namespace_obj, filepath):
    schemas_result = render("templates/schemas.tpl",
                            {
                                "data": namespace_obj["models"],
                                "models_path": "models." + namespace_obj["name"] + ".models",
                                "timestamp": datetime.datetime.utcnow()
                            })

    f = open(filepath, "w")
    f.write(schemas_result)
    f.close()


def create_api_file(filepath):
    api_result = render("templates/api.tpl",
                           {
                               "data": parsed_data["namespaces"],
                               "timestamp": datetime.datetime.utcnow()
                           })

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    f = open(filepath, "w")
    f.write(api_result)
    f.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("spec")
    parser.add_argument("dir")
    parser.add_argument("--debug", action="store_true")
    args = vars(parser.parse_args())

    with open(args["spec"]) as data_file:
        data = json.load(data_file)

    parsed_data = parse_spec_v2(data)

    if args.get("debug"):
        logger.debug("Debug enabled, not generating code files but instead creating parsed_data_test.json file with "
                     "parsed data.")
        file = open("parsed_data_test.json", "w")
        file.write(str(parsed_data))
        file.close()
        exit()

    if parsed_data is None:
        logger.error("Error occurred while attempting to parse OpenAPI spec.")
        exit()

    for namespace in parsed_data["namespaces"]:
        create_package(args["dir"], namespace["name"])
        create_models_file(namespace, args["dir"] + "/models/" + namespace["name"] + "/models.py")
        create_controllers_file(namespace, args["dir"] + "/controllers/" + namespace["name"] + "/controllers.py")
        create_schemas_file(namespace, args["dir"] + "/schemas/" + namespace["name"] + "/schemas.py")

    create_api_file(args["dir"] + "/app/api.py")



