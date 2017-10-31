import os
from unittest import TestCase

from mechanic.src.compiler import Compiler
from mechanic.src.utils import deserialize_file

class TestCompiler(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        try:
            os.remove("tmp-grocery.json")
            os.remove("tmp-petstore.json")
        except Exception:
            pass

    def test_compile(self):
        compiler = Compiler("specs/petstore.yaml", output="tmp-petstore.json")
        compiler.compile()

        obj = deserialize_file("tmp-petstore.json")
        columns = obj["models"]["Pet"]["columns"]
        self.assertTrue("id" in columns.keys())
        self.assertTrue("name" in columns.keys())
        self.assertTrue("tag" in columns.keys())

    def test_compile_grocery_allof(self):
        compiler = Compiler("specs/grocery.yaml", output="tmp-grocery.json")
        compiler.compile()

        obj = deserialize_file("tmp-grocery.json")
        gi_columns = obj["models"]["GroceryItem"]["columns"]
        self.assertTrue("name" in gi_columns.keys())
        self.assertTrue("price" in gi_columns.keys())
        self.assertTrue("quantity" in gi_columns.keys())

        steak_columns = obj["models"]["Steak"]["columns"]
        self.assertTrue("name" in steak_columns.keys())
        self.assertTrue("price" in steak_columns.keys())
        self.assertTrue("quantity" in steak_columns.keys())
        self.assertTrue("steakType" in steak_columns.keys())
        self.assertTrue("weight" in steak_columns.keys())

    def test_compile_grocery_oneof(self):
        compiler = Compiler("specs/grocery.yaml", output="tmp-grocery.json")
        compiler.compile()

        obj = deserialize_file("tmp-grocery.json")
        columns = obj["models"]["Shopper"]["columns"]
        rels = obj["models"]["Shopper"]["relationships"]
        self.assertTrue("wallet_string" in columns.keys())
        self.assertTrue("wallet_wallet" in rels.keys())

        columns = obj["models"]["Cart"]["columns"]
        rels = obj["models"]["Cart"]["relationships"]
        self.assertTrue("cartitems_array_string" in columns.keys())
        self.assertTrue("cartitems_groceryitem" in rels.keys())
        self.assertTrue("cartitems_wallet" in rels.keys())
