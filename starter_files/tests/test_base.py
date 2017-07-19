import unittest
import app


class BaseUnitTest(unittest.TestCase):
    # this attribute needs to be overridden in test cases inheriting from this class
    conf_file_path = "/etc/YOURAPPNAME/app.conf"

    def setUp(self):
        app.init_app(self.conf_file_path, app_type='TEST')
        self.app = app.app.test_client()
        self.app.testing = True

        app.db.drop_all()
        app.db.create_all()

    def tearDown(self):
        pass
