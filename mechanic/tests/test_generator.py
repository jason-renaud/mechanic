import os
from unittest import TestCase
import shutil

from mechanic.src.compiler import Compiler
from mechanic.src.generator import Generator
from mechanic.src.reader import read_mechanicfile, \
    OPENAPI3_FILE_KEY, APP_NAME_KEY, OVERRIDE_BASE_CONTROLLER_KEY, \
    MODELS_PATH_KEY, SCHEMAS_PATH_KEY, CONTROLLERS_PATH_KEY


class TestPetstore(TestCase):
    CURRENT_DIR = os.path.dirname(__file__)
    PETSTORE_SPEC = os.path.dirname(__file__) + "/specs/petstore.yaml"
    PETSTORE_TMP = os.path.dirname(__file__) + "/tmp-petstore.json"
    GROCERY_SPEC = os.path.dirname(__file__) + "/specs/grocery.yaml"
    GROCERY_TMP = os.path.dirname(__file__) + "/tmp-grocery.json"
    MECHANIC_BUILD_FILE_GROCERY = os.path.dirname(__file__) + "/gen/mechanic-grocery.json"
    MECHANIC_BUILD_FILE_PETSTORE = os.path.dirname(__file__) + "/gen/mechanic-petstore.json"

    def setUp(self):
        pass

    def tearDown(self):
        try:
            # os.remove(self.GROCERY_TMP)
            os.remove(self.PETSTORE_TMP)
        except Exception:
            pass

        # for item in os.listdir(os.path.dirname(__file__) + "/gen"):
        #     if os.path.isdir(os.path.realpath("gen/" + item)):
        #         shutil.rmtree(os.path.realpath("gen/" + item))

    def test_directory_structure(self):
        options = read_mechanicfile(self.MECHANIC_BUILD_FILE_GROCERY)

        compiler = Compiler(options, mechanic_file_path=self.MECHANIC_BUILD_FILE_GROCERY, output=self.GROCERY_TMP)
        compiler.compile()

        gen = Generator(self.CURRENT_DIR + "/gen", compiler.mech_obj, options=options)
        gen.create_dir_structure()

        # self.assertTrue(os.path.exists(self.CURRENT_DIR + "/gen/" + options[MODELS_PATH_KEY]))
        # self.assertTrue(os.path.exists(self.CURRENT_DIR + "/gen/" + options[SCHEMAS_PATH_KEY]))
        # self.assertTrue(os.path.exists(self.CURRENT_DIR + "/gen/" + options[CONTROLLERS_PATH_KEY]))

    def test_get_pets_petid_200_response_valid_Pet_schema(self): pass
    def test_get_pets_petid_not_found_response_valid_Error_schema(self): pass
    def test_get_pets_200_response_valid_array_of_Pets(self): pass
    def test_get_pets_error_response_valid_Error_schema(self): pass
    def test_post_pets_201_response_null(self): pass
    def test_post_pets_bad_request_valid_Error_schema(self): pass
    def test_post_pets_missing_required_attr_valid_Error_schema(self): pass
