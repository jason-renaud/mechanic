import time

from flask import Flask, render_template
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from sqlalchemy.exc import OperationalError

from .init_api import init_api

BASE_API_PATH = "/api"

db = SQLAlchemy()
ma = Marshmallow()


def create_app():
    app = Flask(__name__)
    {%- if db_url %}
    app.config["SQLALCHEMY_DATABASE_URI"] = "{{ db_url }}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    {%- endif %}
    api = Api(app)
    db.init_app(app)
    ma.init_app(app)

    init_api(api)

    @app.route("/")
    @app.route("{{ base_api_path }}")
    def home():
        return render_template("index.html")

    {%- if db_url %}
    with app.app_context():
        # TODO - remove drop_all and create_all before prod - consider using alembic instead.
        try:
            db.session.commit()
            db.drop_all()
            db.create_all()
        except OperationalError:
            time.sleep(3)
            db.session.commit()
            db.drop_all()
            db.create_all()
    {%- endif %}
    return app
