import unittest
import app


class BaseUnitTest(unittest.TestCase):
    def setUp(self):
        print("ERROR: edit line below this in test_base.py to get your unit tests running with nose2.")
        app.init_app("/etc/YOURAPPNAME/app.conf", app_type='TEST')
        self.app = app.app.test_client()
        self.app.testing = True

        app.db.drop_all()
        app.db.create_all()

    def tearDown(self):
        pass
