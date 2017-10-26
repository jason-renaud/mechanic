import os
from unittest import TestCase

from mechanic.src.compiler import Compiler
from mechanic.src.utils import deserialize_file

class TestCompiler(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        os.remove("tmp.json")

    def test_compile(self):
        compiler = Compiler("specs/petstore.yaml", output="tmp.json")
        compiler.compile()

        obj = deserialize_file("tmp.json")
        self.assertTrue("id" in obj["models"]["Pet"]["columns"].keys())
        self.assertTrue("name" in obj["models"]["Pet"]["columns"].keys())
        self.assertTrue("tag" in obj["models"]["Pet"]["columns"].keys())
