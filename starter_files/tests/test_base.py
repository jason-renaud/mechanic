import pprint
from flask_testing import TestCase
from flask_restful import Api
from flask_marshmallow import Marshmallow
from app.api import init_api
from app import create_app, db, api


class BaseUnitTest(TestCase):
    # used for debugging
    pp = pprint.PrettyPrinter(indent=4)

    def create_app(self):
        # pass in test configurations
        config_name = "testing"
        app = create_app(config_name)
        return app

    def setUp(self):
        db.session.commit()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_db(self):
        db.create_all()

    def drop_db(self):
        db.session.remove()
        db.drop_all()

    # taken from and modified:
    # https://stackoverflow.com/questions/25851183/how-to-compare-two-json-objects-with-the-same-elements-in-a-different-order-equa
    def ordered(self, obj, remove_attr=[]):
        if isinstance(obj, dict):
            [obj.pop(x) for x in remove_attr if x in obj.keys()]
            return sorted((k, self.ordered(v, remove_attr=remove_attr)) for k, v in obj.items())
        if isinstance(obj, list):
            for x in obj:
                if isinstance(x, dict):
                    [x.pop(key) for key in remove_attr if key in x.keys()]
                    return sorted((k, self.ordered(v, remove_attr=remove_attr)) for k, v in x.items())
            return sorted(self.ordered(x, remove_attr=remove_attr) for x in obj)
        else:
            return obj

    def compare(self, obj1, obj2, ignore_attr=[]):
        return self.ordered(obj1, remove_attr=ignore_attr) == self.ordered(obj2, remove_attr=ignore_attr)

