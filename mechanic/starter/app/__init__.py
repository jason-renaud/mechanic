import os
import logmatic
import logging
from importlib import util

from flask import Flask
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from app.config import app_config

api_exists = False
try:
    from app.api import init_api
    api_exists = True
except ImportError:
    pass

config = {
    "DEFAULT_LOG_NAME": "app",
    "BASE_API_PATH": os.getenv("MECHANIC_BASE_API_PATH", "/api")
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

    if api_exists:
        init_api(api)

    with app.app_context():
        # TODO - remove before prod
        db.session.commit()
        db.drop_all()
        db.create_all()

    from app.admin_init import init_models
    init_models(app, db)
    return app

