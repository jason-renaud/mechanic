import os
import json
import pkg_resources

# third party
import yaml
import yamlordereddictloader
import inflect
from yamlordereddictloader import OrderedDict

# project
import mechanic.src.utils as utils
import mechanic.src.reader as reader

engine = inflect.engine()

data_map = {
    "integer": "Integer",
    "string": "String",
    "number": "Float",
    "boolean": "Boolean"
}

NAMESPACE_EXT = "x-mechanic-namespace"
URI_LINK_EXT = "x-mechanic-uri-link"

NATIVE_TYPES = ["integer", "number", "string", "boolean"]
PRIMARY_KEY_LENGTH = 36


class Compiler(object):
    ACTIONABLE_OBJECTS = {
        "responses": "handle_responses",
        "requestBody": "handle_requestBody",
        "parameters": "handle_parameters",
        "$ref": "handle_ref"
    }

    def __init__(self, options, mechanic_file_path="", output="tmp.json"):
        self.options = options
        self.oapi_file = os.path.abspath(
            os.path.realpath(os.path.join(os.path.dirname(mechanic_file_path), options[reader.OPENAPI3_FILE_KEY])))
        self.oapi_obj = utils.deserialize_file(self.oapi_file)
        self.models = dict()
        self.namespaces = dict()
        self.version = self.oapi_obj.get("info", {}).get("version", "0.0.1")
        self.output = output

    def compile(self):
        self.build_models_pass1()
        self.build_models_pass2()
        self.build_models_pass3()
        self.build_models_pass4()

        self.build_mschemas()
        self.build_controllers()

        self.write_to_file()

    def write_to_file(self):
        self.mech_obj = {
            "version": self.version,
            "models": self.models,
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
            model["base_model_path"] = base_model.rsplit(".", 1)[0]
            model["base_model_name"] = base_model.rsplit(".", 1)[1]
            model["db_tablename"] = self._get_tablename_from_options(model_name,
                                                                     model["db_tablename"],
                                                                     namespace=model["namespace"],
                                                                     version=self.version)

            if not self.namespaces.get(model["namespace"]):
                self.namespaces[model["namespace"]] = dict()
                self.namespaces[model["namespace"]]["models"] = []
            self.namespaces[model["namespace"]]["models"].append(model_name)

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
                else:
                    print("PASS 1 not dealing with relationships yet.")

            self.models[model_name] = model

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

            # Handle allOf
            for item in schema_obj.get("allOf", {}):
                if item.get("type") in NATIVE_TYPES:
                    print("ERROR: objects in 'allOf' arrays must either be of type 'object' or a '$ref'.")
                    exit()
                elif item.get("type") == "object":
                    for prop_name, prop_obj in item.get("properties", {}).items():
                        self._add_column(prop_name, existing_model, prop_obj, prop_name, schema_obj)
                elif item.get("$ref"):
                    obj = self._follow_reference_link(item.get("$ref"))
                    for prop_name, prop_obj in obj.get("properties", {}).items():
                        self._add_column(prop_name, existing_model, prop_obj, prop_name, obj)

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

            # Handle top-level oneOf
            for oneof_item in schema_obj.get("oneOf", []):
                if oneof_item.get("type") in NATIVE_TYPES:
                    column_name = schema_name.lower() + "_" + oneof_item.get("type").lower()
                    self._add_column(column_name, existing_model, oneof_item, schema_name, schema_obj)
                elif oneof_item.get("$ref"):
                    self._add_oneof_relationship(existing_model, model_name, oneof_item, schema_name)

            # Handle oneOf properties
            for prop_name, prop_obj in schema_obj.get("properties", {}).items():
                for item in prop_obj.get("oneOf", []):
                    if item.get("type") in NATIVE_TYPES:
                        column_name = prop_name.lower() + "_" + item.get("type").lower()
                        self._add_column(column_name, existing_model, item, prop_name, schema_obj)
                    elif item.get("$ref"):
                        self._add_oneof_relationship(existing_model, model_name, item, prop_name)

                if prop_obj.get("type") == "array":
                    # Handle array of oneOf
                    for arr_oneof in prop_obj.get("items", {}).get("oneOf", []):
                        if arr_oneof.get("type") in NATIVE_TYPES:
                            column_name = prop_name.lower() + "_array_" + arr_oneof.get("type").lower()
                            self._add_column(column_name, existing_model, arr_oneof, prop_name, schema_obj)
                        elif arr_oneof.get("$ref"):
                            self._add_oneof_relationship(existing_model, model_name, arr_oneof, prop_name, uselist=True)

    def build_models_pass4(self):
        """
        Pass 4 handles relationships not in oneOf's
        """
        for schema_name, schema_obj in self.oapi_obj["components"]["schemas"].items():
            namespace = schema_obj.get(NAMESPACE_EXT, self.options[reader.DEFAULT_NAMESPACE_KEY])
            model_name = self._get_model_name_from_pattern(schema_name,
                                                           namespace=namespace,
                                                           version=self.version)
            existing_model = self.models.get(model_name)

            if schema_obj.get("type") == "array":
                ref = schema_obj.get("items").get("$ref")
                if ref is None:
                    raise SyntaxError(
                        "mechanic currently does not support schemas with type 'array' that do not have the 'items' "
                        "attribute as a '$ref' to another schema. Consider changing items object to reference a "
                        "schema. Object in error: %s" % (schema_name))

                self._add_regular_relationship(existing_model, model_name, ref, schema_name, uselist=True, backref=True)

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
                        # rel = self._init_rel()
                        # ref_name = ref.split("/")[-1]
                        # rel_name = prop_name
                        # rel["model"] = self._get_model_name_from_pattern(ref_name, namespace=existing_model["namespace"], version=self.version)
                        # rel["uselist"] = True
                        # existing_model["relationships"][rel_name] = rel
                        # self._add_foreign_key(existing_model, model_name, rel)
                        self._add_regular_relationship(existing_model, model_name, ref, prop_name, uselist=True, backref=schema_name.lower())

    def _add_regular_relationship(self,
                                  existing_model,
                                  model_name,
                                  ref,
                                  prop_name,
                                  uselist=False,
                                  backref=None,
                                  back_populates=None):
        rel = self._init_rel()
        ref_name = ref.split("/")[-1]
        rel_name = prop_name.lower()
        rel["model"] = self._get_model_name_from_pattern(ref_name, namespace=existing_model["namespace"],
                                                         version=self.version)
        if backref is True:
            rel["backref"] = rel_name
        elif backref:
            rel["backref"] = backref
            referenced_schema = self._follow_reference_link(ref)

            # print(backref, referenced_schema.get("properties"))
            # If the property is already defined in the model, remove it, because the backref will handle it.
            if backref in self.models[rel["model"]]["columns"].keys() and \
                    referenced_schema.get("properties", {}).get(backref, {}).get(URI_LINK_EXT, {}).get("$ref", "").lower().endswith(backref):
                self.models[rel["model"]]["columns"].pop(backref)

        rel["back_populates"] = back_populates
        rel["uselist"] = uselist
        existing_model["relationships"][rel_name] = rel
        self._add_foreign_key(existing_model, model_name, rel)

    def _add_column(self, column_name, existing_model, prop_obj, prop_name, schema_obj):
        col = self._init_model_col()
        col["type"] = self._map_openapi_type_to_sqlalchemy_type(prop_obj["type"])
        col["nullable"] = prop_name in schema_obj.get("required", [])
        col["length"] = prop_obj.get("maxLength", col["length"])
        col["comment"] = prop_obj.get("description")
        existing_model["columns"][column_name] = col

    def _add_oneof_relationship(self, existing_model, model_name, prop_item, schema_name, uselist=False):
        rel = self._init_rel()
        ref_name = prop_item.get("$ref").split("/")[-1]
        rel_name = schema_name.lower() + "_" + ref_name.lower()
        rel["model"] = ref_name
        rel["comment"] = prop_item.get("description")
        rel["uselist"] = uselist
        existing_model["relationships"][rel_name] = rel
        self._add_foreign_key(existing_model, model_name, rel)

    def _add_foreign_key(self, existing_model, existing_model_name, relationship):
        referenced_model = self.models[relationship["model"]]
        foreign_key_name = existing_model_name.lower() + "_id"
        foreign_key = self._init_model_col()
        foreign_key["type"] = self._map_openapi_type_to_sqlalchemy_type("string")
        foreign_key["length"] = PRIMARY_KEY_LENGTH
        # foreign_key["foreign_key"] = existing_model["db_schema"] + "." + \
        #                              existing_model["db_tablename"] + "." + \
        #                              existing_model["primary_key"]
        foreign_key["foreign_key"] = existing_model["db_tablename"] + "." + \
                                     existing_model["primary_key"]
        referenced_model["columns"][foreign_key_name] = foreign_key
        # relationship["foreign_keys"].append(foreign_key["foreign_key"])

    def _map_openapi_type_to_sqlalchemy_type(self, oapi_type):
        oapi_to_sql_alchemy_map = {
            "integer": "Integer",
            "string": "String",
            "number": "Float",
            "boolean": "Boolean"
        }
        return oapi_to_sql_alchemy_map[oapi_type]

    def _get_model_name_from_pattern(self, schema_name, namespace=None, version=None):
        model_name = utils.replace_template_var(self.options[reader.MODELS_NAME_PATTERN_KEY],
                                                resource=schema_name,
                                                namespace=namespace,
                                                version=version)
        return model_name

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
        bm = self.options[reader.OVERRIDE_BASE_MODEL_KEY]

        if bm:
            bm_for = bm.get("for")
            if bm_for:
                if isinstance(bm_for, str):
                    if bm_for.lower().strip() == "all" and model_path not in bm.get("except", []):
                        base_model = bm.get("with")
                elif isinstance(bm_for, list) and model_path in bm_for:
                    base_model = bm.get("with")
                else:
                    raise SyntaxError("'" + reader.OVERRIDE_BASE_MODEL_KEY + "' is not formatted properly.")
            else:
                raise SyntaxError("The 'for' attribute is required in the '" +
                                  reader.OVERRIDE_BASE_MODEL_KEY +
                                  "'option.")
        return base_model

    def _convert_model_name(self, name):
        pass

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
            "primary_key": "identifier"
        }

    def _init_model_col(self):
        return {
            "type": None,
            "nullable": True,
            "length": "2000",
            "foreign_key": None,
        }

    def _init_rel(self):
        return {
            "model": "",
            "backref": None,
            "back_populates": None,
            "uselist": False,
            "foreign_keys": [],
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
            return self.oapi_obj[section][object_type][resource_name]

    def build_mschemas(self): pass
    def build_controllers(self): pass
