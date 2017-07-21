import os
import unittest
import json
import shutil
import pprint

import mechanic

pp = pprint.PrettyPrinter(indent=4)

data = {
    "components": {
        "schemas": {
            "Pet": {
                "title": "Pet",
                "type": "object",
                "properties": {
                    "age": {
                        "type": "integer"
                    },
                    "weight": {
                        "type": "string"
                    }
                }
            }
        }
    }
}

GET_OBJECT = {
    "description": "",
    "operationId": "findPets",
    "parameters": [
        {
            "name": "tags",
            "in": "query",
            "description": "tags to filter by",
            "required": False,
            "style": "form",
            "schema": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            }
        },
        {
            "name": "limit",
            "in": "query",
            "description": "maximum number of results to return",
            "required": False,
            "schema": {
                "type": "integer",
                "format": "int32"
            }
        }
    ],
    "responses": {
        "200": {
            "description": "pet response",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "array",
                        "items": {
                            "$ref": "#/components/schemas/Pet"
                        }
                    }
                }
            }
        },
        "default": {
            "description": "unexpected error",
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/Error"
                    }
                }
            }
        }
    }
}

PATH_OBJ = {
    "x-mechanic-namespace": "dogs",
    "get": {
        "description": "",
        "operationId": "findPets",
        "parameters": [
            {
                "name": "tags",
                "in": "query",
                "description": "tags to filter by",
                "required": False,
                "style": "form",
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            {
                "name": "limit",
                "in": "query",
                "description": "maximum number of results to return",
                "required": False,
                "schema": {
                    "type": "integer",
                    "format": "int32"
                }
            }
        ],
        "responses": {
            "200": {
                "description": "pet response",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "array",
                            "items": {
                                "$ref": "#/components/schemas/Pet"
                            }
                        }
                    }
                }
            },
            "default": {
                "description": "unexpected error",
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": "#/components/schemas/Error"
                        }
                    }
                }
            }
        }
    }
}

COMMAND_METHOD = {
    "parameters": [
        {
            "name": "id",
            "in": "path",
            "required": True,
            "schema": {
                "type": "string"
            }
        }
    ],
    "responses": {
        "202": {
            "description": "Accepted",
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "samples/carstask.json#/components/schemas/carstask"
                    }
                }
            }
        }
    },
    "requestBody": {
        "description": "",
        "content": {
            "application/json": {
                "schema": {
                    "$ref": "samples/requestBodies/wheelrotate.json#/components/requestBodies/wheelrotate"
                }
            }
        }
    }
}

POST_METHOD = {
    "responses": {
        "201": {
            "description": "Created",
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "samples/wheel.json#/components/schemas/wheel"
                    }
                }
            }
        }
    },
    "requestBody": {
        "description": "",
        "content": {
            "application/json": {
                "schema": {
                    "$ref": "samples/wheel.json#/components/schemas/wheel"
                }
            }
        }
    }
}


class MechanicTestConvertMethods(unittest.TestCase):
    def test_convert_input_file_does_exist(self):
        self.assertRaises(json.JSONDecodeError, mechanic.convert, "my-fake-file.json", "mechanic.json")

    def test_convert_invalid_json(self):
        self.assertRaises(json.JSONDecodeError, mechanic.convert, '{'
                                                                  '    "this is invalid json": "because", '
                                                                  '    "there is a trailing comma": "like this",'
                                                                  '}',
                          "mechanic.json")

    def test_convert_invalid_version(self):
        self.assertRaises(SyntaxError, mechanic.convert, '{"openapi": "2.5"}', "mechanic.json")

    def test_convert_paths_not_exist(self):
        self.assertRaises(SyntaxError, mechanic.convert, '{"openapi": "3.0"}', "mechanic.json")

    def test_build_controller_from_path_wrong_uri_format(self):
        self.assertRaises(SyntaxError, mechanic.convert, '{"openapi": "3.0", "paths": {"abc": {}}}', "mechanic.json")

    def test_parse_resource_name_segments_from_path(self):
        name = mechanic.parse_resource_name_segments_from_path("/cars/wheels/{id}/rotate")
        self.assertEqual("WheelRotateCommandController", name["controller"])
        self.assertEqual("WheelRotate", name["command_name"])
        self.assertEqual("WheelRotateService", name["service"])
        self.assertEqual("WheelModel", name["model"])
        self.assertEqual("WheelSchema", name["schema"])
        self.assertEqual("Wheel", name["resource"])

        name = mechanic.parse_resource_name_segments_from_path("/cars/wheel/{id}/rotate")
        self.assertEqual("WheelRotateCommandController", name["controller"])
        self.assertEqual("WheelRotate", name["command_name"])
        self.assertEqual("WheelRotateService", name["service"])
        self.assertEqual("WheelModel", name["model"])
        self.assertEqual("WheelSchema", name["schema"])
        self.assertEqual("Wheel", name["resource"])

        name = mechanic.parse_resource_name_segments_from_path("/cars/wheels/all/rotate")
        self.assertEqual("WheelRotateAllCommandController", name["controller"])
        self.assertEqual("WheelRotate", name["command_name"])
        self.assertEqual("WheelRotateService", name["service"])
        self.assertEqual("WheelModel", name["model"])
        self.assertEqual("WheelSchema", name["schema"])
        self.assertEqual("Wheel", name["resource"])

        name = mechanic.parse_resource_name_segments_from_path("/cars/wheel/all/rotate")
        self.assertEqual("WheelRotateAllCommandController", name["controller"])
        self.assertEqual("WheelRotate", name["command_name"])
        self.assertEqual("WheelRotateService", name["service"])
        self.assertEqual("WheelModel", name["model"])
        self.assertEqual("WheelSchema", name["schema"])
        self.assertEqual("Wheel", name["resource"])

        name = mechanic.parse_resource_name_segments_from_path("/cars/wheels")
        self.assertEqual("WheelCollectionController", name["controller"])
        self.assertEqual("", name["command_name"])
        self.assertEqual("WheelService", name["service"])
        self.assertEqual("WheelModel", name["model"])
        self.assertEqual("WheelSchema", name["schema"])
        self.assertEqual("Wheel", name["resource"])

        name = mechanic.parse_resource_name_segments_from_path("/cars/wheel")
        self.assertEqual("WheelCollectionController", name["controller"])
        self.assertEqual("", name["command_name"])
        self.assertEqual("WheelService", name["service"])
        self.assertEqual("WheelModel", name["model"])
        self.assertEqual("WheelSchema", name["schema"])
        self.assertEqual("Wheel", name["resource"])

    def test_follow_reference_link_in_current_file(self):
        self.assertEqual(len(mechanic.follow_reference_link(data, "#/components/schemas/Pet")[0]["properties"]), 2)

    def test_follow_reference_link_in_external_file(self):
        obj = mechanic.follow_reference_link("", "samples/wheel.json#/components/schemas/wheel")[0]
        self.assertEqual(len(obj["properties"]), 3)
        self.assertEqual(obj["properties"]["size"]["type"], "integer")
        self.assertEqual(obj["properties"]["color"]["type"], "string")

        obj = mechanic.follow_reference_link("", "tire.json#/components/schemas/tire", current_dir="samples")[0]
        self.assertEqual(len(obj["properties"]), 1)
        self.assertEqual(obj["properties"]["brand"]["type"], "string")

        obj = mechanic.follow_reference_link("", "cars/requestBodies/enginetype.json#/components/schemas/enginetype",
                                             current_dir="cars/schemas")[0]
        self.assertEqual(len(obj["properties"]), 1)
        self.assertEqual(obj["properties"]["name"]["type"], "string")

    def test_build_controller_and_models_from_path(self):
        controller, models, schemas = mechanic.build_controller_models_schemas_from_path(data, "/pets", PATH_OBJ, "")
        self.assertEqual(controller.get("class_name"), "PetCollectionController")
        self.assertEqual(controller.get("controller_type"), "COLLECTION")
        self.assertEqual(controller.get("service_class"), "PetService")
        self.assertEqual(controller.get("methods")[0]["name"], "get")
        self.assertEqual(controller.get("methods")[0]["async"], False)
        self.assertEqual(len(controller.get("methods")[0]["query_params"]), 2)
        self.assertEqual(controller.get("methods")[0]["supported"], True)

        list_of_model_class_names = [model["class_name"] for model in models]
        list_of_schema_class_names = [schema["class_name"] for schema in schemas]

        # verify all models and schemas are unique
        for item in models:
            self.assertEqual(list_of_model_class_names.count(item["class_name"]), 1)

        for item in schemas:
            self.assertEqual(list_of_schema_class_names.count(item["class_name"]), 1)

    def test_parse_response_from_method_responses(self):
        response = mechanic.parse_response_from_method_responses(
            {"components": {"schemas": {"Pet": {"title": "Pet"}}}},
            {
                "200": {
                    "description": "pet response",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {
                                    "$ref": "#/components/schemas/Pet"
                                }
                            }
                        }
                    }
                },
                "default": {
                    "description": "unexpected error",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Error"
                            }
                        }
                    }
                }
            }, "")
        self.assertEqual(response["schema"], "PetSchema")
        self.assertEqual(response["model"], "PetModel")
        self.assertEqual(response["success_code"], 200)

    def test_parse_response_from_method_responses_no_2xx_defined(self):
        self.assertRaises(SyntaxError, mechanic.parse_response_from_method_responses, {}, {"responses": {}}, "")

    def test_parse_response_from_method_responses_no_schema_title(self):
        self.assertRaises(SyntaxError, mechanic.parse_response_from_method_responses,
                          {"components": {"schemas": {"Pet": {}}}},
                          {
                              "200": {
                                  "description": "pet response",
                                  "content": {
                                      "application/json": {
                                          "schema": {
                                              "type": "array",
                                              "items": {
                                                  "$ref": "#/components/schemas/Pet"
                                              }
                                          }
                                      }
                                  }
                              },
                              "default": {
                                  "description": "unexpected error",
                                  "content": {
                                      "application/json": {
                                          "schema": {
                                              "$ref": "#/components/schemas/Error"
                                          }
                                      }
                                  }
                              }
                          }, "")

    def test_parse_response_from_method_responses_no_model(self):
        response = mechanic.parse_response_from_method_responses(
            {"components": {"schemas": {"Pet": {"title": "Pet"}}}},
            {
                "200": {
                    "description": "pet response",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {
                                    "$ref": "#/components/schemas/Pet"
                                }
                            }
                        }
                    }
                },
                "default": {
                    "description": "unexpected error",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/Error"
                            }
                        }
                    }
                }
            }, "", no_model=True)
        self.assertEqual(response["schema"], "PetSchema")
        self.assertEqual(response["model"], None)
        self.assertEqual(response["success_code"], 200)

    def test_parse_request_from_requestBody(self):
        request, properties = mechanic.parse_request_from_requestBody(
            {
                "components": {
                    "requestBodies": {
                        "wheelrotate": {
                            "title": "WheelRotateParameters",
                            "properties": {
                                "direction": {
                                    "type": "string"
                                }
                            }
                        }
                    }
                }
            },
            {
                "description": "",
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": "#/components/requestBodies/wheelrotate"
                        }
                    }
                }
            }, "", command=True)
        self.assertEqual(request["schema"], "WheelRotateParameters")

        request, properties = mechanic.parse_request_from_requestBody(
            {"components": {"requestBodies": {"wheel": {"title": "Wheel", "properties": {
                "direction": {
                    "type": "string"
                }
            }}}}},
            {
                "description": "",
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": "#/components/requestBodies/wheel"
                        }
                    }
                }
            }, "", command=False)
        self.assertEqual(request["schema"], "WheelSchema")

    def test_parse_method_from_path_methods(self):
        method = mechanic.parse_method_from_path_method(data, "get", GET_OBJECT, "")
        self.assertEqual(method["name"], "get")
        self.assertEqual(method["async"], False)
        self.assertEqual(len(method["query_params"]), 2)
        self.assertEqual(method["response"]["schema"], "PetSchema")
        self.assertEqual(method["response"]["model"], "PetModel")

    def test_parse_response_models_from_path_method(self):
        models = mechanic.parse_response_models_from_path_method(data, GET_OBJECT, "dogs", "")
        self.assertEqual(len(models), 1)
        self.assertEqual(models[0]["class_name"], "PetModel")
        self.assertEqual(models[0]["resource_name"], "Pet")
        self.assertEqual(models[0]["db_table_name"], "pets")
        self.assertEqual(models[0]["db_schema_name"], "dogs")
        self.assertEqual(len(models[0]["properties"]), 2)

    def test_build_models_from_reference_link(self):
        models = mechanic.build_models_from_reference_link(data, "samples/wheel.json#/components/schemas/wheel", "cars",
                                                           [], "", [])
        self.assertEqual(len(models), 2)

    def test_parse_schemas_from_path_method(self):
        schemas = mechanic.parse_schemas_from_path_method(data, COMMAND_METHOD, "cars", "", command=True)
        self.assertEqual(len(schemas), 2)

        schemas = mechanic.parse_schemas_from_path_method(data, POST_METHOD, "cars", "", command=False)
        self.assertEqual(len(schemas), 2)

    def test_configure_resource_relationships(self):
        models = [
            {
                "class_name": "AggregateModel",
                "resource_name": "Aggregate",
                "db_table_name": "aggregates",
                "db_schema_name": "storage",
                "unique_name": "storage:AggregateModel",
                "namespace": "storage",
                "properties": [
                    {
                        "name": "name",
                        "type": "String",
                        "maxLength": 200,
                        "required": True
                    },
                    {
                        "name": "storageNode",
                        "type": "String",
                        "required": True
                    },
                    {
                        "name": "volumes",
                        "type": "array",
                        "model_ref": "storage:VolumeModel",
                        "required": False
                    }
                ]
            },
            {
                "class_name": "VolumeModel",
                "resource_name": "Volume",
                "db_table_name": "volumes",
                "db_schema_name": "storage",
                "namespace": "storage",
                "unique_name": "storage:VolumeModel",
                "properties": [
                    {
                        "name": "name",
                        "type": "String",
                        "maxLength": 200,
                        "required": True
                    },
                    {
                        "name": "snapshotReservation",
                        "type": "String",
                        "required": True
                    }
                ]
            }
        ]
        schemas = [
            {
                "class_name": "CreateVolumeParameters",
                "model": None,
                "unique_name": "storage:CreateVolumeParameters",
                "namespace": "storage",
                "additional_fields": []
            },
            {
                "class_name": "AggregateSchema",
                "model": "AggregateModel",
                "unique_name": "storage:AggregateSchema",
                "namespace": "storage",
                "additional_fields": []
            },
            {
                "class_name": "VolumeSchema",
                "model": "VolumeModel",
                "unique_name": "storage:VolumeSchema",
                "namespace": "storage",
                "additional_fields": []
            }
        ]
        models, schemas = mechanic.configure_resource_relationships(models, schemas)
        # foreign key should be added to VolumeModel
        self.assertEqual(len(models[1]["properties"]), 3)
        self.assertEqual(len(models[0]["properties"]), 3)
        self.assertEqual(len(schemas[1]["additional_fields"]), 1)

    def test_attach_resources_to_files(self):
        controllers = [
            {
                "class_name": "WheelController",
                "base_controller": "BaseController",
                "controller_type": "item",
                "service_class": "WheelService",
                "namespace": "cars",
                "referenced_models": ["WheelModel"],
                "referenced_schemas": ["WheelSchema"],
                "uri": "/cars/wheels/{id}"
            }
        ]
        models = [
            {
                "class_name": "WheelModel",
                "resource_name": "Wheel",
                "db_table_name": "wheels",
                "db_schema_name": "cars",
                "namespace": "cars"
            }
        ]
        schemas= [
            {
                "class_name": "WheelSchema",
                "model": "WheelModel",
                "namespace": "cars",
                "additionalFields": []
            }
        ]

        files = mechanic.attach_resources_to_files(controllers, models, schemas)

        # should create 1 controller file, 1 model file, 1 schema file, 1 api file
        self.assertEqual(len(files.keys()), 4)
        self.assertEqual(
            files["controllers/cars/controllers.py"]["base_controllers_to_import"]["base.controllers"]["modules"][0],
            "BaseController")
        self.assertEqual(
            files["controllers/cars/controllers.py"]["models_to_import"]["models.cars.models"]["modules"][0],
            "WheelModel")
        self.assertEqual(
            files["controllers/cars/controllers.py"]["schemas_to_import"]["schemas.cars.schemas"]["modules"][0],
            "WheelSchema")
        self.assertEqual(
            files["controllers/cars/controllers.py"]["services_to_import"]["services.cars.services"]["modules"][0],
            "WheelService")

        self.assertEqual(len(files["models/cars/models.py"]["models"]), 1)
        self.assertEqual(len(files["schemas/cars/schemas.py"]["schemas"]), 1)
        self.assertEqual(len(files["app/api.py"]["controllers.cars.controllers"]), 1)

    def test_convert(self):
        mechanic.convert("cars/cars.json", "output.json")

        with open("cars/expected-cars-mechanic.json", "r") as f:
            expected = json.load(f)

        with open("output.json", "r") as f:
            actual = json.load(f)

        # os.remove("output.json")
        self.assertTrue(ordered(expected) == ordered(actual))


# taken from
# https://stackoverflow.com/questions/25851183/how-to-compare-two-json-objects-with-the-same-elements-in-a-different-order-equa
def ordered(obj):
    if isinstance(obj, dict):
        return sorted((k, ordered(v)) for k, v in obj.items())
    if isinstance(obj, list):
        return sorted(ordered(x) for x in obj)
    else:
        return obj


class MechanicTestGenerateMethods(unittest.TestCase):
    @unittest.skip
    def test_generate(self):
        mechanic.convert("cars/cars.json", "output.json")

        shutil.rmtree("proj", ignore_errors=True)
        mechanic.generate("output.json", "proj")

        # assert top level directories created
        self.assertTrue("controllers" in os.listdir("proj"))
        self.assertTrue("models" in os.listdir("proj"))
        self.assertTrue("schemas" in os.listdir("proj"))
        #self.assertTrue("services" in os.listdir("proj"))
        self.assertTrue("base" in os.listdir("proj"))

        # assert files got created
        self.assertTrue("controllers.py" in os.listdir("proj/controllers/cars"))
        self.assertTrue("models.py" in os.listdir("proj/models/cars"))
        self.assertTrue("schemas.py" in os.listdir("proj/schemas/cars"))
        #shutil.rmtree("proj")

    @unittest.skip
    def test_generate_file_from_spec_item(self):
        #mechanic.generate_file_from_spec_item()
        pass