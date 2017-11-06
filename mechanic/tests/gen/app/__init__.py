from flask import Flask
from flask_restful import Api

# import controllers
from mechanic.tests.gen.controllers.test_ctlr import TestCTRL


def create_app():
    app = Flask(__name__)
    api = Api(app)

    # initialize API
    api.add_resource(TestCTRL, "/test")

    @app.route("/")
    @app.route("/api")
    def home():
        return "home"

    # with app.app_context():
    #     # TODO - remove before prod
    #     Base.metadata.drop_all(engine)
    #     Base.metadata.create_all(engine)
    return app
