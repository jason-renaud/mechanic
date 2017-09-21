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
import yamlordereddictloader
import re
import ast
import copy
from enum import Enum
from collections import OrderedDict

# debug
import pprint

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
DEFAULT_BASE_CONTROLLERS_PATH = "base.controllers"
OPENAPI_PRIMITIVE_DATA_TYPES = ["string", "boolean", "integer", "long", "float", "double", "binary", "byte", "date",
                                "dateTime", "password"]
DEFAULT_PRIMARY_KEY = "identifier"
# regex pattern that matches variables in the path uri. For example {id} in /api/dogs/{id}
VAR_PATTERN = r'{([\w_-]*)}'

data_map = {
    "integer": "Integer",
    "string": "String",
    "number": "Float",
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
    ONE_TO_ONEOF = "ONE_TO_ONEOF"
    SELF_ONE_TO_ONE = "SELF_ONE_TO_ONE"
    ONE_TO_MANY = "ONE_TO_MANY"
    MANY_TO_ONE = "MANY_TO_ONE"
    TO_ONE = "TO_ONE"
    TO_MANY = "TO_MANY"
    MANY_TO_MANY = "MANY_TO_MANY"


class ControllerType(Enum):
    BASE = "BaseController"
    ITEM = "BaseItemController"
    COLLECTION = "BaseCollectionController"


class Merger:
    """
    Provides an API to merge an OpenAPI spec that is split into multiple files. For example, if you have a reference
    to an external document like this:

    $ref: cars/wheel.yaml#wheel

    mechanic will merge the reference to that schema into the original file, and then save a copy.
    """
    root_dir = ""
    EXTERNAL_SCHEMA_REGEX = "['\"]\$ref['\"]:\s['\"](?:\w|/)*\.(?:json|yaml|yml)#[/\w]*['\"]"

    def __init__(self, oapi_file, output_file):
        self.oapi_file = oapi_file
        self.oapi_obj = self._deserialize_file()
        self.output_file = output_file

    def merge(self):
        """
        Currently only supports referencing items that will end up in the components/schemas location in the spec file.
        """
        self._merge_schemas()

        self._write_to_file()

    def _deserialize_file(self):
        """
        Deserializes a file from either json or yaml and converts it to a dictionary structure to operate on.

        :param oapi_file:
        :return: dictionary representation of the OpenAPI file
        """
        if self.oapi_file.endswith(".json"):
            with open(self.oapi_file) as f:
                oapi = json.load(f)
        elif self.oapi_file.endswith(".yaml") or self.oapi_file.endswith(".yml"):
            with open(self.oapi_file) as f:
                oapi = yaml.load(f)
        else:
            raise SyntaxError("File is not of correct format. Must be either json or yaml (and filename extension must "
                              "one of those too).")
        self.root_dir = os.path.dirname(os.path.realpath(self.oapi_file))
        return oapi

    def _follow_reference_link(self, ref, remote_only=False):
        """
        Gets a referenced object. Note, references must be in relation to the main OpenAPI file, not in relation to the
        current file.

        :param ref: reference link, example: #/components/schemas/Pet or pet.json#/Pet
        :param remote_only: flag to indicate if the caller is only interested in external references.
        :return: dictionary representation of the referenced object or None is ref is not external and remote_only=True.
        """
        is_link_in_current_file = True if ref.startswith("#/") else False

        if is_link_in_current_file and remote_only:
            return None

        if is_link_in_current_file:
            section = ref.split("/")[-3]
            object_type = ref.split("/")[-2]
            resource_name = ref.split("/")[-1]
            return self.oapi_obj[section][object_type][resource_name], resource_name
        else:
            filename = ref.split("#/")[0]
            object_name = ref.split("#/")[1]
            data = None

            with open(self.root_dir + "/" + filename) as f:
                if filename.endswith(".json"):
                    data = json.load(f)
                elif filename.endswith(".yaml") or filename.endswith(".yml"):
                    data = yaml.load(f)
                else:
                    raise SyntaxError(
                        "File is not of correct format. Must be either json or yaml (and filename extension must "
                        "one of those too).")

            return data[object_name]

    def _write_to_file(self):
        """
        Write the merged data into the specified output file.
        """
        with open(self.output_file, "w") as f:
            if self.output_file.endswith(".json"):
                json_data = json.dumps(self.oapi_obj, indent=3)
                f.write(json_data)
            elif self.output_file.endswith(".yaml") or self.output_file.endswith(".yml"):
                yaml_data = yaml.dump(OrderedDict(self.oapi_obj),
                                      Dumper=yamlordereddictloader.Dumper,
                                      default_flow_style=False)
                f.write(yaml_data)
            else:
                raise SyntaxError("Specified output file is not of correct format. Must be either json or yaml.")

    def _merge_schemas(self):
        """
        Merges referenced items into the components/schemas section of the specification file.
        """

        # convert the master file oapi dictionary into a string
        oapi_str = str(self.oapi_obj)
        # find all patterns in the string that match an external reference.
        matches = re.findall(self.EXTERNAL_SCHEMA_REGEX, oapi_str)

        # as long as there are matches, continue to merge the schemas
        while len(matches) > 0:
            for match in matches:
                reference = match.split(":")[1].replace("'", "").strip(" ")
                resource_name = reference.split("/")[-1]
                obj = self._follow_reference_link(reference, remote_only=True)

                if obj:
                    oapi_str = oapi_str.replace(match, '"$ref": "#/components/schemas/' + resource_name + '"')
                    # convert string back to a dictionary
                    self.oapi_obj = ast.literal_eval(oapi_str)

                    # if the object doesn't exist yet in the components/schemas section, add it.
                    if not self.oapi_obj["components"]["schemas"].get(resource_name):
                        self.oapi_obj["components"]["schemas"][resource_name] = obj

                    # set the string object for the next iteration of the loops.
                    oapi_str = str(self.oapi_obj)
            # find new matches after current iteration of merging schemas. Some of the merged schemas may have external
            # references as well, which would required several iterations of the while loop.
            matches = re.findall(self.EXTERNAL_SCHEMA_REGEX, oapi_str)


class Converter:
    """
    Class that provides an API for converting an OpenAPI 3.0 specification file into a mechanic formatted file that can
    be used to generate code.
    """
    microservices = dict()          # Not used yet
    models = dict()                 # Dict representation of SQLAlchemy models to be generated
    many_to_many_models = dict()    # Not used yet.
    namespaces = dict()             # Mapping of namespaces and resources within those namespaces
    controllers = dict()            # Dict representation of controllers to be generated
    mschemas = dict()               # Dict representation of Marshmallow schemas, not to be confused w/ OpenAPI schemas
    fkeys = dict()                  # Dict representation of foreign keys that are added to the mappings at the end

    def __init__(self, oapi_file, output_file):
        # first merge the file into one
        self.merger = Merger(oapi_file, "temp.json")
        self.merger.merge()
        self.temp_file = "temp.json"
        self.oapi_obj = self.merger.oapi_obj
        self.output_file = output_file
        self.engine = inflect.engine()

    def convert(self, merge=None):
        """
        Converts the OpenAPI file into a mechanic readable format and writes to the specified file.
        """
        self._validate_info()

        # microservices are not used by the code generator yet.
        self._init_microservices()

        # go through paths
        for path_key, path_obj in self.paths.items():
            self._controller_from_path(path_key, path_obj)

        self._configure_relationships()
        self._attach_to_namespaces()
        os.remove(self.temp_file)
        self._write_to_file()

        # If merge is set, write the output of the merged OpenAPI file into the specified file.
        if merge:
            if not os.path.exists(merge):
                os.makedirs(os.path.dirname(merge))

            with open(merge, "w") as f:
                if merge.endswith(".yaml") or merge.endswith(".yml"):
                    f.write(yaml.dump(OrderedDict(self.oapi_obj),
                                      Dumper=yamlordereddictloader.Dumper,
                                      default_flow_style=False))
                elif merge.endswith(".json"):
                    f.write(json.dumps(self.oapi_obj, indent=3))
                else:
                    print("ERROR: merge file specified must end with either .json, .yml, or .yaml")
                    exit()

    def _validate_info(self):
        """
        Validates basic information in the OpenAPI file
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
            'base_controller': 'BaseItemController',
            'methods': {
                "get": {...},
                "delete": {...}
            },
            "uri": "/pets/{id}"
        }
        """
        names = self._parse_resource_name_segments_from_path(path_key)
        controller_type = self._determine_controller_type(path_key)
        namespace = path_obj.get(EXTENSION_NAMESPACE, DEFAULT_NAMESPACE)

        controller = dict()
        controller_name = names["controller"]
        controller["methods"] = dict()
        controller["controller_type"] = controller_type.name

        if controller_type == ControllerType.BASE:
            controller["base_controller"] = os.getenv("MECHANIC_CUSTOM_CONTROLLER", controller_type.value).split(".")[-1]
        elif controller_type == ControllerType.ITEM:
            controller["base_controller"] = os.getenv("MECHANIC_CUSTOM_ITEM_CONTROLLER", controller_type.value).split(".")[-1]
        elif controller_type == ControllerType.COLLECTION:
            controller["base_controller"] = os.getenv("MECHANIC_CUSTOM_COLLECTION_CONTROLLER", controller_type.value).split(".")[-1]

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

                if path_method.get("requestBody"):
                    self._mschema_from_request_body(path_method.get("requestBody"), namespace=namespace)

        # format uri in way readable for Flask-Restful
        if controller_type == ControllerType.ITEM:
            controller["uri"] = re.sub(VAR_PATTERN, r'<string:resource_id>', path_key)
        elif controller_type == ControllerType.COLLECTION:
            controller["uri"] = path_key
        else:
            controller_name = controller_name.replace("Controller",
                                                      controller["uri"].split("}/", 1)[1].
                                                      replace("{", "").
                                                      replace("/", "").
                                                      replace("}", "").
                                                      replace("-", "").
                                                      replace("_", "").title() + "Controller")
            controller["uri"] = re.sub(VAR_PATTERN, r'<string:\1>', path_key).replace("-", "_")
        self.controllers[controller_name] = controller

    def _configure_relationships(self):
        """
        Configures any relationships that could not be configured during the initial processing. For example, adding
        foreign keys. During initial processing, certain attributes were marked with specific string patterns to be
        replaced with meaningful objects that had not been created at that time
        """
        models_str = str(self.models)
        mschemas_str = str(self.mschemas)
        fkeys_str = str(self.fkeys)
        matches = re.findall("REPLACE:\w*", models_str)
        matches.extend(re.findall("REPLACE:\w*", fkeys_str))
        exclude_matches = re.findall("\[\s*'EXCLUDE:\w*:\w*'\s*\]", mschemas_str)

        for match in exclude_matches:
            """
            Find attributes marked by the exclude matches. This is used in the mschemas section, where a nested property
            can mark certain attributes to exclude from it's schema.
            """
            mschemas_str = str(self.mschemas)
            modelA = match.split(":")[1].strip(" ']")
            modelB = match.split(":")[2].strip(" ']")
            refs = self._find_model_attributes_with_reference(modelA, modelB)

            mschemas_str = mschemas_str.replace(match, str(refs))
            self.mschemas = ast.literal_eval(mschemas_str)

        for match in matches:
            """
            Find foreign keys based on the patterns in both fkeys and models objects.
            """
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
            """
            Add foreign keys to model properties.
            """
            model = self.models[model_key]

            for fkey, fkey_obj in fkeys.items():
                model["properties"][fkey] = fkey_obj

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
            if self.output_file.endswith(".json"):
                json_data = json.dumps(obj, indent=3)
                f.write(json_data)
            elif self.output_file.endswith(".yaml") or self.output_file.endswith(".yml"):
                yaml_data = yaml.dump(OrderedDict(obj),
                                      Dumper=yamlordereddictloader.Dumper,
                                      default_flow_style=False)
                f.write(yaml_data)
            else:
                raise SyntaxError("Specified output file is not of correct format. Must be either json or yaml.")

    # ------------------------ Helper methods
    def _mschema_from_request_body(self, request_body, namespace=DEFAULT_NAMESPACE):
        """
        Builds a dictionary representation of a Marshmallow schema from an OpenAPI requestBody object.

        :param request_body: requestBody object
        :param namespace: namespace for the mschema to be placed in.
        """
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
        Builds a model and mschema from an OpenAPI 3.0 response object.

        :param response_code: response code of the response object
        :param response_obj: the object itself
        """
        if response_code == "204":
            return
        content = response_obj.get("content").get(CONTENT_TYPE)

        if not content.get("schema").get("$ref"):
            if content.get("schema").get("type") == "array" and content.get("schema").get("items").get("$ref"):
                # array of references
                schema, schema_name = self._follow_reference_link(content.get("schema").get("items").get("$ref"))
            else:
                schema = content.get("schema")
                schema_name = schema.get("title", DEFAULT_RESPONSE_BODY)
        else:
            schema, schema_name = self._follow_reference_link(content.get("schema").get("$ref"))

        # Create models from response
        model_key = self._get_model_name_from_schema(schema, schema_key=schema_name)
        model = self._init_model_obj(schema_name, schema, namespace=schema.get(EXTENSION_NAMESPACE, namespace))
        self._model_from_schema_properties(model_key,
                                           model,
                                           current_schema_key=schema_name,
                                           namespace=schema.get(EXTENSION_NAMESPACE, namespace),
                                           schema_all_of=schema.get("allOf", []),
                                           schema_properties=schema.get("properties", {}),
                                           required_props=schema.get("required", []))

        # Create mschemas from the model
        self._mschema_from_model(model_key, model, namespace=model["namespace"])

    def _mschema_from_model(self, model_key, model, namespace=DEFAULT_NAMESPACE):
        """
        Build an mschema from an already existing model.

        :param model_key: name of the model, for example 'DogModel'
        :param model: model object itself.
        :param namespace: namespace to place the mschema in.
        """
        schema_key = model_key.replace("Model", "Schema")
        schema = dict()
        schema["model"] = model_key
        schema["resource"] = model_key.replace("Model", "")
        schema["namespace"] = namespace
        model_copy = copy.deepcopy(model)
        schema["properties"] = dict()

        for prop_name, prop in model_copy["properties"].items():
            if prop.get("reference"):
                if not schema["properties"].get(prop_name):
                    schema["properties"][prop_name] = dict()

                referenced_schema_name = prop.get("reference").get("model").replace("Model", "Schema")
                nested = "self" if referenced_schema_name == schema_key else referenced_schema_name
                schema["properties"][prop_name]["nested"] = nested
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
        """
        Gets a list of all attributes in modelA that reference modelB.

        :param modelA_key:
        :param modelB_key:
        :return: List of attributes in modelA that reference modelB
        """
        attrs = []
        modelA = self.models[modelA_key]

        for prop_name, prop in modelA.get("properties").items():
            if prop.get("reference", {}).get(modelB_key):
                attrs.append(prop_name)
            elif prop.get("oneOf"):
                for item in prop.get("oneOf"):
                    if item.get("reference", {}).get(modelB_key):
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
        Recursively creates a mschema object from schema properties and references to other schemas.

        :param mschema_key: the key for the mschema being created. Usually <resource-name>Schema
        :param mschema: the mschema object currently being created.
        :param namespace: the namespace for the mschema to be placed in.
        :param schema_properties: the properties object of the schema
        :param schema_all_of: the allOf object of the schema if it exists.
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
        :param current_schema_key: the OpenAPI key of the schema being processed.
        :param namespace: the namespace for the model to be placed in.
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
        """
        Creates a property that indicates a reference to another model.

        :param current_schema_key: schema key of the OpenAPI schema object being processed.
        :param model_key: model key of the model where the property will be placed
        :param new_prop: property object being created.
        :param ref_type: type of reference to the referenced schema. Can be 'ONE' or 'MANY'.
        :param referenced_model_key: model key of the model being referenced.
        :param referenced_schema: OpenAPI object of the referenced schema.
        :param referenced_schema_key: key to the referenced schema.
        :param one_of: indicates if this reference is coming from inside of a oneOf construct.
        """
        if not new_prop.get("reference"):
            new_prop["reference"] = dict()

        new_prop["reference"][referenced_model_key] = ref_type
        # new_prop["reference"]["model"] = "self" if model_key == referenced_model_key else referenced_model_key
        new_prop["reference"]["model"] = referenced_model_key
        new_prop["reference"]["remote_side"] = "[identifier]" if model_key == referenced_model_key else None
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
        elif rel_type == RelationshipType.ONE_TO_ONEOF:
            new_prop["reference"]["uselist"] = False
            new_prop["reference"]["back_populates"] = current_schema_key.lower() + "_" + model_key.lower()

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
        elif rel_type == RelationshipType.MANY_TO_MANY:
            print("Many to many relationships are not supported.")
            exit()

    def _determine_controller_type(self, path_key):
        """
        Based on the pattern of the path endpoint, map to the correct type of controller.
        :param path_key: uri of the controller endpoint
        :return: the controller type
        """
        matches = re.findall(VAR_PATTERN, path_key)
        if len(matches) > 1:
            controller_type = ControllerType.BASE
        elif matches and (not path_key.endswith("{" + matches[0] + "}") and not path_key.endswith("{" + matches[0] + "}/")):
            controller_type = ControllerType.BASE
        elif len(matches) == 1 and (path_key.endswith("{" + matches[0] + "}") or path_key.endswith("{" + matches[0] + "}/")):
            controller_type = ControllerType.ITEM
        else:
            controller_type = ControllerType.COLLECTION
        return controller_type

    def _controller_method_from_path_method(self, method_name, method_obj):
        """
        Parses an operation object and converts it to a method object, to be included in a controller object.

        Example:
        {
            'get': {
                'method': 'get',
                'query_params': [
                    'limit',
                    'sort'
                ],
                'response': {
                    'success_code': '200',
                    'model': 'DogModel',
                    'mschema': 'DogSchema'
                },
                'request': {},
                'supported': true
            }
        }
        :return: dictionary representation of a controller method
        """

        method = dict()
        method["method"] = method_name
        method["query_params"] = []
        if method_obj.get("parameters"):
            method["query_params"] = [p["name"] for p in method_obj.get("parameters") if p["in"] == "query"]
        method["response"] = dict()
        method["request"] = dict()
        method["supported"] = True

        self._controller_method_response_from_path_response(method, method_obj["responses"])

        if method_obj.get("requestBody"):
            self._controller_method_request_from_path_request(method, method_obj["requestBody"])
        return method

    def _controller_method_request_from_path_request(self, method, request_obj):
        """
        Adds to the controller method's reponse object based on the OpenAPI response object.
        :param method: object to be updated with the new response
        :param request_obj: OpenAPI response object
        :return:
        """
        content = request_obj.get("content").get(CONTENT_TYPE)

        method["request"]["model"] = self._get_model_name_from_schema(content.get("schema"))
        method["request"]["mschema"] = self._get_mschema_name_from_schema(content.get("schema"))

    def _controller_method_response_from_path_response(self, method, response_obj):
        """
        Adds to the controller method's reponse object based on the OpenAPI response object.
        :param method: object to be updated with the new response
        :param response_obj: OpenAPI response object
        :return:
        """
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

    def _determine_relationship(self,
                                current_schema_name,
                                ref_type_to_schema,
                                referenced_schema):
        """
        Determines the type of relationship the current schema has with the referenced schema.

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
                            return RelationshipType.ONE_TO_ONEOF
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

        :param ref: reference link, example: #/components/schemas/Pet
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
        split = re.split(VAR_PATTERN, path_uri)[0].split("/")
        if split[-1] != "":
            n = split[-1]
        else:
            n = split[-2]

        naming["resource"] = self.engine.singular_noun(n.title()) or n.title()
        names = dict()
        names["controller"] = naming["resource"].replace("-", "")

        controller_type = self._determine_controller_type(path_uri)
        if controller_type == ControllerType.ITEM:
            names["controller"] = names["controller"] + "Item"
        elif controller_type == ControllerType.COLLECTION:
            names["controller"] = names["controller"] + "Collection"

        names["controller"] = names["controller"] + "Controller"
        names["resource"] = naming["resource"].replace("-", "")
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
