import os
import ast
import re
import json
import yaml
import yamlordereddictloader
import pprint
import pkg_resources
from collections import OrderedDict

pp = pprint.PrettyPrinter(indent=4)
EXTERNAL_SCHEMA_REGEX = "['\"]\$ref['\"]:\s['\"](?:\w|/)*\.(?:json|yaml|yml)#[/\w]*['\"]"

class Merger:
    """
    Provides an API to merge an OpenAPI spec that is split into multiple files. For example, if you have a reference
    to an external document like this:

    $ref: cars/wheel.yaml#/components/schemas/wheel

    mechanic will merge the reference to that schema into the original file, and then save a copy.

    **Note, the below is not currently supported
    You can also reference files that don't live on the same file system. If the files are hosted at www.abc.my.api.com,
    you could reference them like this:

    $ref: http://www.abc.my.api.com/cars/wheel.yaml#/components/schemas/wheel
    """
    root_dir = ""

    def __init__(self, oapi_file, output_file):
        self.oapi_file = oapi_file
        self.oapi_obj = self._deserialize_file()
        self.output_file = output_file

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
        Gets a referenced object.

        :param ref: reference link, example: #/components/schemas/Pet or pet.json#/components/schemas/Pet
        :param current_dir: current directory of looking for file
        :return: dictionary representation of the referenced object
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

            with open(self.root_dir + "/" + filename) as f:
                if filename.endswith(".json"):
                    data = json.load(f)
                elif filename.endswith(".yaml") or filename.endswith(".yml"):
                    data = yaml.load(f)

            return data[object_name]

    def merge(self):
        """
        Currently only supports referencing items that will end up in the components/schemas location in the spec file.
        """
        self._merge_schemas()

    def _merge_schemas(self):
        oapi_str = str(self.oapi_obj)
        matches = re.findall(EXTERNAL_SCHEMA_REGEX, oapi_str)

        while len(matches) > 0:
            for match in matches:
                reference = match.split(":")[1].replace("'", "").strip(" ")
                resource_name = reference.split("/")[-1]
                obj = self._follow_reference_link(reference, remote_only=True)

                if obj:
                    oapi_str = oapi_str.replace(match, '"$ref": "#/components/schemas/' + resource_name + '"')
                    self.oapi_obj = ast.literal_eval(oapi_str)

                    if not self.oapi_obj["components"]["schemas"].get(resource_name):
                        self.oapi_obj["components"]["schemas"][resource_name] = obj
                    oapi_str = str(self.oapi_obj)
            matches = re.findall(EXTERNAL_SCHEMA_REGEX, oapi_str)

        with open(self.output_file, "w") as f:
            if self.output_file.endswith(".json"):
                json_data = json.dumps(self.oapi_obj, indent=3)
                f.write(json_data)
            elif self.output_file.endswith(".yaml") or self.output_file.endswith(".yml"):
                yaml_data = yaml.dump(OrderedDict(self.oapi_obj),
                                      Dumper=yamlordereddictloader.Dumper,
                                      default_flow_style=False)
                f.write(yaml_data)
