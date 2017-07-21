import unittest
import pprint
import json

import app


class BaseUnitTest(unittest.TestCase):
    # this attribute needs to be overridden in test cases inheriting from this class
    conf_file_path = "/etc/YOURAPPNAME/app.conf"
    pp = pprint.PrettyPrinter(indent=4)

    def setUp(self):
        app.init_app(self.conf_file_path, app_type="TEST")
        self.app = app.app.test_client()
        self.app.testing = True

        app.db.drop_all()
        app.db.create_all()

    def tearDown(self):
        pass

    # taken from and modified:
    # https://stackoverflow.com/questions/25851183/how-to-compare-two-json-objects-with-the-same-elements-in-a-different-order-equa
    def ordered(self, obj, remove_attr=[]):
        [obj.pop(x) for x in remove_attr if isinstance(obj, dict)]

        if isinstance(obj, dict):
            return sorted((k, self.ordered(v, remove_attr=remove_attr)) for k, v in obj.items())
        if isinstance(obj, list):
            return sorted(self.ordered(x, remove_attr=remove_attr) for x in obj)
        else:
            return obj

    def compare(self, obj1, obj2, ignore_attr=[]):
        return self.ordered(obj1, remove_attr=ignore_attr) == self.ordered(obj2, remove_attr=ignore_attr)
