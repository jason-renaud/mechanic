import time

from flask import Flask, render_template
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from sqlalchemy.exc import OperationalError

config = {
    "DEFAULT_LOG_NAME": "app",
    "BASE_API_PATH": "/api"
}

db = SQLAlchemy()
ma = Marshmallow()


def create_app():
    app = Flask(__name__)
    {%- if db_url %}
    app.config["SQLALCHEMY_DATABASE_URI"] = "{{ db_url }}"
    {%- endif %}
    api = Api(app)
    db.init_app(app)
    ma.init_app(app)
    {# #}
    {%- for controller_path, controller_names in dependent_controllers.items() %}
    from {{ controller_path }} import ({% for name in controller_names %}{{ name}}, {% endfor %})
    {%- endfor %}
    {%- for controller_name, controller in controllers.items() %}
    api.add_resource({{ controller_name }}, "{{ base_api_path }}{{ controller.uri }}")
    {%- endfor %}

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
