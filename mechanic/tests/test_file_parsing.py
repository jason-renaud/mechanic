from unittest import TestCase

from mechanic.src.reader import read_mechanicfile


class TestFileParsing(TestCase):
    def test_reader(self):
        options = read_mechanicfile("gen/mechanic.json")
        self.assertEqual(options.get("APP_NAME"), "petstore")
        self.assertEqual(options.get("OVERRIDE_BASE_CONTROLLER").get("with"), "controllers.base.MyController")
        self.assertEqual(options.get("OVERRIDE_BASE_CONTROLLER").get("for"), "controllers.default.ABCController")
