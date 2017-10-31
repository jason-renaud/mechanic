import json
import yaml
import yamlordereddictloader
from yamlordereddictloader import OrderedDict

import mechanic.src.utils as utils

data_map = {
    "integer": "Integer",
    "string": "String",
    "number": "Float",
    "boolean": "Boolean"
}

NATIVE_TYPES = ["integer", "number", "string", "boolean"]


class Compiler(object):
    ACTIONABLE_OBJECTS = {
        "responses": "handle_responses",
        "requestBody": "handle_requestBody",
        "parameters": "handle_parameters",
        "$ref": "handle_ref"
    }

    def __init__(self, oapi_file, output="tmp.json"):
        self.oapi_file = oapi_file
        self.oapi_obj = utils.deserialize_file(self.oapi_file)
        self.models = dict()
        self.output = output

    def compile(self):
        self.build_models_pass1()
        self.build_models_pass2()
        self.build_models_pass3()

        self.build_mschemas()
        self.build_controllers()

        self.write_to_file()

    def write_to_file(self):
        obj = {
            "models": self.models,
        }

        with open(self.output, "w") as f:
            if self.output.endswith(".json"):
                json_data = json.dumps(obj, indent=3)
                f.write(json_data)
            elif self.output.endswith(".yaml") or self.output.endswith(".yml"):
                yaml_data = yaml.dump(OrderedDict(obj),
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
            model = self._init_model()

            # Handle properties
            for prop_name, prop_obj in schema_obj.get("properties", {}).items():
                if prop_obj.get("type") in NATIVE_TYPES:
                    model["columns"][prop_name] = self._init_model_col()
                    model["columns"][prop_name]["type"] = prop_obj["type"]
                    model["columns"][prop_name]["nullable"] = prop_name in schema_obj.get("required", [])
                    model["columns"][prop_name]["length"] = prop_obj.get("maxLength", model["columns"][prop_name]["length"])
                    model["columns"][prop_name]["comment"] = prop_obj.get("description")
                else:
                    print("PASS 1 not dealing with relationships yet.")

            # Handle allOf
            # Handle oneOf
            # Handle anyOf
            self.models[schema_name] = model

    def build_models_pass2(self):
        """
        Pass 2 handles allOf composition
        """
        for schema_name, schema_obj in self.oapi_obj["components"]["schemas"].items():
            existing_model = self.models.get(schema_name)

            # Handle allOf
            for item in schema_obj.get("allOf", {}):
                if item.get("type") in NATIVE_TYPES:
                    print("ERROR: objects in 'allOf' arrays must either be of type 'object' or a '$ref'.")
                    exit()
                elif item.get("type") == "object":
                    for prop_name, prop_obj in item.get("properties", {}).items():
                        col = self._init_model_col()
                        col["type"] = prop_obj["type"]
                        col["nullable"] = prop_name in schema_obj.get("required", [])
                        col["length"] = prop_obj.get("maxLength", col["length"])
                        col["comment"] = prop_obj.get("description")
                        existing_model["columns"][prop_name] = col
                elif item.get("$ref"):
                    obj = self._follow_reference_link(item.get("$ref"))
                    for prop_name, prop_obj in obj.get("properties", {}).items():
                        col = self._init_model_col()
                        col["type"] = prop_obj["type"]
                        col["nullable"] = prop_name in schema_obj.get("required", [])
                        col["length"] = prop_obj.get("maxLength", col["length"])
                        col["comment"] = prop_obj.get("description")
                        existing_model["columns"][prop_name] = col

    def build_models_pass3(self):
        """
        Pass 3 handles oneOf and relationships.
        """
        for schema_name, schema_obj in self.oapi_obj["components"]["schemas"].items():
            existing_model = self.models.get(schema_name)

            # Handle any oneOf properties
            for prop_name, prop_obj in schema_obj.get("properties", {}).items():
                for item in prop_obj.get("oneOf", []):
                    print(item)
                    if item.get("type") in NATIVE_TYPES:
                        column_name = prop_name.lower() + "_" + item.get("type").lower()
                        col = self._init_model_col()
                        col["type"] = item["type"]
                        col["nullable"] = prop_name in schema_obj.get("required", [])
                        col["length"] = item.get("maxLength", col["length"])
                        col["comment"] = item.get("description")
                        existing_model["columns"][column_name] = col
                    elif item.get("$ref"):
                        rel = self._init_rel()
                        ref_name = item.get("$ref").split("/")[-1]
                        rel_name = prop_name.lower() + "_" + ref_name.lower()
                        rel["model"] = ref_name
                        rel["comment"] = item.get("description")
                        existing_model["relationships"][rel_name] = rel

                if prop_obj.get("type") == "array":
                    # Handle array of oneOf
                    for arr_oneof in prop_obj.get("items", {}).get("oneOf", []):
                        if arr_oneof.get("type") in NATIVE_TYPES:
                            column_name = prop_name.lower() + "_array_" + arr_oneof.get("type").lower()
                            col = self._init_model_col()
                            col["type"] = arr_oneof["type"]
                            col["nullable"] = prop_name in schema_obj.get("required", [])
                            col["length"] = arr_oneof.get("maxLength", col["length"])
                            col["comment"] = arr_oneof.get("description")
                            existing_model["columns"][column_name] = col
                        elif arr_oneof.get("$ref"):
                            rel = self._init_rel()
                            ref_name = arr_oneof.get("$ref").split("/")[-1]
                            rel_name = prop_name.lower() + "_" + ref_name.lower()
                            rel["model"] = ref_name
                            rel["uselist"] = True
                            rel["comment"] = arr_oneof.get("description")
                            existing_model["relationships"][rel_name] = rel

    def _convert_model_name(self, name):
        pass

    def _init_model(self):
        return {
            "columns": {},
            "relationships": {},
            "tablename": "default",
            "db_schema": "default",
            "namespace": "default",
            "comment": None
        }

    def _init_model_col(self):
        return {
            "type": None,
            "nullable": False,
            "length": "2000",
            "foreign_key": None
        }

    def _init_rel(self):
        return {
            "model": "",
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
