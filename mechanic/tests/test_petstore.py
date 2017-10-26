import os
from unittest import TestCase
import shutil

from mechanic.src.generator import Generator
from mechanic.src.reader import read_mechanicfile


class TestPetstore(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        for item in os.listdir("gen"):
            if os.path.isdir(os.path.realpath("gen/" + item)):
                shutil.rmtree(os.path.realpath("gen/" + item))

    def test_directory_structure(self):
        options = read_mechanicfile("gen/mechanic.json")
        gen = Generator("gen", "abc.json", options=options)
        gen.create_dir_structure()

        self.assertTrue(os.path.exists("gen/" + options["MODELS_PATH"]))
        self.assertTrue(os.path.exists("gen/" + options["SCHEMAS_PATH"]))
        self.assertTrue(os.path.exists("gen/" + options["CONTROLLERS_PATH"]))

    def test_get_pets_petid_200_response_valid_Pet_schema(self): pass
    def test_get_pets_petid_not_found_response_valid_Error_schema(self): pass
    def test_get_pets_200_response_valid_array_of_Pets(self): pass
    def test_get_pets_error_response_valid_Error_schema(self): pass
    def test_post_pets_201_response_null(self): pass
    def test_post_pets_bad_request_valid_Error_schema(self): pass
    def test_post_pets_missing_required_attr_valid_Error_schema(self): pass
