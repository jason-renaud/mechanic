import os
import logmatic
import logging
import configparser

from flask import Flask
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from app.api import init_api

config = {
    "DEFAULT_LOG_NAME": "operation-app",
    "BASE_API_PATH": "/api"
}

"""
parser = configparser.ConfigParser()
parser.read("/etc/app/app.conf")

settings = {
    "DEV_DB": parser.get("database", "dev"),
    "STAGING_DB": parser.get("database", "staging"),
    "TEST_DB": parser.get("database", "test"),
    "PRO_DB": parser.get("database", "pro")
}
"""

logger = logging.getLogger(config["DEFAULT_LOG_NAME"])
handler = logging.StreamHandler()
handler.setFormatter(logmatic.JsonFormatter())

logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

app = None
db = None
ma = None
api = None
settings = None


def init_app(conf_file_path, app_type="DEV"):
    parser = configparser.ConfigParser()
    parser.read(conf_file_path)

    global settings
    settings = {
        "DEV_DB": parser.get("database", "dev"),
        "STAGING_DB": parser.get("database", "staging"),
        "TEST_DB": parser.get("database", "test"),
        "PRO_DB": parser.get("database", "pro"),
        "PORT": parser.get("server", "port")
    }

    logger.info("Init app...")
    db_uri = settings["DEV_DB"]
    global app
    app = Flask(__name__)

    if app_type is "DEV":
        db_uri = settings["DEV_DB"]
        app.config["DEBUG"] = True
    elif app_type is "TEST":
        db_uri = settings["TEST_DB"]
        app.config["DEBUG"] = True
        app.config["PORT"] = 5001

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri

    global db
    db = SQLAlchemy(app)

    global api
    api = Api(app)

    global ma
    ma = Marshmallow(app)

    init_api(api)
    # TODO drop_all() is development only, remove before production
    db.drop_all()
    db.create_all()


