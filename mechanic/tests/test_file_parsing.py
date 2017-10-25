from unittest import TestCase

from mechanic.src.reader import read_mechanicfile


class TestFileParsing(TestCase):
    def test_reader(self):
        options = read_mechanicfile("gen/mechanicfile")
        self.assertEqual(options.get("APP_NAME"), "grocery")
        self.assertEqual(options.get("OVERRIDE_BASE_CONTROLLER"),
                         "with controllers.base.MyController for controllers.default.ABCController")
