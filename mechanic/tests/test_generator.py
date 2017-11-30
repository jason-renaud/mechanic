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
            os.remove(self.GROCERY_TMP)
            os.remove(self.PETSTORE_TMP)
        except Exception:
            pass

        for item in os.listdir(os.path.dirname(__file__) + "/gen"):
            if os.path.isdir(os.path.realpath("gen/" + item)):
                shutil.rmtree(os.path.realpath("gen/" + item))
            elif item == "run.py" or item == "requirements.txt":
                os.remove(os.path.realpath("gen/" + item))

    def test_directory_structure(self):
        options = read_mechanicfile(self.MECHANIC_BUILD_FILE_GROCERY)

        compiler = Compiler(options, mechanic_file_path=self.MECHANIC_BUILD_FILE_GROCERY, output=self.GROCERY_TMP)
        compiler.compile()

        gen = Generator(self.CURRENT_DIR + "/gen", compiler.mech_obj, options=options)
        gen.generate()

        self.assertTrue(os.path.exists(self.CURRENT_DIR + "/gen/models/default.py"))
        self.assertTrue(os.path.exists(self.CURRENT_DIR + "/gen/schemas/v100/default.py"))
