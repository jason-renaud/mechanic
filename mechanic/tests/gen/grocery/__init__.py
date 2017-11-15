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
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:postgres@cmdb-postgres:5432/sample"
    api = Api(app)
    db.init_app(app)
    ma.init_app(app)
    
    from controllers.default import (GroceryItemCollectionController, GroceriesItemController, ShopperItemController, )
    api.add_resource(GroceryItemCollectionController, "/api/groceries")
    api.add_resource(GroceriesItemController, "/api/groceries/<string:resource_id>")
    api.add_resource(ShopperItemController, "/api/shoppers/<string:resource_id>")

    @app.route("/")
    @app.route("/api")
    def home():
        return render_template("index.html")
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
    return app