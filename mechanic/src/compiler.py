import os
import json
import pkg_resources
import re
import enum
import copy

# third party
import yaml
import yamlordereddictloader
import inflect
from yamlordereddictloader import OrderedDict

# project
import mechanic.src.utils as utils
import mechanic.src.reader as reader
from mechanic.src.merger import Merger

engine = inflect.engine()

data_map = {
    "integer": "Integer",
    "string": "String",
    "number": "Float",
    "boolean": "Boolean"
}

NAMESPACE_EXT = "x-mechanic-namespace"
EMBEDDABLE_EXT = "x-mechanic-embeddable"
VAR_PATTERN = r'{([\w_-]*)}'

SUPPORTED_CONTENT_TYPE = "application/json"
NATIVE_TYPES = ["integer", "number", "string", "boolean"]
PRIMARY_KEY_LENGTH = 36
# HTTP_METHODS = ["get", "put", "post", "delete", "options", "head", "patch", "trace"]
MECHANIC_SUPPORTED_HTTP_METHODS = ["get", "put", "post", "delete"]


class ControllerType(enum.Enum):
    BASE = "mechanic.base.controllers.BaseController", ""
    ITEM = "mechanic.base.controllers.BaseItemController", "Item"
    COLLECTION = "mechanic.base.controllers.BaseCollectionController", "Collection"


class RelationshipType(enum.IntEnum):
    m2m = 100
    o2m = 50
    o2o = 10


class Compiler(object):
    def __init__(self, options, mechanic_file_path="", output="mech-compiled.yaml"):
        self.options = options
        self.oapi_file = os.path.abspath(
            os.path.realpath(os.path.join(os.path.dirname(mechanic_file_path), options[reader.OPENAPI3_FILE_KEY])))
        self.merger = Merger(self.oapi_file, os.path.dirname(mechanic_file_path) + "/temp.yaml")
        self.merger.merge()
        self.oapi_obj = self.merger.oapi_obj
        self.models = dict()
        self.schemas = dict()
        self.controllers = dict()
        self.resources = dict()
        self.namespaces = dict()
        self.foreign_keys = dict()
        self.many_to_many = dict()
        self.version = self.oapi_obj.get("info", {}).get("version", "0.0.1").replace(".", "").replace("-", "").replace("_", "")
        self.output = output

    def compile(self):
        self.build_models_pass1()
        self.build_models_pass2()
        self.build_models_pass3()
        self.build_models_pass4()
        self.build_models_pass5()
        self.build_models_pass6()

        self.build_mschemas_pass1()
        self.build_mschemas_pass2()
        self.build_mschemas_pass3()
        self.build_controllers_pass1()

        self.write_to_file()

    def write_to_file(self):
        self.mech_obj = {
            "openapi_file_location": self.oapi_file,
            "version": self.version,
            "resources": self.resources,
            "models": self.models,
            "schemas": self.schemas,
            "foreign_keys": self.foreign_keys,
            "many_to_many": self.many_to_many,
            "controllers": self.controllers,
            "namespaces": self.namespaces
        }

        with open(self.output, "w") as f:
            if self.output.endswith(".json"):
                json_data = json.dumps(self.mech_obj, indent=3)
                f.write(json_data)
            elif self.output.endswith(".yaml") or self.output.endswith(".yml"):
                yaml_data = yaml.dump(OrderedDict(self.mech_obj),
                                      Dumper=yamlordereddictloader.Dumper,
                                      default_flow_style=False)
                f.write(yaml_data)
            else:
                raise SyntaxError("Specified output file is not of correct format. Must be either json or yaml.")

    def build_models_pass1(self):
        """
        Pass 1 only handles properties, no relationships
        :return:
        """
        for schema_name, schema_obj in self.oapi_obj["components"]["schemas"].items():
            namespace = schema_obj.get(NAMESPACE_EXT, self.options[reader.DEFAULT_NAMESPACE_KEY])
            model_name = self._get_model_name_from_pattern(schema_name,
                                                           namespace=namespace,
                                                           version=self.version)
            model = self._init_model(model_name)
            model["namespace"] = namespace

            base_model = self._get_base_model_from_options(model_name,
                                                           namespace=model["namespace"],
                                                           version=self.version)
            path = self._get_model_path_from_options(namespace=model["namespace"],
                                                     version=self.version)

            model["module_path"] = path
            model["base_model_path"] = base_model.rsplit(".", 1)[0]
            model["base_model_name"] = base_model.rsplit(".", 1)[1]
            model["db_schema"] = self._get_db_schema_name_from_options(model_name,
                                                                       model["namespace"],
                                                                       namespace=model["namespace"],
                                                                       version=self.version)
            model["db_tablename"] = self._get_tablename_from_options(model_name,
                                                                     model["db_tablename"],
                                                                     namespace=model["namespace"],
                                                                     version=self.version)

            self._init_namespace(model["namespace"])

            # Handle properties
            if schema_obj.get("type") in NATIVE_TYPES:
                raise SyntaxError("mechanic currently does not support schemas that are not of type 'object' or 'type' "
                                  "array. Schemas of type 'array' must have the 'items' attribute contain a '$ref' to "
                                  "another schema. Consider changing the schema type to an 'object' and adding "
                                  "properties. Object in error: %s" % (schema_name))
            elif schema_obj.get("type") == "array" and not schema_obj.get("items", {}).get("$ref"):
                raise SyntaxError("mechanic currently does not support schemas that are not of type 'object' or 'type' "
                                  "array. Schemas of type 'array' must have the 'items' attribute contain a '$ref' to "
                                  "another schema. Consider changing the schema type to an 'object' and adding "
                                  "properties. Object in error: %s" % (schema_name))

            for prop_name, prop_obj in schema_obj.get("properties", {}).items():
                if prop_obj.get("type") in NATIVE_TYPES:
                    self._add_column(prop_name, model, prop_obj, prop_name, schema_obj)

            self._put_resource_to_mechanic(model, model_name, schema_name, "model")

    def build_models_pass2(self):
        """
        Pass 2 handles allOf composition
        """
        for schema_name, schema_obj in self.oapi_obj["components"]["schemas"].items():
            namespace = schema_obj.get(NAMESPACE_EXT, self.options[reader.DEFAULT_NAMESPACE_KEY])
            model_name = self._get_model_name_from_pattern(schema_name,
                                                           namespace=namespace,
                                                           version=self.version)
            existing_model = self.models.get(model_name)
            if not existing_model:
                # model has been excluded
                continue

            # Handle allOf
            for item in schema_obj.get("allOf", {}):
                if item.get("type") in NATIVE_TYPES:
                    raise SyntaxError("Objects in 'allOf' arrays must either be of type 'object' or a '$ref'.")
                elif item.get("type") == "object":
                    for prop_name, prop_obj in item.get("properties", {}).items():
                        self._add_column(prop_name, existing_model, prop_obj, prop_name, schema_obj)
                elif item.get("$ref"):
                    obj = self._follow_reference_link(item.get("$ref"))
                    for prop_name, prop_obj in obj.get("properties", {}).items():
                        if prop_obj.get("type") in NATIVE_TYPES:
                            self._add_column(prop_name, existing_model, prop_obj, prop_name, obj)
                        elif prop_obj.get("$ref"):
                            self._add_regular_relationship(existing_model, model_name, prop_obj.get("$ref"), schema_name)
                        else:
                            raise SyntaxError("mechanic does not support 'allOf' if the referenced objects have 'oneOf'"
                                              " attributes. ")

    def build_models_pass3(self):
        """
        Pass 3 handles oneOf and oneOf relationships.
        """
        for schema_name, schema_obj in self.oapi_obj["components"]["schemas"].items():
            namespace = schema_obj.get(NAMESPACE_EXT, self.options[reader.DEFAULT_NAMESPACE_KEY])
            model_name = self._get_model_name_from_pattern(schema_name,
                                                           namespace=namespace,
                                                           version=self.version)
            existing_model = self.models.get(model_name)
            if not existing_model:
                # model has been excluded
                continue

            # Handle top-level oneOf
            for oneof_item in schema_obj.get("oneOf", []):
                self._validate_oneof_embeddable(schema_obj, schema_name, "")
                if oneof_item.get("type") == "string":
                    pass
                elif oneof_item.get("$ref"):
                    self._add_regular_relationship(existing_model,
                                                   model_name,
                                                   oneof_item.get("$ref"),
                                                   schema_name.lower(),
                                                   embeddable=True)

            # Handle oneOf properties
            for prop_name, prop_obj in schema_obj.get("properties", {}).items():
                for item in prop_obj.get("oneOf", []):
                    self._validate_oneof_embeddable(prop_obj, schema_name, prop_name)
                    if item.get("type") == "string":
                        pass
                    elif item.get("$ref"):
                        self._add_regular_relationship(existing_model,
                                                       model_name,
                                                       item.get("$ref"),
                                                       prop_name,
                                                       embeddable=True)

                if prop_obj.get("type") == "array":
                    # Handle array of oneOf
                    for arr_oneof in prop_obj.get("items", {}).get("oneOf", []):
                        self._validate_oneof_embeddable(prop_obj.get("items", {}), schema_name, prop_name)
                        if arr_oneof.get("type") == "string":
                            pass
                        elif arr_oneof.get("$ref"):
                            self._add_regular_relationship(existing_model,
                                                           model_name,
                                                           arr_oneof.get("$ref"),
                                                           prop_name,
                                                           uselist=True,
                                                           embeddable=True)

    def build_models_pass4(self):
        """
        Pass 4 handles relationships NOT in oneOf's
        """
        for schema_name, schema_obj in self.oapi_obj["components"]["schemas"].items():
            namespace = schema_obj.get(NAMESPACE_EXT, self.options[reader.DEFAULT_NAMESPACE_KEY])
            model_name = self._get_model_name_from_pattern(schema_name,
                                                           namespace=namespace,
                                                           version=self.version)
            existing_model = self.models.get(model_name)
            if not existing_model:
                # model has been excluded
                continue

            if schema_obj.get("type") == "array":
                ref = schema_obj.get("items").get("$ref")
                if ref is None:
                    raise SyntaxError(
                        "mechanic currently does not support schemas with type 'array' that do not have the 'items' "
                        "attribute as a '$ref' to another schema. Consider changing items object to reference a "
                        "schema. Object in error: %s" % (schema_name))

                self._add_regular_relationship(existing_model,
                                               model_name,
                                               ref,
                                               schema_name.lower(),
                                               uselist=True,
                                               backref=True,
                                               nested=True)

            for prop_name, prop_obj in schema_obj.get("properties", {}).items():
                if prop_obj.get("type") == "array":
                    # make foreign key
                    # determine rel type
                    if prop_obj.get("items").get("type") in NATIVE_TYPES:
                        raise SyntaxError("mechanic currently does not support 'array' of primitive OpenAPI 3.0 data "
                                          "types. Consider changing the array to reference an object that has one "
                                          "property containing the intended data. "
                                          "Object in error: %s.%s" % (schema_name, prop_name))
                    elif prop_obj.get("items").get("type") == "object":
                        raise SyntaxError("mechanic currently does not support nested schemas without referencing. "
                                          "Consider moving the nested object definition to its own schema definition, "
                                          "and referencing that object using the '$ref' attribute. "
                                          "Object in error: %s.%s" % (schema_name, prop_name))
                    elif prop_obj.get("items").get("type") == "array":
                        raise SyntaxError("mechanic currently does not support nested arrays. Consider moving the "
                                          "nested array definition to its own schema definition, "
                                          "and referencing that object using the '$ref' attribute. "
                                          "Object in error: %s.%s" % (schema_name, prop_name))
                    elif prop_obj.get("items").get("$ref"):
                        ref = prop_obj.get("items").get("$ref")
                        self._add_regular_relationship(existing_model,
                                                       model_name,
                                                       ref,
                                                       prop_name,
                                                       uselist=True,
                                                       backref=schema_name.lower(),
                                                       nested=True)
                elif prop_obj.get("$ref"):
                    ref = prop_obj.get("$ref")
                    self._add_regular_relationship(existing_model,
                                                   model_name,
                                                   ref, prop_name,
                                                   uselist=False,
                                                   backref=schema_name.lower(),
                                                   nested=True)

    def build_models_pass5(self):
        """
        Pass 5 finding the correct foreign keys
        """
        fkey_copy = copy.deepcopy(self.foreign_keys)
        for fkey_models, fkey in fkey_copy.items():
            model_a = fkey_models.split(".")[0]
            model_b = fkey_models.split(".")[1]
            rel_type = RelationshipType[fkey["rel"]]

            # see if there is a foreign key for the reverse relationship
            reversed_models = model_b + "." + model_a

            # see if the relationship is overridden in config file
            overridden_rel_types = self.options[reader.OVERRIDE_MANY_TO_MANY_KEY]
            for item in overridden_rel_types:
                if (item["model1"] == model_a and item["model2"] == model_b) or \
                        (item["model1"] == model_b and item["model2"] == model_a):
                    self._add_many_to_many(model_a, model_b)
                    self.foreign_keys.pop(fkey_models, None)
                    self.foreign_keys.pop(reversed_models, None)

            reverse_fkey = self.foreign_keys.get(reversed_models)

            # If the reversed_models == fkey_models, that means it is a self referential foreign key, in which case no
            # need to remove any key.
            if reverse_fkey and reversed_models != fkey_models:
                reverse_rel_type = RelationshipType[reverse_fkey["rel"]]

                if rel_type == RelationshipType.o2m and reverse_rel_type == RelationshipType.o2m:
                    rel_type = RelationshipType.m2m
                    reverse_rel_type = RelationshipType.m2m
                    self.foreign_keys[reversed_models]["rel"] = reverse_rel_type.name
                    self.foreign_keys[fkey_models]["rel"] = rel_type.name

                    # add m2m
                    self._add_many_to_many(model_a, model_b)

                # We only want one foreign key between the 2 models, so remove one based on the rel_type
                if rel_type > reverse_rel_type:
                    if self.foreign_keys.get(reversed_models):
                        self.foreign_keys.pop(reversed_models)
                elif rel_type < reverse_rel_type:
                    if self.foreign_keys.get(fkey_models):
                        self.foreign_keys.pop(fkey_models)
                else:
                    if rel_type == RelationshipType.m2m and reverse_rel_type == RelationshipType.m2m:
                        self._add_many_to_many(model_a, model_b)
                    else:
                        # remove one of them cause they each have the same rel
                        self.foreign_keys.pop(fkey_models)

    def build_models_pass6(self):
        """
        Pass 6 attaches the foreign keys to the models
        """
        for fkey_models, fkey in self.foreign_keys.items():
            # Handle many to many first
            if fkey["rel"] == RelationshipType.m2m:
                # model_a = fkey_models.split(".")[0]
                # model_b = fkey_models.split(".")[1]
                # raise SyntaxError("mechanic does not currently support many to many relationships: %s:%s" %
                #                   (model_a, model_b))
                pass
            else:
                on_model = fkey["on_model"]
                foreign_key_name = fkey["name"]
                foreign_key = self._init_model_col()
                foreign_key["type"] = self._map_openapi_type_to_sqlalchemy_type("string")
                foreign_key["length"] = PRIMARY_KEY_LENGTH
                foreign_key["foreign_key"] = fkey["key"]
                self.models[on_model]["columns"][foreign_key_name] = foreign_key

    def build_mschemas_pass1(self):
        """
        Pass 1 handles schemas that are associated with models.
        """
        # If model already built, use that
        for schema_name, schema_obj in self.oapi_obj["components"]["schemas"].items():
            namespace = schema_obj.get(NAMESPACE_EXT, self.options[reader.DEFAULT_NAMESPACE_KEY])
            mschema_name = self._get_mschema_name_from_pattern(schema_name,
                                                               namespace=namespace,
                                                               version=self.version)
            resource_model_name = self.resources.get(schema_name, {}).get("model")
            existing_model_obj = self.models.get(resource_model_name)
            mschema = self._init_mschema(mschema_name)
            mschema["namespace"] = namespace
            is_model_schema = resource_model_name and existing_model_obj
            base_mschema = self._get_base_mschema_from_options(mschema_name,
                                                               model_schema=is_model_schema,
                                                               namespace=mschema["namespace"],
                                                               version=self.version)

            path = self._get_mschema_path_from_options(namespace=namespace,
                                                       version=self.version)

            mschema["module_path"] = path
            mschema["base_schema_path"] = base_mschema.rsplit(".", 1)[0]
            mschema["base_schema_name"] = base_mschema.rsplit(".", 1)[1]

            # self.namespaces[mschema["namespace"]]["schemas"].append(mschema_name)

            if is_model_schema:
                # only need to set the model
                mschema["namespace"] = namespace
                mschema["comment"] = schema_obj.get("description")
                mschema["model"] = resource_model_name
            # Set in mechanic object
            self._put_resource_to_mechanic(mschema, mschema_name, schema_name, "schema")

    def build_mschemas_pass2(self):
        """
        Pass 2 handles creating MechanicEmbeddable/Nested Marshmallow fields"
        """
        for schema_name, schema_obj in self.oapi_obj["components"]["schemas"].items():
            namespace = schema_obj.get(NAMESPACE_EXT, self.options[reader.DEFAULT_NAMESPACE_KEY])
            mschema_name = self._get_mschema_name_from_pattern(schema_name,
                                                               namespace=namespace,
                                                               version=self.version)

            existing_mschema = self.schemas.get(mschema_name)
            if not existing_mschema:
                # mschema has been excluded
                continue

            resource_model_name = self.resources.get(schema_name, {}).get("model")
            existing_model_obj = self.models.get(resource_model_name)

            if resource_model_name and existing_model_obj:
                for rel_name, rel_obj in existing_model_obj["relationships"].items():
                    if rel_obj["embeddable"]:
                        rel_model = rel_obj["model"]
                        existing_mschema["embeddable"][rel_name] = self._find_schema_from_model_name(rel_model)
                    elif rel_obj["nested"]:
                        rel_model = rel_obj["model"]

                        if not existing_mschema["nested"].get(rel_name):
                            existing_mschema["nested"][rel_name] = dict()
                        existing_mschema["nested"][rel_name]["schema"] = self._find_schema_from_model_name(rel_model)
                        existing_mschema["nested"][rel_name]["many"] = rel_obj["uselist"]

    def build_mschemas_pass3(self):
        """
        Pass 3 handles creating Marshmallow schemas for objects that do not have a model already created for them.
        """
        for schema_name, schema_obj in self.oapi_obj["components"]["schemas"].items():
            namespace = schema_obj.get(NAMESPACE_EXT, self.options[reader.DEFAULT_NAMESPACE_KEY])
            mschema_name = self._get_mschema_name_from_pattern(schema_name,
                                                               namespace=namespace,
                                                               version=self.version)

            existing_mschema = self.schemas.get(mschema_name)
            if not existing_mschema:
                # mschema has been excluded
                continue

            resource_model_name = self.resources.get(schema_name, {}).get("model")
            existing_model_obj = self.models.get(resource_model_name)

            if not (resource_model_name and existing_model_obj):
                # Handle properties
                if schema_obj.get("type") in NATIVE_TYPES:
                    raise SyntaxError("mechanic currently does not support schemas that are not of type 'object' or 'type' "
                                      "array. Schemas of type 'array' must have the 'items' attribute contain a '$ref' to "
                                      "another schema. Consider changing the schema type to an 'object' and adding "
                                      "properties. Object in error: %s" % (schema_name))
                elif schema_obj.get("type") == "array" and not schema_obj.get("items", {}).get("$ref"):
                    raise SyntaxError("mechanic currently does not support schemas that are not of type 'object' or 'type' "
                                      "array. Schemas of type 'array' must have the 'items' attribute contain a '$ref' to "
                                      "another schema. Consider changing the schema type to an 'object' and adding "
                                      "properties. Object in error: %s" % (schema_name))

                for prop_name, prop_obj in schema_obj.get("properties", {}).items():
                    if prop_obj.get("type") in NATIVE_TYPES:
                        self._add_field(prop_name, existing_mschema, prop_obj, prop_name, schema_obj)

    def build_controllers_pass1(self):
        for path_uri, path_obj in self.oapi_obj["paths"].items():
            controller = self._init_controller()

            namespace = path_obj.get(NAMESPACE_EXT, self.options[reader.DEFAULT_NAMESPACE_KEY])
            controller["namespace"] = namespace
            controller["oapi_uri"] = path_uri
            matches = re.findall(VAR_PATTERN, path_uri)

            if len(matches) > 1:
                print("WARNING: You have defined a URI that has more than one variable. If you intend to use mechanic's"
                      "default base controllers, you will need to manually override the generated controller to handle"
                      "multiple path variables.")
                controller["uri"] = re.sub(VAR_PATTERN, r'<string:\1>', path_uri).replace("-", "_")
            else:
                controller["uri"] = re.sub(VAR_PATTERN, r'<string:resource_id>', path_uri).replace("-", "_")

            # Need to determine controller type name based on URI. From there get naming pattern
            controller_type = self._determine_controller_type(path_uri)
            # Default resource name in case one is not found.
            resource_name = path_uri.replace("/", "") \
                                    .replace("-", "") \
                                    .replace("{", "") \
                                    .replace("}", "") \
                                    .title()
            controller["resource"] = resource_name
            controller_name = self._get_controller_name_from_pattern(resource_name=resource_name,
                                                                     controller_type=controller_type,
                                                                     namespace=namespace)

            for method_name, method_obj in path_obj.items():
                if method_name in MECHANIC_SUPPORTED_HTTP_METHODS:
                    for response_code, response_obj in method_obj.get("responses", {}).items():
                        if response_code.startswith("2"):
                            response = self._init_controller_response()
                            response["code"] = response_code
                            response["comment"] = method_obj.get("summary")

                            ref = response_obj.get("content", {}).get(SUPPORTED_CONTENT_TYPE, {}).get("schema", {}).get("$ref")
                            if not ref:
                                ref = response_obj.get("content", {}).get(SUPPORTED_CONTENT_TYPE, {}).get("schema", {}).get("items", {}).get("$ref")

                            if not ref:
                                response["model"] = None
                                response["schema"] = None
                            else:
                                schema_name = ref.split("/")[-1]
                                response["model"] = self.resources.get(schema_name, {}).get("model")
                                response["schema"] = self.resources.get(schema_name, {}).get("schema")

                                resource_name = schema_name

                                # if controller.get("change"):
                                controller["resource"] = resource_name
                                controller["change"] = False

                                # Rename controller if there is a resource defined in the responses.
                                controller_name = self._get_controller_name_from_pattern(resource_name=resource_name,
                                                                                         controller_type=controller_type,
                                                                                         namespace=namespace)
                            controller["responses"][method_name] = response

                            # assign this controller to the model
                            if response.get("model"):
                                self.models[response["model"]]["controller"] = controller_name.lower()
                                self.models[response["model"]]["namespace"] = controller["namespace"]

                    requestbody_obj = method_obj.get("requestBody", {})
                    request = self._init_controller_request()
                    request["comment"] = method_obj.get("summary")

                    ref = requestbody_obj.get("content", {}).get(SUPPORTED_CONTENT_TYPE, {}).get("schema", {}).get("$ref")
                    if not ref:
                        request["model"] = None
                        request["schema"] = None
                    else:
                        schema_name = ref.split("/")[-1]
                        request["model"] = self.resources.get(schema_name, {}).get("model")
                        request["schema"] = self.resources.get(schema_name, {}).get("schema")
                    controller["requests"][method_name] = request

                    if request.get("model"):
                        self.models[request["model"]]["controller"] = controller_name.lower()
                        self.models[request["model"]]["namespace"] = controller["namespace"]

            path = self._get_controller_path_from_options(namespace=controller["namespace"],
                                                          version=self.version)
            base_controller = self._get_base_controller_from_options(controller_name,
                                                                     controller_type=controller_type,
                                                                     namespace=controller["namespace"],
                                                                     version=self.version)
            controller["module_path"] = path
            controller["base_controller_path"] = base_controller.rsplit(".", 1)[0]
            controller["base_controller_name"] = base_controller.rsplit(".", 1)[1]
            self._put_controller_to_mechanic(controller_name, controller)

    def _add_many_to_many(self, model1_name, model2_name):
        model1 = self.models[model1_name]
        model2 = self.models[model2_name]

        sorted_names = [model1["db_tablename"], model2["db_tablename"]]
        sorted_names.sort()
        table_name = "_".join(sorted_names)

        # verify namespace and db_schema match
        if model1["namespace"] != model2["namespace"]:
            raise SyntaxError("namespace attributes do not match for models %s and %s" % (model1_name, model2_name))
        if model1["db_schema"] != model2["db_schema"]:
            raise SyntaxError("db_schema attributes do not match for models %s and %s" % (model1_name, model2_name))

        m2m = {
            "namespace": model1["namespace"],
            "db_tablename": table_name,
            "db_schema": model1["db_schema"],
            "fkeys": {
                model1_name.lower() + "_id": model1["db_schema"] + "." +
                                             model1["db_tablename"] + "." +
                                             model1["primary_key"],
                model2_name.lower() + "_id": model2["db_schema"] + "." +
                                             model2["db_tablename"] + "." +
                                             model2["primary_key"],
            }
        }

        # If there is a relationship defined on either model, add the secondary option to point at the association
        # table.
        for rel_name, rel in model1.get("relationships", {}).items():
            if rel["model"] == model2_name:
                rel["secondary"] = table_name

        for rel_name, rel in model2.get("relationships", {}).items():
            if rel["model"] == model1_name:
                rel["secondary"] = table_name

        self.many_to_many[table_name] = m2m

    def _init_namespace(self, namespace):
        if not self.namespaces.get(namespace):
            self.namespaces[namespace] = dict()
            self.namespaces[namespace]["models"] = []
            self.namespaces[namespace]["schemas"] = []
            self.namespaces[namespace]["controllers"] = []

    def _determine_controller_type(self, path_uri):
        """
        Determines the type of controller based on the uri pattern. If the uri pattern is overridden in the mechanic
        file, then that controller type will be used instead. Otherwise, the pattern regex's are:

        Item: a uri that ends with a variable, and has exactly one variable. Ex: /api/groceries/apples/{appleid}, /v1/mylong/url/with/a/variable/at/the/end/{id}
        Collection: a uri with no variables in it: /api/groceries/apples

        If a URI does not match either of these, then it will not have a 'controller_type'.

        :param path_uri
        :return: ControllerType value string
        """
        matches = re.findall(VAR_PATTERN, path_uri)
        if len(matches) > 1:
            controller_type = ControllerType.BASE
        elif matches and (not path_uri.endswith("{" + matches[0] + "}") and not path_uri.endswith("{" + matches[0] + "}/")):
            controller_type = ControllerType.BASE
        elif len(matches) == 1 and (path_uri.endswith("{" + matches[0] + "}") or path_uri.endswith("{" + matches[0] + "}/")):
            controller_type = ControllerType.ITEM
        else:
            controller_type = ControllerType.COLLECTION

        # Get the enum's second value
        ctype = controller_type.value[1]
        # If overridden in build file, use that instead
        override = self.options[reader.OVERRIDE_CONTROLLER_TYPE_KEY]
        ctype = override.get(path_uri, ctype)
        return ctype

    def _find_schema_from_model_name(self, model_name):
        for res, res_obj in self.resources.items():
            if res_obj.get("model") == model_name:
                return res_obj.get("schema")

    def _init_mschema(self, schema_name):
        return {
            "model": None,
            "strict": True,
            "namespace": self.options[reader.DEFAULT_NAMESPACE_KEY],
            "comment": schema_name,
            "base_schema_path": None,
            "base_schema_name": None,
            "module_path": None,
            "fields": dict(),
            "embeddable": dict(),
            "nested": dict()
        }

    def _init_controller(self, controller_name=None):
        return {
            "responses": {},
            "requests": {},
            "comment": controller_name,
            "base_controller_path": None,
            "base_controller_name": None,
            "module_path": None,
            "namespace": self.options[reader.DEFAULT_NAMESPACE_KEY],
            "resource": None
        }

    def _init_controller_response(self):
        return {
            "code": 200,
            "model": None,
            "schema": None,
            "comment": None
        }

    def _init_controller_request(self):
        return {
            "model": None,
            "schema": None,
            "comment": None,
            "query_params": []
        }

    def _put_resource_to_mechanic(self, obj, obj_name, oapi_schema_name, type):
        if not self.resources.get(oapi_schema_name):
            self.resources[oapi_schema_name] = dict()

        if type == "model" and not self._is_model_excluded(oapi_schema_name):
            self.models[obj_name] = obj
            self.resources[oapi_schema_name][type] = obj_name
            self._init_namespace(obj["namespace"])
            self.namespaces[obj["namespace"]]["models"].append(obj_name)
        elif type == "schema" and not self._is_schema_excluded(oapi_schema_name):
            self.schemas[obj_name] = obj
            self.resources[oapi_schema_name][type] = obj_name
            self._init_namespace(obj["namespace"])
            self.namespaces[obj["namespace"]]["schemas"].append(obj_name)

    def _put_controller_to_mechanic(self, controller_name, controller):
        self.controllers[controller_name] = controller
        self._init_namespace(controller["namespace"])
        self.namespaces[controller["namespace"]]["controllers"].append(controller_name)

    def _is_model_excluded(self, oapi_schema_name):
        excluded_models = self.options[reader.EXCLUDE_MODEL_GENERATION_KEY]
        return oapi_schema_name in excluded_models or (excluded_models == "all")

    def _is_schema_excluded(self, oapi_schema_name):
        excluded_schemas = self.options[reader.EXCLUDE_SCHEMA_GENERATION_KEY]
        return oapi_schema_name in excluded_schemas or (excluded_schemas == "all")

    def _validate_oneof_embeddable(self, schema_obj, schema_name, prop_name):
        if not schema_obj.get(EMBEDDABLE_EXT):
            raise SyntaxError("mechanic does not currently support 'oneOf' schemas that are not "
                              "'embeddable'. See docs for more details. Object in error: %s.%s"
                              % (schema_name, prop_name))
        elif len(schema_obj.get("oneOf", [])) != 2:
            raise SyntaxError("mechanic only supports 'oneOf' schemas that are 'embeddable' and have exactly 1 "
                              "string type and 1 reference type. See docs for more details. Object in error: %s.%s"
                              % (schema_name, prop_name))
        elif any(x.get("type") != "string" and x.get("$ref") is None for x in schema_obj.get("oneOf", [])):
            raise SyntaxError("zzzzmechanic only supports 'oneOf' schemas that are 'embeddable' and have exactly 1 "
                              "string type and 1 reference type. See docs for more details. Object in error: %s.%s"
                              % (schema_name, prop_name))

    def _add_regular_relationship(self,
                                  existing_model,
                                  model_name,
                                  ref,
                                  prop_name,
                                  uselist=False,
                                  embeddable=False,
                                  nested=False,
                                  backref=None,
                                  back_populates=None):
        rel = self._init_rel()
        ref_name = ref.split("/")[-1]
        rel_name = prop_name
        rel["model"] = self._get_model_name_from_pattern(ref_name, namespace=existing_model["namespace"],
                                                         version=self.version)
        """
        if backref is True:
            rel["backref"] = rel_name
        elif backref:
            rel["backref"] = backref
            referenced_schema = self._follow_reference_link(ref)

            # If the property is already defined in the model, remove it, because the backref will handle it.
            prop = referenced_schema.get("properties", {}).get(backref, {})
            embeddable = prop.get(EMBEDDABLE_EXT, {})
            backref_exists = any(x.get("$ref", "").endswith(backref) for x in prop.get("oneOf", []))

            # if backref in self.models[rel["model"]]["columns"].keys() and embeddable and backref_exists:
            #     self.models[rel["model"]]["columns"].pop(backref)
        """
        rel["back_populates"] = back_populates
        rel["uselist"] = uselist
        rel["embeddable"] = embeddable
        rel["nested"] = nested
        existing_model["relationships"][rel_name] = rel
        self._add_foreign_key(existing_model, model_name, rel, is_list=uselist)

    def _add_column(self, column_name, existing_model, prop_obj, prop_name, schema_obj):
        col = self._init_model_col()
        col["type"] = self._map_openapi_type_to_sqlalchemy_type(prop_obj["type"])
        col["nullable"] = prop_name not in schema_obj.get("required", [])
        col["length"] = prop_obj.get("maxLength", col["length"])
        col["comment"] = prop_obj.get("description")
        existing_model["columns"][column_name] = col

    def _add_field(self, field_name, existing_mschema, prop_obj, prop_name, schema_obj):
        field = self._init_schema_field()
        field["type"] = self._map_openapi_type_to_marshmallow_type(prop_obj["type"])
        field["required"] = prop_name in schema_obj.get("required", [])
        field["maxLength"] = prop_obj.get("maxLength", field["maxLength"])
        field["load_only"] = prop_obj.get("writeOnly", field["load_only"])
        field["dump_only"] = prop_obj.get("readOnly", field["dump_only"])
        field["comment"] = prop_obj.get("description")
        existing_mschema["fields"][field_name] = field

    def _add_oneof_relationship(self, existing_model, model_name, prop_item, schema_name, uselist=False):
        rel = self._init_rel()
        ref_name = prop_item.get("$ref").split("/")[-1]
        rel_name = schema_name.lower() + "_" + ref_name.lower()
        rel["model"] = ref_name
        rel["comment"] = prop_item.get("description")
        rel["uselist"] = uselist
        existing_model["relationships"][rel_name] = rel
        self._add_foreign_key(existing_model, model_name, rel, is_list=uselist)

    def _add_foreign_key(self, existing_model, existing_model_name, relationship, is_list=False):
        foreign_key_name = existing_model_name.lower() + "_id"
        foreign_key = existing_model["db_schema"] + "." + \
                      existing_model["db_tablename"] + "." + \
                      existing_model["primary_key"]

        keys = [existing_model_name, relationship["model"]]
        keys = ".".join(keys)
        rel_type = RelationshipType.o2m if is_list else RelationshipType.o2o

        self.foreign_keys[keys] = {
            "on_model": relationship["model"],
            "db_schema": existing_model["db_schema"],
            "rel": rel_type.name,
            "key": foreign_key,
            "name": foreign_key_name,
            "secondary_key": None,
            "secondary_name": None
        }

        # print(self.foreign_keys[keys])

        # relationship["foreign_keys"].append(foreign_key_name)
        # relationship["foreign_keys"].append(foreign_key)

    def _map_openapi_type_to_sqlalchemy_type(self, oapi_type):
        oapi_to_sql_alchemy_map = {
            "integer": "Integer",
            "string": "String",
            "number": "Float",
            "boolean": "Boolean"
        }
        return oapi_to_sql_alchemy_map[oapi_type]

    def _map_openapi_type_to_marshmallow_type(self, oapi_type):
        return self._map_openapi_type_to_sqlalchemy_type(oapi_type)

    def _get_model_name_from_pattern(self, schema_name, namespace=None, version=None):
        model_name = utils.replace_template_var(self.options[reader.MODELS_NAME_PATTERN_KEY],
                                                resource=schema_name,
                                                namespace=namespace,
                                                version=version)
        model_name = model_name.replace(".", "").replace("-", "").replace("_", "")
        return model_name

    def _get_mschema_name_from_pattern(self, schema_name, namespace=None, version=None):
        mschema_name = utils.replace_template_var(self.options[reader.SCHEMAS_NAME_PATTERN_KEY],
                                                resource=schema_name,
                                                namespace=namespace,
                                                version=version)
        mschema_name = mschema_name.replace(".", "").replace("-", "").replace("_", "")
        return mschema_name

    def _get_controller_name_from_pattern(self, resource_name=None, controller_type=None, namespace=None, version=None):
        controller_name = utils.replace_template_var(self.options[reader.CONTROLLERS_NAME_PATTERN_KEY],
                                                     resource=resource_name,
                                                     namespace=namespace,
                                                     controller_type=controller_type,
                                                     version=version)
        controller_name = controller_name.replace(".", "").replace("-", "").replace("_", "")
        return controller_name

    def _get_db_schema_name_from_options(self, model_name, default_schemaname, namespace=None, version=None):
        models_path_key = utils.replace_template_var(self.options[reader.MODELS_PATH_KEY],
                                                     namespace=namespace,
                                                     version=version)
        model_path = models_path_key.replace("/", ".").replace(".py", "") + "." + model_name
        overridden_schemanames = self.options[reader.OVERRIDE_DB_SCHEMA_NAMES_KEY]
        schemaname = default_schemaname

        if not isinstance(overridden_schemanames, list):
            raise SyntaxError("'" + reader.OVERRIDE_DB_SCHEMA_NAMES_KEY + "' must be a list." )

        for item in overridden_schemanames:
            table_for = item.get("for")
            if table_for:
                if model_path == table_for:
                    schemaname = item.get("with")
            else:
                raise SyntaxError("The 'for' attribute is required in the '" +
                                  reader.OVERRIDE_DB_SCHEMA_NAMES_KEY +
                                  "' option.")
        return schemaname

    def _get_tablename_from_options(self, model_name, default_tablename, namespace=None, version=None):
        models_path_key = utils.replace_template_var(self.options[reader.MODELS_PATH_KEY],
                                                     namespace=namespace,
                                                     version=version)
        model_path = models_path_key.replace("/", ".").replace(".py", "") + "." + model_name
        overridden_tables = self.options[reader.OVERRIDE_TABLE_NAMES_KEY]
        tablename = default_tablename

        if not isinstance(overridden_tables, list):
            raise SyntaxError("'" + reader.OVERRIDE_TABLE_NAMES_KEY + "' must be a list." )

        for item in overridden_tables:
            table_for = item.get("for")
            if table_for:
                if model_path == table_for:
                    tablename = item.get("with")
            else:
                raise SyntaxError("The 'for' attribute is required in the '" +
                                  reader.OVERRIDE_TABLE_NAMES_KEY +
                                  "' option.")
        return tablename

    def _get_base_model_from_options(self, model_name, namespace=None, version=None):
        models_path_key = utils.replace_template_var(self.options[reader.MODELS_PATH_KEY],
                                                     namespace=namespace,
                                                     version=version)
        model_path = models_path_key.replace("/", ".").replace(".py", "") + "." + model_name
        base_model = self.options[reader.DEFAULT_BASE_MODEL_KEY]
        overridden_base_models = self.options[reader.OVERRIDE_BASE_MODEL_KEY]

        if not isinstance(overridden_base_models, list):
            raise SyntaxError("'" + reader.OVERRIDE_BASE_MODEL_KEY + "' must be a list." )

        for bm in overridden_base_models:
            if bm:
                bm_for = bm.get("for")
                if bm_for:
                    if isinstance(bm_for, str):
                        if bm_for.lower().strip() == "all" and model_path not in bm.get("except", []):
                            base_model = bm.get("with")
                    elif isinstance(bm_for, list):
                        if model_path in bm_for:
                            base_model = bm.get("with")
                    else:
                        raise SyntaxError("'" + reader.OVERRIDE_BASE_MODEL_KEY + "' is not formatted properly.")
                else:
                    raise SyntaxError("The 'for' attribute is required in the '" +
                                      reader.OVERRIDE_BASE_MODEL_KEY +
                                      "'option.")
        return base_model

    def _get_base_mschema_from_options(self, mschema_name, model_schema=True, namespace=None, version=None):
        schemas_path_key = utils.replace_template_var(self.options[reader.SCHEMAS_PATH_KEY],
                                                      namespace=namespace,
                                                      version=version)
        schema_path = schemas_path_key.replace("/", ".").replace(".py", "") + "." + mschema_name
        base_mschema = self.options[reader.DEFAULT_BASE_MODEL_SCHEMA_KEY] if model_schema else self.options[reader.DEFAULT_BASE_SCHEMA_KEY]
        overridden_base_schemas = self.options[reader.OVERRIDE_BASE_SCHEMA_KEY]

        for bs in overridden_base_schemas:
            if bs:
                bs_for = bs.get("for")
                if bs_for:
                    if isinstance(bs_for, str):
                        if bs_for.lower().strip() == "all" and schema_path not in bs.get("except", []):
                            base_mschema = bs.get("with")
                    elif isinstance(bs_for, list):
                        if schema_path in bs_for:
                            base_mschema = bs.get("with")
                    else:
                        raise SyntaxError("'" + reader.OVERRIDE_BASE_SCHEMA_KEY + "' is not formatted properly.")
                else:
                    raise SyntaxError("The 'for' attribute is required in the '" +
                                      reader.OVERRIDE_BASE_SCHEMA_KEY +
                                      "'option.")
        return base_mschema

    def _get_base_controller_from_options(self, controller_name, controller_type=None, namespace=None, version=None):
        controllers_path_key = utils.replace_template_var(self.options[reader.CONTROLLERS_PATH_KEY],
                                                          namespace=namespace,
                                                          version=version)
        controller_path = controllers_path_key.replace("/", ".").replace(".py", "") + "." + controller_name

        if controller_type == ControllerType.ITEM.value[1]:
            base_controller = self.options[reader.DEFAULT_BASE_ITEM_CONTROLLER_KEY]
        elif controller_type == ControllerType.COLLECTION.value[1]:
            base_controller = self.options[reader.DEFAULT_BASE_COLLECTION_CONTROLLER_KEY]
        else:
            base_controller = self.options[reader.DEFAULT_BASE_CONTROLLER_KEY]

        overridden_base_controllers = self.options[reader.OVERRIDE_BASE_CONTROLLER_KEY]

        for bc in overridden_base_controllers:
            if bc:
                bc_for = bc.get("for")
                if bc_for:
                    if isinstance(bc_for, str):
                        if bc_for.lower().strip() == "all" and controller_path not in bc.get("except", []):
                            base_controller = bc.get("with")
                    elif isinstance(bc_for, list):
                        if controller_path in bc_for:
                            base_controller = bc.get("with")
                    else:
                        raise SyntaxError("'" + reader.OVERRIDE_BASE_CONTROLLER_KEY + "' is not formatted properly.")
                else:
                    raise SyntaxError("The 'for' attribute is required in the '" +
                                      reader.OVERRIDE_BASE_CONTROLLER_KEY +
                                      "'option.")
        return base_controller

    def _get_model_path_from_options(self, namespace=None, version=None):
        models_path_key = utils.replace_template_var(self.options[reader.MODELS_PATH_KEY],
                                                      namespace=namespace,
                                                      version=version)
        return models_path_key.strip(".py").replace("/", ".")

    def _get_mschema_path_from_options(self, namespace=None, version=None):
        mschemas_path_key = utils.replace_template_var(self.options[reader.SCHEMAS_PATH_KEY],
                                                      namespace=namespace,
                                                      version=version)
        return mschemas_path_key.strip(".py").replace("/", ".")

    def _get_controller_path_from_options(self, namespace=None, version=None):
        controllers_path_key = utils.replace_template_var(self.options[reader.CONTROLLERS_PATH_KEY],
                                                          namespace=namespace,
                                                          version=version)
        return controllers_path_key.strip(".py").replace("/", ".")

    def _init_model(self, model_name):
        return {
            "columns": {},
            "relationships": {},
            "db_tablename": engine.plural_noun(model_name.replace("-", "").replace("_", "")).lower(),
            "db_schema": self.options[reader.DEFAULT_NAMESPACE_KEY],
            "namespace": self.options[reader.DEFAULT_NAMESPACE_KEY],
            "comment": model_name,
            "base_model_path": None,
            "base_model_name": None,
            "module_path": None,
            "primary_key": "identifier"
        }

    def _init_model_col(self):
        return {
            "type": None,
            "nullable": True,
            "length": "2000",
            "foreign_key": None,
        }

    def _init_schema_field(self):
        return {
            "type": None,
            "load_only": False,
            "dump_only": False,
            "maxLength": "2000",
            "required": False,
        }

    def _init_rel(self):
        return {
            "model": "",
            "backref": None,
            "back_populates": None,
            "uselist": False,
            "foreign_keys": [],
            "embeddable": False,
            "nested": False,
            "secondary": None
        }

    def _follow_reference_link(self, ref):
        """
        Gets a referenced object.
        :param ref: reference link, example: #/components/schemas/Pet
        :return: dictionary representation of the referenced object
        """
        is_link_in_current_file = True if ref.startswith("#/") else False

        if is_link_in_current_file:
            section = ref.split("/")[-3]
            object_type = ref.split("/")[-2]
            resource_name = ref.split("/")[-1]
            return self.oapi_obj[section][object_type][resource_name]
