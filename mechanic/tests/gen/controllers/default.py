# do not modify - generated code at UTC 2017-11-15 05:11:25.140667

from mechanic.base.controllers import MechanicBaseController, MechanicBaseItemController, MechanicBaseCollectionController
from abc.mypackage.hello import (MyController, )

from models.default import (GroceryItem, Groceries, Shopper, )

from schemas.v100.default import (GroceryItemSchema, GroceriesSchema, ShopperSchema, )


class GroceryItemCollectionController(MechanicBaseCollectionController):
    responses = {
        "get": {
            "code": 200,
            "model": GroceryItem,
            "schema": GroceryItemSchema
        },
        "post": {
            "code": 201,
            "model": None,
            "schema": None
        },
    }
    requests = {
        "get": {
            "model": None,
            "schema": None
        },
        "post": {
            "model": GroceryItem,
            "schema": GroceryItemSchema
        },
    }

class GroceriesItemController(MyController):
    responses = {
        "get": {
            "code": 200,
            "model": Groceries,
            "schema": GroceriesSchema
        },
    }
    requests = {
        "get": {
            "model": None,
            "schema": None
        },
    }

class ShopperItemController(MechanicBaseItemController):
    responses = {
        "get": {
            "code": 200,
            "model": Shopper,
            "schema": ShopperSchema
        },
    }
    requests = {
        "get": {
            "model": None,
            "schema": None
        },
    }
