import os
from unittest import TestCase
import shutil

from mechanic.src.generator import Generator
from mechanic.src.reader import read_mechanicfile


class TestV100(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        for item in os.listdir("gen"):
            if os.path.isdir(os.path.realpath("gen/" + item)):
                shutil.rmtree(os.path.realpath("gen/" + item))

    def test_directory_structure(self):
        options = read_mechanicfile("gen/mechanicfile")
        gen = Generator("gen", options=options)
        gen.create_dir_structure()

        self.assertTrue(os.path.exists("gen/models/__init__.py"))
        self.assertTrue(os.path.exists("gen/schemas/__init__.py"))
        self.assertTrue(os.path.exists("gen/controllers/__init__.py"))
