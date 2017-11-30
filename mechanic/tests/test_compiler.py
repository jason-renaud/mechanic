import os
from unittest import TestCase

from mechanic.src.compiler import Compiler
from mechanic.src.reader import read_mechanicfile
from mechanic.src.utils import deserialize_file


class TestCompiler(TestCase):
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

    def test_compile(self):
        options = read_mechanicfile(self.MECHANIC_BUILD_FILE_PETSTORE)
        compiler = Compiler(options, mechanic_file_path=self.MECHANIC_BUILD_FILE_PETSTORE, output=self.PETSTORE_TMP)
        compiler.compile()

        obj = deserialize_file(self.PETSTORE_TMP)
        columns = obj["models"]["Pet"]["columns"]
        self.assertTrue("id" in columns.keys())
        self.assertTrue("name" in columns.keys())
        self.assertTrue("tag" in columns.keys())

    def test_compile_grocery_allof(self):
        options = read_mechanicfile(self.MECHANIC_BUILD_FILE_GROCERY)
        compiler = Compiler(options, mechanic_file_path=self.MECHANIC_BUILD_FILE_GROCERY, output=self.GROCERY_TMP)
        compiler.compile()

        obj = deserialize_file(self.GROCERY_TMP)
        gi_columns = obj["models"]["GroceryItem"]["columns"]
        self.assertTrue("name" in gi_columns.keys())
        self.assertTrue("price" in gi_columns.keys())
        self.assertTrue("quantity" in gi_columns.keys())

        steak_columns = obj["models"]["Steak"]["columns"]
        self.assertTrue("type" in steak_columns.keys())
        self.assertTrue("animal" in steak_columns.keys())
        self.assertTrue("steakType" in steak_columns.keys())
        self.assertTrue("weight" in steak_columns.keys())

    def test_compile_grocery_oneof(self):
        options = read_mechanicfile(self.MECHANIC_BUILD_FILE_GROCERY)
        compiler = Compiler(options, mechanic_file_path=self.MECHANIC_BUILD_FILE_GROCERY, output=self.GROCERY_TMP)
        compiler.compile()

        obj = deserialize_file(self.GROCERY_TMP)
        rels = obj["models"]["Shopper"]["relationships"]
        self.assertTrue("wallet" in rels.keys())

        rels = obj["models"]["Cart"]["relationships"]
        self.assertTrue("cartItems" in rels.keys())

    def test_compile_grocery_verify_foreign_keys(self):
        options = read_mechanicfile(self.MECHANIC_BUILD_FILE_GROCERY)
        compiler = Compiler(options, mechanic_file_path=self.MECHANIC_BUILD_FILE_GROCERY, output=self.GROCERY_TMP)
        compiler.compile()

        # one-to-many
        obj = deserialize_file(self.GROCERY_TMP)
        columns = obj["models"]["GroceryItem"]["columns"]
        rels = obj["models"]["Groceries"]["relationships"]
        self.assertTrue("groceries_id" in columns.keys())
        self.assertTrue("groceries" in rels.keys())

        # one-to-many w/ oneOf
        columns = obj["models"]["GroceryItem"]["columns"]
        rels = obj["models"]["Cart"]["relationships"]
        self.assertTrue("cart_id" in columns.keys())
        self.assertTrue("cartItems" in rels.keys())

        # one-to-one
        columns = obj["models"]["Wallet"]["columns"]
        rels = obj["models"]["Shopper"]["relationships"]
        self.assertTrue("shopper_id" in columns.keys())
        self.assertTrue("wallet" in rels.keys())

    def test_compile_verify_excluded_models_and_schemas(self):
        options = read_mechanicfile(self.MECHANIC_BUILD_FILE_GROCERY)
        compiler = Compiler(options, mechanic_file_path=self.MECHANIC_BUILD_FILE_GROCERY, output=self.GROCERY_TMP)
        compiler.compile()

        obj = deserialize_file(self.GROCERY_TMP)
        # self.assertFalse(obj["models"].get("Error"))
        self.assertFalse(obj["schemas"].get("Error"))
        self.assertFalse(obj["resources"].get("Error").get("model"))

    def test_compile_verify_base_controllers(self):
        options = read_mechanicfile(self.MECHANIC_BUILD_FILE_GROCERY)
        compiler = Compiler(options, mechanic_file_path=self.MECHANIC_BUILD_FILE_GROCERY, output=self.GROCERY_TMP)
        compiler.compile()

        obj = deserialize_file(self.GROCERY_TMP)

        self.assertEqual(obj["controllers"]["GroceriesItemController"]["base_controller_name"], "MyController")
        self.assertEqual(obj["controllers"]["GroceriesItemController"]["base_controller_path"], "abc.mypackage.hello")

        self.assertEqual(obj["controllers"]["ShopperItemController"]["base_controller_name"], "MechanicBaseItemController")
        self.assertEqual(obj["controllers"]["ShopperItemController"]["base_controller_path"], "mechanic.base.controllers")

    def test_compile_verify_nested(self):
        options = read_mechanicfile(self.MECHANIC_BUILD_FILE_GROCERY)
        compiler = Compiler(options, mechanic_file_path=self.MECHANIC_BUILD_FILE_GROCERY, output=self.GROCERY_TMP)
        compiler.compile()

        obj = deserialize_file(self.GROCERY_TMP)

        self.assertEqual(obj["schemas"]["EmployeeSchema"]["nested"]["favBanana"]["schema"], "BananaSchema")
        self.assertEqual(obj["schemas"]["EmployeeSchema"]["nested"]["favBanana"]["many"], False)
        self.assertEqual(obj["schemas"]["EmployeeSchema"]["nested"]["favApples"]["schema"], "AppleSchema")
        self.assertEqual(obj["schemas"]["EmployeeSchema"]["nested"]["favApples"]["many"], True)
