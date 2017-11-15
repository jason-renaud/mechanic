# do not modify - generated code at UTC 2017-11-15 05:11:25.132879
from marshmallow import fields

from grocery import db
from models.default import (GroceryItem, Wallet, Shopper, Fruit, Apple, Banana, Store, Employee, Meat, Steak, Groceries, Cart, )
from mechanic.base.schemas import MechanicBaseModelSchema, MechanicBaseSchema
from mechanic.base.fields import MechanicEmbeddable
from schemas.cmdb import (MyBaseSchema, )


class GroceryItemSchema(MyBaseSchema):
    cart = MechanicEmbeddable("CartSchema", column="uri")

    class Meta:
        model = GroceryItem
        strict = True

    
class WalletSchema(MyBaseSchema):
    owner = MechanicEmbeddable("ShopperSchema", column="uri")

    class Meta:
        model = Wallet
        strict = True

    
class ShopperSchema(MyBaseSchema):
    wallet = MechanicEmbeddable("WalletSchema", column="uri")

    class Meta:
        model = Shopper
        strict = True

    
class FruitSchema(MyBaseSchema):
    fruit = MechanicEmbeddable("AppleSchema", column="uri")

    class Meta:
        model = Fruit
        strict = True

    
class AppleSchema(MyBaseSchema):

    class Meta:
        model = Apple
        strict = True

    
class BananaSchema(MyBaseSchema):

    class Meta:
        model = Banana
        strict = True

    
class StoreSchema(MyBaseSchema):

    class Meta:
        model = Store
        strict = True

    
class EmployeeSchema(MyBaseSchema):
    """
    Some description for an Employee object blah blah blah
    """
    subordinate = MechanicEmbeddable("EmployeeSchema", column="uri")
    store = MechanicEmbeddable("StoreSchema", column="uri")

    class Meta:
        model = Employee
        strict = True

    
class MeatSchema(MyBaseSchema):

    class Meta:
        model = Meat
        strict = True

    
class SteakSchema(MyBaseSchema):

    class Meta:
        model = Steak
        strict = True

    
class GroceriesSchema(MyBaseSchema):

    class Meta:
        model = Groceries
        strict = True

    
class CartSchema(MyBaseSchema):
    cartitems = MechanicEmbeddable("GroceryItemSchema", column="uri")

    class Meta:
        model = Cart
        strict = True

    
class ErrorSchema(MyBaseSchema):
    """
    ErrorSchema
    """
    code = fields.Integer(required=True, maxLength=2000, load_only=False, dump_only=False)
    message = fields.String(required=True, maxLength=2000, load_only=False, dump_only=False)