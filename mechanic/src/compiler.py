import json
import yaml
import yamlordereddictloader
from yamlordereddictloader import OrderedDict

from .utils import deserialize_file

data_map = {
    "integer": "Integer",
    "string": "String",
    "number": "Float",
    "boolean": "Boolean"
}


class Compiler(object):
    ACTIONABLE_OBJECTS = {
        "responses": "handle_responses",
        "requestBody": "handle_requestBody",
        "parameters": "handle_parameters",
        "$ref": "handle_ref"
    }

    def __init__(self, oapi_file, output="tmp.json"):
        self.oapi_file = oapi_file
        self.oapi_obj = deserialize_file(self.oapi_file)
        self.models = dict()
        self.output = output

    def compile(self):
        self.build_models()
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


    def build_models(self):
        for schema_name, schema_obj in self.oapi_obj["components"]["schemas"].items():
            model = self._init_model()

            # Handle properties
            for prop_name, prop_obj in schema_obj.get("properties", {}).items():
                model["columns"][prop_name] = self._init_model_col()
                model["columns"][prop_name]["type"] = prop_obj["type"]
                model["columns"][prop_name]["nullable"] = prop_name in schema_obj.get("required", [])
                model["columns"][prop_name]["length"] = prop_obj.get("maxLength", model["columns"][prop_name]["length"])
                model["columns"][prop_name]["comment"] = prop_obj.get("description")

            # Handle allOf
            # Handle oneOf
            # Handle anyOf
            self.models[schema_name] = model

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

    def build_mschemas(self): pass
    def build_controllers(self): pass
