import unittest
import app


class BaseUnitTest(unittest.TestCase):
    def setUp(self):
        app.init_tugboat(app_type='TEST')
        self.app = app.app.test_client()
        self.app.testing = True

        #app.db.session.close()
        app.db.drop_all()
        app.db.create_all()

    def tearDown(self):
        #app.db.session.close()
        pass
