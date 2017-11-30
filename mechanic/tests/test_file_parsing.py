import os
from unittest import TestCase

from mechanic.src.reader import read_mechanicfile


class TestFileParsing(TestCase):
    MECHANIC_BUILD_FILE = os.path.dirname(__file__) + "/gen/mechanic-grocery.json"

    def test_reader(self):
        options = read_mechanicfile(self.MECHANIC_BUILD_FILE)
        self.assertEqual(options.get("APP_NAME"), "grocery")
        self.assertEqual(options.get("OVERRIDE_BASE_CONTROLLER")[0].get("with"), "abc.mypackage.hello.MyController")
        self.assertEqual(options.get("OVERRIDE_BASE_CONTROLLER")[0].get("for")[0], "controllers.default.GroceriesItemController")
