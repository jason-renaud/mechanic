"""
In this file, there are several terms used that can often be confusing. Here is a mini glossary to help you understand
how mechanic refers to certain terms.

model = dictionary representation needed to generate a SQLAlchemy model.
schema = a OpenAPI specification schema object.
mschema = dictionary representation needed to generate a Marshmallow schema.

Things to note:
- mechanic determines that schema responses have both MSchemas AND Models, but request bodies have only MSchemas. The
exception is error responses, these are given only MSchemas and not Models (it is assumed error responses are not saved
in the database, it is only used as a structure for response bodies).
"""
import os
import json
import yaml
import inflect
import functools
import re
import ast
import copy
from enum import Enum

# debug
import pprint

from mechanic.mechanic.merger import Merger

pp = pprint.PrettyPrinter(indent=4)
engine = inflect.engine()
EXTENSION_MICROSERVICE = "x-mechanic-microservice"
EXTENSION_NAMESPACE = "x-mechanic-namespace"
EXTENSION_PLURAL = "x-mechanic-plural"
HTTP_METHODS = ["get", "put", "post", "delete", "options", "head", "patch", "trace"]
MECHANIC_SUPPORTED_HTTP_METHODS = ["get", "put", "post", "delete"]
CONTENT_TYPE = "application/json"
DEFAULT_NAMESPACE = "default"
DEFAULT_REQUEST_BODY = "RequestBody"
DEFAULT_RESPONSE_BODY = "ResponseBody"
OPENAPI_PRIMITIVE_DATA_TYPES = ["string", "boolean", "integer", "long", "float", "double", "binary", "byte", "date",
                                "dateTime", "password"]
DEFAULT_PRIMARY_KEY = "identifier"

data_map = {
    "integer": "Integer",
    "string": "String",
    "float": "Float",
    "boolean": "Boolean"
}

py_data_map = {
    "string": "str",
    "String": "str",
    "integer": "int",
    "Integer": "int"
}


class RelationshipType(Enum):
    ONE_TO_ONE = "ONE_TO_ONE"
    SELF_ONE_TO_ONE = "SELF_ONE_TO_ONE"
    ONE_TO_MANY = "ONE_TO_MANY"
    MANY_TO_ONE = "MANY_TO_ONE"
    TO_ONE = "TO_ONE"
    TO_MANY = "TO_MANY"
    MANY_TO_MANY = "MANY_TO_MANY"


class ControllerType(Enum):
    COLLECTION_COMMAND = '/(.*)/all/(.*)*', "BaseCommandController"
    COMMAND = '/(.*)/{id}/(.*)', "BaseCommandController"
    ITEM = '/(.*)/{id}*', "BaseItemController"
    COLLECTION = '/(.*)', "BaseCollectionController"


class Converter:
    microservices = dict()          # ...
    models = dict()                 # ...
    many_to_many_models = dict()    # ...
    many_to_one_models = dict()     # ...
    one_to_many_models = dict()     # ...
    one_to_one_models = dict()      # ...
    namespaces = dict()             # the files that will house the generated code
    controllers = dict()            # ...
    mschemas = dict()               # not to be confused with OpenAPI schemas
    fkeys = dict()

    def __init__(self, oapi_file, output_file):
        self.merger = Merger(oapi_file, "temp.json")
        self.merger.merge()
        self.temp_file = "temp.json"
        self.oapi_obj = self.merger.oapi_obj
        self.output_file = output_file
        self.engine = inflect.engine()

    def convert(self):
        """
        Converts the OpenAPI file into a mechanic readable format and writes to the specified file.
        """
        self._validate_info()
        self._init_microservices()

        # go through paths
        for path_key, path_obj in self.paths.items():
            self._controller_from_path(path_key, path_obj)
        pp.pprint("###")
        self._configure_relationships()
        self._attach_to_namespaces()
        os.remove(self.temp_file)
        self._write_to_file()

    def _validate_info(self):
        """
        Validates basic information in the OpenAPI file, such as version.
        """
        self.version = self.oapi_obj.get("openapi")
        if self.version is None or not self.version.startswith("3"):
            raise SyntaxError("openapi version is invalid. Must be version 3 or greater.")

        self.servers = self.oapi_obj.get("servers")
        if self.servers is None:
            raise SyntaxError("servers array is required at the top level.")

        self.paths = self.oapi_obj.get("paths")
        if self.paths is None:
            raise SyntaxError("paths object is required")

    def _init_microservices(self):
        """
        Looks through oapi object and finds all server arrays. Each server array is considered a microservice if it has
        the mechanic extension 'x-mechanic-microservice-name': '<your-microservice-name>'. If there is no extension
        defined in any of the server objects in the servers array, the servers array is essentially ignored, and then
        will default to the main servers array at the top level of the file.

        Note: Although in OpenAPI 3.0 allows you to specify a servers array inside an operation object, mechanic only
        recognizes microservices at the paths level.
        """

        for item in self.servers:
            ms = item.get(EXTENSION_MICROSERVICE)
            if ms:
                self.microservices[ms["name"]] = ""

        # look in each path object for a server array
        for key, val in self.paths.items():
            ms_servers = val.get("servers")
            if ms_servers:
                for item in ms_servers:
                    ms = item.get(EXTENSION_MICROSERVICE)
                    if ms:
                        self.microservices[ms["name"]] = ""

    def _controller_from_path(self, path_key, path_obj):
        """
        Builds a controller object in mechanic format from a path object.

        :param path_key: key of the path, ex: "/pets/{id}"
        :param path_obj: value of the path
        :return: dictionary representation of a mechanic controller object.

        Example controller object:
        {
            'name': 'PetController',
            'controller_type': 'ITEM',
            'methods': {
                "get": {},
                "delete": {}
            },
            "uri": "/pets/{id}",
            "service": "PetService"
        }
        """
        names = self._parse_resource_name_segments_from_path(path_key)
        controller_type = self._determine_controller_type(path_key)
        namespace = path_obj.get(EXTENSION_NAMESPACE, DEFAULT_NAMESPACE)

        controller = dict()
        controller_name = names["controller"]
        controller["service"] = names["service"]
        controller["methods"] = dict()
        controller["controller_type"] = controller_type.name
        controller["base_controller"] = controller_type.value[1]
        controller["uri"] = path_key
        controller["namespace"] = namespace

        self._init_http_methods(controller)
        # get methods that are valid http methods
        path_http_methods = [method for method in path_obj.items() if method[0] in HTTP_METHODS]
        for path_method_key, path_method in path_http_methods:
            if path_method_key not in MECHANIC_SUPPORTED_HTTP_METHODS:
                msg = "WARNING: " \
                      + path_method_key \
                      + " is not supported by mechanic. This method and all items in it will be ignored."
                print(msg)
            else:
                method = self._controller_method_from_path_method(path_method_key, path_method)
                controller["methods"][path_method_key] = method

                for response_code, response_obj in path_method.get("responses").items():
                    self._model_mschema_from_response(response_code, response_obj, namespace=namespace)

                # if path_method.get("requestBody"):
                #     self._mschema_from_request_body(path_method.get("requestBody"), namespace=namespace)
        self.controllers[controller_name] = controller

    def _configure_relationships(self):
        models_str = str(self.models)
        mschemas_str = str(self.mschemas)
        fkeys_str = str(self.fkeys)
        matches = re.findall("REPLACE:\w*", models_str)
        matches.extend(re.findall("REPLACE:\w*", fkeys_str))
        exclude_matches = re.findall("\[\s*'EXCLUDE:\w*:\w*'\s*\]", mschemas_str)

        for match in exclude_matches:
            mschemas_str = str(self.mschemas)
            modelA = match.split(":")[1].strip(" ']")
            modelB = match.split(":")[2].strip(" ']")
            refs = self._find_model_attributes_with_reference(modelA, modelB)
            mschemas_str = mschemas_str.replace(match, str(refs))
            self.mschemas = ast.literal_eval(mschemas_str)

        for match in matches:
            models_str = str(self.models)
            fkeys_str = str(self.fkeys)
            model_key = match.split(":")[-1]
            model = self.models[model_key]
            replace_text = model["db_schema_name"] + "." + model["db_table_name"] + "." + DEFAULT_PRIMARY_KEY

            models_str = models_str.replace(match, replace_text)
            fkeys_str = fkeys_str.replace(match, replace_text)
            self.models = ast.literal_eval(models_str)
            self.fkeys = ast.literal_eval(fkeys_str)

        for model_key, fkeys in self.fkeys.items():
            model = self.models[model_key]

            for fkey, fkey_obj in fkeys.items():
                model["properties"][fkey] = fkey_obj

        for model_name, model_obj in self.models.items():
            for reference in model_obj.get("references"):
                for ref_name, ref_obj in reference.items():
                    if self._has_one_to_one_relationship(model_name, ref_name):
                        sorted_names = [model_name, ref_name]
                        sorted_names.sort()
                        key = "".join(sorted_names)

                        self.models[model_name]["relationships"].append({
                            "type": "one_to_one",
                            ref_name: {
                                "backref": self.models[model_name]["resource"].lower(),
                            },
                            model_name: {
                                "name": self.models[ref_name]["resource"].lower() + "_id",
                                "fkey": self.models[ref_name]["namespace"] +
                                        "." +
                                        self.models[ref_name]["db_table_name"] +
                                        ".identifier"
                            }
                        })
                    elif self._has_one_to_many_relationship(model_name, ref_name):
                        pass
                    elif self._has_many_to_one_relationship(model_name, ref_name):
                        pass
                    elif self._has_many_to_many_relationship(model_name, ref_name):
                        # sort them so that we always have the same key for the same 2 resources
                        sorted_names = [model_obj.get("resource").lower(), self.models[ref_name].get("resource").lower()]
                        sorted_names.sort()
                        table_name = "".join(sorted_names)

                        if model_obj.get("namespace") != self.models[ref_name].get("namespace"):
                            print("ERROR: many to many relationships across different namespaces is not supported.")
                            exit()

                        self.many_to_many_models[table_name] = {
                            "namespace": model_obj.get("namespace"),
                            "models": [
                                {
                                    "db_table_name": model_obj.get("db_schema_name") + "." + table_name,
                                    "fkey": model_obj.get("db_schema_name") + "." + model_obj.get("db_table_name") + "." + DEFAULT_PRIMARY_KEY,
                                    "maxLength": 36,
                                    "name": model_obj.get("resource").lower() + "_id",
                                    "type": "String"
                                },
                                {
                                    "db_table_name": model_obj.get("db_schema_name") + "." + table_name,
                                    "fkey": self.models[ref_name].get("db_schema_name") + "." + self.models[ref_name].get("db_table_name") + "." + DEFAULT_PRIMARY_KEY,
                                    "maxLength": 36,
                                    "name": self.models[ref_name].get("resource").lower() + "_id",
                                    "type": "String"
                                }
                            ]
                        }


    def _attach_to_namespaces(self):
        """
        Attaches the appropriate resources to the correct file definitions, so mechanic will know which files to
        generate.
        """
        namespaces = dict()
        for model_key, model in self.models.items():
            if not namespaces.get(model.get("namespace")):
                namespaces[model.get("namespace")] = dict()
            if not namespaces[model.get("namespace")].get("models"):
                namespaces[model.get("namespace")]["models"] = []
            namespaces[model.get("namespace")]["models"].append(model_key)
        for mschema_key, mschema in self.mschemas.items():
            if not namespaces.get(mschema.get("namespace")):
                namespaces[mschema.get("namespace")] = dict()
            if not namespaces[mschema.get("namespace")].get("mschemas"):
                namespaces[mschema.get("namespace")]["mschemas"] = []
            namespaces[mschema.get("namespace")]["mschemas"].append(mschema_key)
        for controller_key, controller in self.controllers.items():
            if not namespaces.get(controller.get("namespace")):
                namespaces[controller.get("namespace")] = dict()
            if not namespaces[controller.get("namespace")].get("controllers"):
                namespaces[controller.get("namespace")]["controllers"] = []
            namespaces[controller.get("namespace")]["controllers"].append(controller_key)
        for mm_key, mm_item in self.many_to_many_models.items():
            if not namespaces.get(mm_item.get("namespace")):
                namespaces[mm_item.get("namespace")] = dict()
            if not namespaces[mm_item.get("namespace")].get("many_to_many"):
                namespaces[mm_item.get("namespace")]["many_to_many"] = []
            namespaces[mm_item.get("namespace")]["many_to_many"].append(mm_key)
        self.namespaces = namespaces

    def _write_to_file(self):
        obj = {
            "microservices": self.microservices,
            "namespaces": self.namespaces,
            "models": self.models,
            "mschemas": self.mschemas,
            "many_to_many_models": self.many_to_many_models,
            "controllers": self.controllers,
            "fkeys": self.fkeys,
        }
        with open(self.output_file, "w") as f:
            f.write(json.dumps(obj, indent=4))

    # ------------------------ Helper methods
    def _has_one_to_one_relationship(self, model_a, model_b):
        return self._has_one_relationship(model_a, model_b) and self._has_one_relationship(model_b, model_a)

    def _has_one_to_many_relationship(self, model_a, model_b):
        return self._has_one_relationship(model_a, model_b) and self._has_many_relationship(model_b, model_a)

    def _has_many_to_one_relationship(self, model_a, model_b):
        return self._has_many_relationship(model_a, model_b) and self._has_one_relationship(model_b, model_a)

    def _has_many_to_many_relationship(self, model_a, model_b):
        return self._has_many_relationship(model_a, model_b) and self._has_many_relationship(model_b, model_a)

    def _has_one_relationship(self, model_name, many_one_check):
        for item in self.models[model_name].get("references", []):
            if item.get(many_one_check) == "ONE":
                return True
        return False

    def _has_many_relationship(self, model_name, many_model_check):
        for item in self.models[model_name].get("references", []):
            if item.get(many_model_check) == "MANY":
                return True
        return False

    def _mschema_from_request_body(self, request_body, namespace=DEFAULT_NAMESPACE):
        content = request_body.get("content").get(CONTENT_TYPE)

        if not content.get("schema").get("$ref"):
            if content.get("schema").get("type") == "array" and content.get("schema").get("items").get("$ref"):
                # array of references
                schema, schema_name = self._follow_reference_link(content.get("schema").get("items").get("$ref"))
            else:
                schema = content.get("schema")
                schema_name = schema.get("title", DEFAULT_REQUEST_BODY)
        else:
            schema, schema_name = self._follow_reference_link(content.get("schema").get("$ref"))

        mschema_key = self._get_mschema_name_from_schema(schema, schema_key=schema_name)
        mschema = self._init_mschema_obj(schema_name, schema, namespace=schema.get(EXTENSION_NAMESPACE, namespace))

        self._mschema_from_schema_properties(mschema_key,
                                             mschema,
                                             namespace=mschema["namespace"],
                                             schema_properties=schema.get("properties", {}))

    def _model_mschema_from_response(self, response_code, response_obj, namespace=DEFAULT_NAMESPACE):
        """
        'ref_type' can be one of: 'oo', 'om', 'mo', 'mm'
        'oo': One-to-one
        'om': One-to-many
        'mo': Many-to-one
        'mm': Many-to-many
        'pair': Subset of one-to-one where the objects are the same type, identifies objects that reference each other,
                but no others.

        {
            'db_table_name': 'cars',
            'db_schema_name': 'garage',
            'folder': 'cars',
            'path': 'models.CarModel',
            'references': {
                'wheels': {
                    'model_path': 'models.WheelModel',
                    'model_name': 'WheelModel',
                    'ref_type': 'om',           # a car has many wheels
                    'self_reference': false,
                    'tightly_coupled': true     # implies that this object can only exist with it's parent. Admittedly,
                                                # car/wheel analogy falls apart here. But in this case, this means that
                                                # if a car is deleted, the wheel is also deleted.
                }
            },
            'properties': {
                'make': {
                    'enum': [],
                    'max_length': null,
                    'type': 'String'
                },
                'model': {
                    'type': 'String'
                }
            }

        }
        :param response_code:
        :param response_obj:
        :return:
        """
        if response_code == "204":
            return
        content = response_obj.get("content").get(CONTENT_TYPE)
        # current_schema_key = None

        if not content.get("schema").get("$ref"):
            if content.get("schema").get("type") == "array" and content.get("schema").get("items").get("$ref"):
                # array of references
                schema, schema_name = self._follow_reference_link(content.get("schema").get("items").get("$ref"))
                # current_schema_key = self._schema_key_from_ref(content.get("schema").get("items").get("$ref"))
            else:
                schema = content.get("schema")
                schema_name = schema.get("title", DEFAULT_RESPONSE_BODY)
        else:
            schema, schema_name = self._follow_reference_link(content.get("schema").get("$ref"))
            # current_schema_key = content.get("schema").get("$ref")

        # Create models from response
        model_key = self._get_model_name_from_schema(schema, schema_key=schema_name)
        model = self._init_model_obj(schema_name, schema, namespace=schema.get(EXTENSION_NAMESPACE, namespace))
        self._model_from_schema_properties(model_key,
                                           model,
                                           current_schema_key=schema_name,
                                           namespace=schema.get(EXTENSION_NAMESPACE, namespace),
                                           schema_properties=schema.get("properties", {}))

        # Create mschemas from response
        self._mschema_from_model(model_key, model, namespace=model["namespace"])

    def _mschema_from_model(self, model_key, model, namespace=DEFAULT_NAMESPACE):
        schema_key = model_key.replace("Model", "Schema")
        schema = dict()
        schema["model"] = model_key
        schema["resource"] = model_key.replace("Model", "")
        schema["namespace"] = namespace
        model_copy = copy.deepcopy(model)
        # schema["properties"] = copy.deepcopy(model_copy["properties"])
        schema["properties"] = dict()

        for prop_name, prop in model_copy["properties"].items():
            if prop.get("reference"):
                if not schema["properties"].get(prop_name):
                    schema["properties"][prop_name] = dict()
                schema["properties"][prop_name]["nested"] = prop.get("reference").get("model").replace("Model", "Schema")
                schema["properties"][prop_name]["many"] = prop.get("reference").get("uselist", False)
            if prop.get("enum"):
                if not schema["properties"].get(prop_name):
                    schema["properties"][prop_name] = dict()
                schema["properties"][prop_name]["enum"] = prop.get("enum")
            if prop.get("regex"):
                if not schema["properties"].get(prop_name):
                    schema["properties"][prop_name] = dict()
                schema["properties"][prop_name]["regex"] = prop.get("regex")
            if prop.get("oneOf"):
                if not schema["properties"].get(prop_name):
                    schema["properties"][prop_name] = dict()
                    schema["properties"][prop_name]["oneOf"] = []

                for item in prop.get("oneOf"):
                    if item.get("reference"):
                        """
                        This tells mechanic that once all of the models are built, it will replace this text with 
                        attributes names that are referenced from one model to the other. For example, if the text says
                        EXCLUDE:DogModel:FoodModel, it will replace this text with a list of attribute names in DogModel
                        that reference FoodModel. This is to prevent infinite recursion, in the case where 2 models
                        refer back to each other.
                        """

                        exclude = ["EXCLUDE:" + item.get("reference").get("model") + ":" + model_key]
                        schema["properties"][prop_name]["oneOf"].append({
                            "nested": item.get("reference").get("model").replace("Model", "Schema"),
                            "exclude": exclude,
                            "attr_name": item.get("attr_name")
                        })
                    else:
                        schema["properties"][prop_name]["oneOf"].append({
                            "type": item.get("type"),
                            "required": item.get("required"),
                            "maxLength": item.get("maxLength"),
                            "enum": item.get("enum"),
                            "regex": item.get("regex"),
                            "attr_name": item.get("attr_name")
                        })


            if schema["properties"].get(prop_name):
                schema["properties"][prop_name]["required"] = prop.get("required")
                schema["properties"][prop_name]["maxLength"] = prop.get("maxLength")
                schema["properties"][prop_name]["type"] = prop.get("type")

        self.mschemas[schema_key] = schema

    def _find_model_attributes_with_reference(self, modelA_key, modelB_key):
        attrs = []
        modelA = self.models[modelA_key]

        for prop_name, prop in modelA.get("properties").items():
            if prop.get("reference", {}).get(modelB_key):
                attrs.append(prop_name)
        return attrs

    def _mschema_from_schema_properties(self,
                                        mschema_key,
                                        mschema,
                                        namespace=DEFAULT_NAMESPACE,
                                        schema_properties={},
                                        schema_all_of=[],
                                        required_props=[],
                                        visited_schemas=[]):
        """
        Recursively creates a model object from schema properties and references to other schemas.

        :param mschema_key: the key for the mschema being created. Usually <resource-name>Schema
        :param mschema: the mschema object currently being created.
        :param schema_properties: the properties object of the schema
        :param schema_all_of: the allOf object of the schema
        :param required_props: the required array of the schema
        :param visited_schemas: schemas that have been processed already.
        :return:
        """

        # mark as visited
        visited_schemas.append(mschema_key)

        if schema_all_of:
            # if a schema has the "allOf" property, then combine all of the properties into a single schema.
            for item in schema_all_of:
                ref_type, ref = self._get_schema_reference_type(item)
                if ref:
                    referenced_schema, referenced_schema_key = self._follow_reference_link(ref)
                    referenced_mschema_key = self._get_mschema_name_from_schema(referenced_schema,
                                                                                schema_key=referenced_schema.get("title", referenced_schema_key))

                    mschema["references"].append({
                        referenced_mschema_key: ref_type
                    })
                    self._mschema_from_schema_properties(mschema_key,
                                                         mschema,
                                                         namespace=referenced_schema.get(EXTENSION_NAMESPACE, namespace),
                                                         schema_properties=referenced_schema.get("properties", {}),
                                                         schema_all_of=referenced_schema.get("allOf", []),
                                                         required_props=referenced_schema.get("required", []))

                    if referenced_mschema_key not in visited_schemas:
                        self._mschema_from_schema_properties(referenced_mschema_key,
                                                             self._init_mschema_obj(referenced_schema_key,
                                                                                    referenced_schema,
                                                                                    namespace=referenced_schema.get(
                                                                                        EXTENSION_NAMESPACE,
                                                                                        namespace)),
                                                             namespace=referenced_schema.get(EXTENSION_NAMESPACE, namespace),
                                                             schema_properties=referenced_schema.get("properties"),
                                                             required_props=referenced_schema.get("required", []),
                                                             schema_all_of=referenced_schema.get("allOf", []),
                                                             visited_schemas=visited_schemas)
                else:
                    self._mschema_from_schema_properties(mschema_key,
                                                         mschema,
                                                         namespace=item.get(EXTENSION_NAMESPACE, namespace),
                                                         schema_properties=item.get("properties", {}),
                                                         schema_all_of=item.get("allOf", []),
                                                         required_props=item.get("required", []))
        else:
            # Otherwise, look at the properties object
            for prop_name, prop_obj in schema_properties.items():
                ref_type, ref = self._get_schema_reference_type(prop_obj)
                prop_one_of = prop_obj.get("oneOf")
                prop_any_of = prop_obj.get("anyOf")
                prop_all_of = prop_obj.get("allOf")

                new_prop = dict()
                name = prop_name.replace("-", "_") if prop_name else None
                new_prop["type"] = data_map.get(prop_obj.get("type")) or prop_obj.get("type")
                new_prop["required"] = prop_name in required_props
                new_prop["maxLength"] = prop_obj.get("maxLength")
                new_prop["enum"] = prop_obj.get("enum", [])
                new_prop["regex"] = prop_obj.get("pattern")

                # Base case
                if prop_obj.get("type") in OPENAPI_PRIMITIVE_DATA_TYPES:
                    mschema["properties"][name] = new_prop
                elif ref:
                    referenced_schema, referenced_schema_key = self._follow_reference_link(ref)
                    referenced_mschema_key = self._get_mschema_name_from_schema(prop_obj,
                                                                                schema_key=referenced_schema.get("title", referenced_schema_key))
                    new_prop["references"] = dict()
                    new_prop["references"][referenced_mschema_key] = ref_type
                    mschema["properties"][name] = new_prop
                    mschema["references"].append({
                        referenced_mschema_key: ref_type
                    })
                    if referenced_mschema_key not in visited_schemas:
                        self._mschema_from_schema_properties(referenced_mschema_key,
                                                             self._init_mschema_obj(referenced_schema_key,
                                                                                    referenced_schema,
                                                                                    namespace=referenced_schema.get(
                                                                                        EXTENSION_NAMESPACE,
                                                                                        namespace)),
                                                           namespace=referenced_schema.get(EXTENSION_NAMESPACE, namespace),
                                                           schema_properties=referenced_schema.get("properties", {}),
                                                           schema_all_of=referenced_schema.get("allOf", []),
                                                           required_props=referenced_schema.get("required", []),
                                                           visited_schemas=visited_schemas)
                elif prop_one_of:
                    new_prop["references"] = dict()
                    new_prop["references"]["oneOf"] = []

                    for item in prop_one_of:
                        one_of_ref_type, one_of_ref = self._get_schema_reference_type(item)
                        new_prop["references"]["oneOf"].append({
                            item.get("type") or self._get_mschema_name_from_schema(item): one_of_ref_type
                        })

                        if one_of_ref:
                            referenced_schema, referenced_schema_key = self._follow_reference_link(one_of_ref)
                            referenced_mschema_key = self._get_mschema_name_from_schema(referenced_schema,
                                                                                        schema_key=referenced_schema.get("title",referenced_schema_key))
                            mschema["references"].append({
                                referenced_mschema_key: one_of_ref_type
                            })
                            if referenced_mschema_key not in visited_schemas:
                                self._mschema_from_schema_properties(referenced_mschema_key,
                                                                   self._init_mschema_obj(referenced_schema_key,
                                                                                          referenced_schema,
                                                                                          namespace=referenced_schema.get(EXTENSION_NAMESPACE, namespace)),
                                                                   namespace=referenced_schema.get(EXTENSION_NAMESPACE, namespace),
                                                                   schema_properties=referenced_schema.get("properties"),
                                                                   required_props=referenced_schema.get("required", []),
                                                                   schema_all_of=referenced_schema.get("allOf", []),
                                                                   visited_schemas=visited_schemas)
                    mschema["properties"][name] = new_prop
                elif prop_all_of:
                    self._mschema_from_schema_properties(mschema_key,
                                                         mschema,
                                                         namespace=namespace,
                                                         schema_all_of=prop_all_of,
                                                         visited_schemas=visited_schemas)

        if not self.mschemas.get(mschema_key):
            print(mschema_key)
            self.mschemas[mschema_key] = mschema

    def _model_from_schema_properties(self,
                                      model_key,
                                      model,
                                      current_schema_key=None,
                                      namespace=DEFAULT_NAMESPACE,
                                      schema_properties={},
                                      schema_all_of=[],
                                      required_props=[],
                                      visited_schemas=[]):
        """
        Recursively creates a model object from schema properties and references to other schemas.

        :param model_key: the key for the model being created. Usually <resource-name>Model
        :param model: the model object currently being created.
        :param schema_properties: the properties object of the schema
        :param schema_all_of: the allOf object of the schema
        :param required_props: the required array of the schema
        :param visited_schemas: schemas that have been processed already.
        :return:
        """
        # mark as visited
        visited_schemas.append(model_key)

        if schema_all_of:
            # if a schema has the "allOf" property, then combine all of the properties into a single schema.
            for item in schema_all_of:
                ref_type, ref = self._get_schema_reference_type(item)
                if ref:
                    referenced_schema, referenced_schema_key = self._follow_reference_link(ref)
                    referenced_model_key = self._get_model_name_from_schema(referenced_schema,
                                                                            schema_key=referenced_schema.get("title", referenced_schema_key))
                    current_schema_key = self._schema_key_from_ref(ref)
                    model["references"].append({
                        referenced_model_key: ref_type
                    })
                    self._model_from_schema_properties(model_key,
                                                       model,
                                                       current_schema_key=current_schema_key,
                                                       namespace=referenced_schema.get(EXTENSION_NAMESPACE, namespace),
                                                       schema_properties=referenced_schema.get("properties", {}),
                                                       schema_all_of=referenced_schema.get("allOf", []),
                                                       required_props=referenced_schema.get("required", []))

                    if referenced_model_key not in visited_schemas:
                        self._model_from_schema_properties(referenced_model_key,
                                                           self._init_model_obj(referenced_schema_key,
                                                                                referenced_schema,
                                                                                namespace=referenced_schema.get(EXTENSION_NAMESPACE, namespace)),
                                                           current_schema_key=referenced_schema_key,
                                                           namespace=referenced_schema.get(EXTENSION_NAMESPACE,
                                                                                           namespace),
                                                           schema_properties=referenced_schema.get("properties"),
                                                           required_props=referenced_schema.get("required", []),
                                                           schema_all_of=referenced_schema.get("allOf", []),
                                                           visited_schemas=visited_schemas)
                else:
                    self._model_from_schema_properties(model_key,
                                                       model,
                                                       current_schema_key=current_schema_key,
                                                       namespace=item.get(EXTENSION_NAMESPACE, namespace),
                                                       schema_properties=item.get("properties", {}),
                                                       schema_all_of=item.get("allOf", []),
                                                       required_props=item.get("required", []))
        else:
            # Otherwise, look at the properties object
            for prop_name, prop_obj in schema_properties.items():
                ref_type, ref = self._get_schema_reference_type(prop_obj)
                prop_one_of = prop_obj.get("oneOf")
                prop_any_of = prop_obj.get("anyOf")
                prop_all_of = prop_obj.get("allOf")

                new_prop = dict()
                name = prop_name.replace("-", "_") if prop_name else None
                new_prop["type"] = data_map.get(prop_obj.get("type")) or prop_obj.get("type")
                new_prop["pytype"] = py_data_map.get(prop_obj.get("type")) or prop_obj.get("type")
                new_prop["required"] = prop_name in required_props
                new_prop["maxLength"] = prop_obj.get("maxLength")
                new_prop["enum"] = prop_obj.get("enum", [])
                new_prop["regex"] = prop_obj.get("pattern")

                # Base case
                if prop_obj.get("type") in OPENAPI_PRIMITIVE_DATA_TYPES:
                    model["properties"][name] = new_prop
                elif ref:
                    referenced_schema, referenced_schema_key = self._follow_reference_link(ref)
                    referenced_model_key = self._get_model_name_from_schema(prop_obj,
                                                                            schema_key=referenced_schema.get("title", referenced_schema_key))
                    self._create_reference_property(current_schema_key, model_key, new_prop, ref_type,
                                                    referenced_model_key, referenced_schema, referenced_schema_key)

                    model["properties"][name] = new_prop
                    model["references"].append({
                        referenced_model_key: ref_type
                    })
                    if referenced_model_key not in visited_schemas:
                        self._model_from_schema_properties(referenced_model_key,
                                                           self._init_model_obj(referenced_schema_key,
                                                                                referenced_schema,
                                                                                namespace=referenced_schema.get(EXTENSION_NAMESPACE, namespace)),
                                                           current_schema_key=referenced_schema_key,
                                                           namespace=referenced_schema.get(EXTENSION_NAMESPACE, namespace),
                                                           schema_properties=referenced_schema.get("properties", {}),
                                                           schema_all_of=referenced_schema.get("allOf", []),
                                                           required_props=referenced_schema.get("required", []),
                                                           visited_schemas=visited_schemas)
                elif prop_one_of:
                    new_prop["oneOf"] = []
                    for item in prop_one_of:
                        one_of_ref_type, one_of_ref = self._get_schema_reference_type(item)
                        one_of_prop = dict()

                        if one_of_ref:
                            referenced_schema, referenced_schema_key = self._follow_reference_link(one_of_ref)
                            referenced_model_key = self._get_model_name_from_schema(referenced_schema,
                                                                                    schema_key=referenced_schema.get("title", referenced_schema_key))

                            self._create_reference_property(current_schema_key, model_key, one_of_prop, one_of_ref_type,
                                                            referenced_model_key, referenced_schema,
                                                            referenced_schema_key, one_of=True)

                            model["references"].append({
                                referenced_model_key: one_of_ref_type
                            })

                            one_of_prop["attr_name"] = prop_name + "_" + referenced_model_key.lower()
                            new_prop["oneOf"].append(one_of_prop)
                            # model["references"].append(new_prop)
                            if referenced_model_key not in visited_schemas:
                                self._model_from_schema_properties(referenced_model_key,
                                                                   self._init_model_obj(referenced_schema_key,
                                                                                        referenced_schema,
                                                                                        namespace=referenced_schema.get(EXTENSION_NAMESPACE, namespace)),
                                                                   current_schema_key=referenced_schema_key,
                                                                   namespace=referenced_schema.get(EXTENSION_NAMESPACE, namespace),
                                                                   schema_properties=referenced_schema.get("properties"),
                                                                   required_props=referenced_schema.get("required", []),
                                                                   schema_all_of=referenced_schema.get("allOf", []),
                                                                   visited_schemas=visited_schemas)
                        else:
                            one_of_prop = dict()
                            one_of_prop["type"] = data_map.get(item.get("type")) or item.get("type")
                            one_of_prop["attr_name"] = prop_name + "_" + one_of_prop["type"].lower()
                            one_of_prop["pytype"] = py_data_map.get(item.get("type")) or item.get("type")
                            one_of_prop["required"] = prop_name in item.get("properties", [])
                            one_of_prop["maxLength"] = item.get("maxLength")
                            one_of_prop["enum"] = item.get("enum", [])
                            one_of_prop["regex"] = item.get("pattern")

                            new_prop["oneOf"].append(one_of_prop)
                    model["properties"][name] = new_prop
                elif prop_all_of:
                    self._model_from_schema_properties(model_key,
                                                       model,
                                                       namespace=namespace,
                                                       schema_all_of=prop_all_of,
                                                       visited_schemas=visited_schemas)

        self.models[model_key] = model
        self._mschema_from_model(model_key, model, namespace=model["namespace"])

    def _create_reference_property(self, current_schema_key, model_key, new_prop, ref_type, referenced_model_key,
                                   referenced_schema, referenced_schema_key, one_of=False):
        if not new_prop.get("reference"):
            new_prop["reference"] = dict()

        new_prop["reference"][referenced_model_key] = ref_type
        new_prop["reference"]["model"] = referenced_model_key
        # new_prop["reference"]["resource"] = referenced_schema_key
        new_prop["reference"]["foreign_keys"] = None
        new_prop["reference"]["back_populates"] = None
        new_prop["reference"]["backref"] = None
        new_prop["reference"]["uselist"] = True

        rel_type = self._determine_relationship(current_schema_key, ref_type, referenced_schema)
        if rel_type == RelationshipType.TO_ONE:
            new_prop["reference"]["uselist"] = False

            if not self.fkeys.get(model_key):
                self.fkeys[model_key] = dict()

            self.fkeys[model_key][referenced_schema_key.lower() + "_id"] = {
                "type": "String",
                "maxLength": 36,
                "foreign_key": "REPLACE:" + referenced_model_key
            }
            if self.fkeys.get(model_key, {}).get(referenced_schema_key.lower() + "_id"):
                new_prop["reference"]["foreign_keys"] = model_key + "." + referenced_schema_key.lower() + "_id"
        elif rel_type == RelationshipType.TO_MANY:
            if not self.fkeys.get(referenced_model_key):
                self.fkeys[referenced_model_key] = dict()

            self.fkeys[referenced_model_key][current_schema_key.lower() + "_id"] = {
                "type": "String",
                "maxLength": 36,
                "foreign_key": "REPLACE:" + model_key
            }

            if self.fkeys.get(model_key, {}).get(referenced_schema_key.lower() + "_id"):
                new_prop["reference"]["foreign_keys"] = model_key + "." + referenced_schema_key.lower() + "_id"
        elif rel_type == RelationshipType.ONE_TO_ONE:
            new_prop["reference"]["uselist"] = False
            new_prop["reference"]["back_populates"] = current_schema_key.lower()

            # sorting them, because we only want 1 foreign key
            sorted_model_keys = [referenced_model_key, model_key]
            sorted_model_keys.sort()
            sorted_schema_keys = [referenced_schema_key, current_schema_key]
            sorted_schema_keys.sort()

            if not self.fkeys.get(sorted_model_keys[0]):
                self.fkeys[sorted_model_keys[0]] = dict()

            self.fkeys[sorted_model_keys[0]][sorted_schema_keys[1].lower() + "_id"] = {
                "type": "String",
                "maxLength": 36,
                "foreign_key": "REPLACE:" + sorted_model_keys[1]
            }
            if self.fkeys.get(model_key, {}).get(referenced_schema_key.lower() + "_id"):
                new_prop["reference"]["foreign_keys"] = model_key + "." + referenced_schema_key.lower() + "_id"
        elif rel_type == RelationshipType.ONE_TO_MANY:
            new_prop["reference"]["backref"] = current_schema_key.lower()
            if not self.fkeys.get(referenced_model_key):
                self.fkeys[referenced_model_key] = dict()

            self.fkeys[referenced_model_key][current_schema_key.lower() + "_id"] = {
                "type": "String",
                "maxLength": 36,
                "foreign_key": "REPLACE:" + model_key
            }
            # new_prop["reference"]["foreign_keys"] = model_key + "." + referenced_schema_key.lower() + "_id"
        elif rel_type == RelationshipType.MANY_TO_ONE:
            new_prop["reference"]["uselist"] = False

            if not one_of:
                new_prop.pop("reference")
        elif rel_type == RelationshipType.MANY_TO_MANY:
            print("Many to many relationships are not supported.")
            exit()

    def _determine_controller_type(self, path_key):
        if re.fullmatch(ControllerType.COLLECTION_COMMAND.value[0], path_key):
            controller_type = ControllerType.COLLECTION_COMMAND
            is_command = True
        elif re.fullmatch(ControllerType.COMMAND.value[0], path_key):
            controller_type = ControllerType.COMMAND
            is_command = True
        elif re.fullmatch(ControllerType.ITEM.value[0], path_key):
            controller_type = ControllerType.ITEM
        elif re.fullmatch(ControllerType.COLLECTION.value[0], path_key):
            controller_type = ControllerType.COLLECTION
        else:
            raise SyntaxError("path uri does not match proper uri formatting. See mechanic documentation for details")
        return controller_type

    def _controller_method_from_path_method(self, method_name, method_obj):
        """
        Parses an operation object and converts it to a method object, to be included in a controller object.

        Example:
        {
            'get': {}
        }
        :return: dictionary representation of a controller method
        """
        method = dict()
        method["method"] = method_name
        method["query_params"] = []
        if method_obj.get("parameters"):
            # TODO - make more specific so doesn't include uri params
            method["query_params"] = [p["name"] for p in method_obj.get("parameters")]
        method["response"] = dict()
        method["request"] = dict()
        method["supported"] = True

        self._controller_method_response_from_path_response(method, method_obj["responses"])
        return method

    def _controller_method_response_from_path_response(self, method, response_obj):
        response_code = None
        response_obj_item = None
        if response_obj.get("200"):
            response_code = "200"
            response_obj_item = response_obj.get("200")
        elif response_obj.get("201"):
            response_code = "201"
            response_obj_item = response_obj.get("201")
        elif response_obj.get("202"):
            response_code = "202"
            response_obj_item = response_obj.get("202")
        elif response_obj.get("204"):
            response_code = "204"
            method["response"]["success_code"] = response_code
            return method

        if response_code is None:
            raise SyntaxError("No 200, 201, 202, or 204 response is defined for method.")

        content = response_obj_item.get("content").get(CONTENT_TYPE)

        method["response"]["success_code"] = response_code
        method["response"]["model"] = self._get_model_name_from_schema(content.get("schema"))
        method["response"]["mschema"] = self._get_mschema_name_from_schema(content.get("schema"))

    def _get_name_from_schema(self, schema_obj, schema_key=None):
        if schema_key:
            return schema_obj.get("title", schema_key)

        _, ref = self._get_schema_reference_type(schema_obj)
        if ref:
            return schema_obj.get("title", ref.rsplit("/", 1)[1])

        return schema_obj.get("title")

    def _get_model_name_from_schema(self, schema_obj, schema_key=None):
        if schema_obj.get("$ref"):
            schema, schema_name = self._follow_reference_link(schema_obj.get("$ref"))
        elif schema_obj.get("items", {}).get("$ref"):
            schema, schema_name = self._follow_reference_link(schema_obj.get("items", {}).get("$ref"))
        else:
            schema_name = self._get_name_from_schema(schema_obj, schema_key=schema_key)
        return schema_name + "Model"

    def _get_mschema_name_from_schema(self, schema_obj, schema_key=None):
        if schema_obj.get("$ref"):
            schema, schema_name = self._follow_reference_link(schema_obj.get("$ref"))
        elif schema_obj.get("items", {}).get("$ref"):
            schema, schema_name = self._follow_reference_link(schema_obj.get("items", {}).get("$ref"))
        else:
            schema_name = self._get_name_from_schema(schema_obj, schema_key=schema_obj.get("title", schema_key))
        return schema_name + "Schema"

    def _get_schema_reference_type(self, schema_obj):
        if schema_obj.get("$ref"):
            return "ONE", schema_obj.get("$ref")
        elif schema_obj.get("items", {}).get("$ref"):
            return "MANY", schema_obj.get("items", {}).get("$ref")
        return None, None

    def _schema_key_from_ref(self, ref):
        return ref.split("/")[-1]

    def _determine_relationship(self, current_schema_name, ref_type_to_schema, referenced_schema, referenced_schema_name=None):
        """

        :param current_schema_name: the schema's name that references another schema
        :param ref_type_to_schema: the reference type the current schema has to the referenced schema
        :param referenced_schema: the referenced schema object
        :return:
        """
        for prop_name, prop in referenced_schema.get("properties", {}).items():
            if prop.get("$ref", "").endswith(current_schema_name.lower()):

                if ref_type_to_schema == "ONE":
                    return RelationshipType.ONE_TO_ONE
                elif ref_type_to_schema == "MANY":
                    return RelationshipType.ONE_TO_MANY
            elif prop.get("items", {}).get("$ref", "").endswith(current_schema_name.lower()):
                if ref_type_to_schema == "ONE":
                    return RelationshipType.MANY_TO_ONE
                elif ref_type_to_schema == "MANY":
                    return RelationshipType.MANY_TO_MANY
            elif prop.get("oneOf"):
                for item in prop["oneOf"]:
                    if item.get("$ref", "").endswith(current_schema_name.lower()):
                        if ref_type_to_schema == "ONE":
                            return RelationshipType.ONE_TO_ONE
                        elif ref_type_to_schema == "MANY":
                            return RelationshipType.ONE_TO_MANY
                    elif item.get("items", {}).get("$ref", "").endswith(current_schema_name.lower()):
                        if ref_type_to_schema == "ONE":
                            return RelationshipType.MANY_TO_ONE
                        elif ref_type_to_schema == "MANY":
                            return RelationshipType.MANY_TO_MANY

        if ref_type_to_schema == "ONE":
            return RelationshipType.TO_ONE
        elif ref_type_to_schema == "MANY":
            return RelationshipType.TO_MANY

    def _init_http_methods(self, controller):
        # start by initializing all methods as unsupported.
        for http_method in HTTP_METHODS:
            # all other methods are by default not supported, so no need to explicitly mark it
            if http_method in MECHANIC_SUPPORTED_HTTP_METHODS:
                controller["methods"][http_method] = {
                    "supported": False
                }

    def _follow_reference_link(self, ref):
        """
        Gets a referenced object.

        :param ref: reference link, example: #/components/schemas/Pet or pet.json#/components/schemas/Pet
        :param current_dir: current directory of looking for file
        :return: dictionary representation of the referenced object
        """
        is_link_in_current_file = True if ref.startswith("#/") else False

        if is_link_in_current_file:
            section = ref.split("/")[-3]
            object_type = ref.split("/")[-2]
            resource_name = ref.split("/")[-1]
            return self.oapi_obj[section][object_type][resource_name], \
                   self.oapi_obj[section][object_type][resource_name].get("title") or resource_name

    def _parse_resource_name_segments_from_path(self, path_uri):
        naming = dict()
        n = path_uri.split("/{id}")[0].split("/all/")[0].split("/")[-1]
        naming["resource"] = self.engine.singular_noun(n.title()) or n.title()
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
        return names

    def _init_model_obj(self, schema_name, schema_obj, namespace=DEFAULT_NAMESPACE, base_uri=None):
        model = dict()
        model["resource"] = schema_name
        model["properties"] = dict()
        model["references"] = []
        model["relationships"] = []
        model["namespace"] = namespace
        model["base_uri"] = base_uri

        # if overridden
        if schema_obj.get(EXTENSION_PLURAL):
            model["db_table_name"] = schema_obj.get(EXTENSION_PLURAL)
        else:
            model["db_table_name"] = engine.plural_noun(schema_name.replace("-", "").replace("_", "")).lower()

        model["db_schema_name"] = schema_obj.get(EXTENSION_NAMESPACE, namespace)
        return model

    def _init_mschema_obj(self, schema_name, schema_obj, namespace=DEFAULT_NAMESPACE):
        mschema = dict()
        mschema["resource"] = schema_name
        mschema["properties"] = dict()
        mschema["references"] = []
        mschema["namespace"] = namespace
        return mschema
