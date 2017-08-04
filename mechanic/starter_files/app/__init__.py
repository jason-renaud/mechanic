import os
import logmatic
import logging

from flask import Flask
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from app.api import init_api
from app.config import app_config

config = {
    "DEFAULT_LOG_NAME": "operation-app",
    "BASE_API_PATH": "/api"
}

logger = logging.getLogger(config["DEFAULT_LOG_NAME"])
handler = logging.StreamHandler()
handler.setFormatter(logmatic.JsonFormatter())

logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

db = SQLAlchemy()
ma = Marshmallow()


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(app_config[config_name])
    app.config.from_pyfile("config.py")

    db.init_app(app)
    ma.init_app(app)
    api = Api(app)
    init_api(api)

    with app.app_context():
        # TODO - remove before prod
        db.session.commit()
        db.drop_all()
        db.create_all()
    return app

