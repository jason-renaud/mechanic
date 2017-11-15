# do not modify - generated code at UTC 2017-11-15 05:11:25.121782
import uuid
import datetime

from flask import url_for

from grocery import db
from mechanic.base.models import MechanicBaseModelMixin


def get_uri(context):
    try:
        return str(url_for(context.current_parameters["controller"], resource_id=context.current_parameters["identifier"]))
    except Exception:
        return None


class GroceryItem(MechanicBaseModelMixin, db.Model):
    """
    GroceryItem
    """
    __tablename__ = "groceryitems"
    __table_args__ = {"schema": "default"}
    
    controller = db.Column(db.String(), default="groceryitemcollectioncontroller")
    uri = db.Column(db.String, default=get_uri)
    name = db.Column(db.String(), nullable=False,)
    price = db.Column(db.Float(), nullable=True,)
    quantity = db.Column(db.Integer(), nullable=True,)
    cart_id = db.Column(db.String(), db.ForeignKey("default.carts.identifier"), nullable=True,)
    groceries_id = db.Column(db.String(), db.ForeignKey("default.groceries.identifier"), nullable=True,)
    cart = db.relationship("Cart",  uselist=False,)


class Wallet(MechanicBaseModelMixin, db.Model):
    """
    Wallet
    """
    __tablename__ = "my_wallet_tablename"
    __table_args__ = {"schema": "default"}
    
    controller = db.Column(db.String(), default="")
    uri = db.Column(db.String, default=get_uri)
    cash = db.Column(db.Float(), nullable=False,)
    shopper_id = db.Column(db.String(), db.ForeignKey("default.shoppers.identifier"), nullable=True,)
    owner = db.relationship("Shopper",  uselist=False,)


class Shopper(MechanicBaseModelMixin, db.Model):
    """
    Shopper
    """
    __tablename__ = "shoppers"
    __table_args__ = {"schema": "default"}
    
    controller = db.Column(db.String(), default="shopperitemcontroller")
    uri = db.Column(db.String, default=get_uri)
    name = db.Column(db.String(), nullable=True,)
    age = db.Column(db.Integer(), nullable=True,)
    wallet = db.relationship("Wallet",  uselist=False,)


class Fruit(MechanicBaseModelMixin, db.Model):
    """
    Fruit
    """
    __tablename__ = "fruits"
    __table_args__ = {"schema": "default"}
    
    controller = db.Column(db.String(), default="")
    uri = db.Column(db.String, default=get_uri)
    fruit = db.relationship("Apple",  uselist=False,)


class Apple(MechanicBaseModelMixin, db.Model):
    """
    Apple
    """
    __tablename__ = "apples"
    __table_args__ = {"schema": "default"}
    
    controller = db.Column(db.String(), default="")
    uri = db.Column(db.String, default=get_uri)
    kind = db.Column(db.String(), nullable=True,)
    fruit_id = db.Column(db.String(), db.ForeignKey("default.fruits.identifier"), nullable=True,)


class Banana(MechanicBaseModelMixin, db.Model):
    """
    Banana
    """
    __tablename__ = "bananas"
    __table_args__ = {"schema": "default"}
    
    controller = db.Column(db.String(), default="")
    uri = db.Column(db.String, default=get_uri)
    brand = db.Column(db.String(), nullable=True,)


class Store(MechanicBaseModelMixin, db.Model):
    """
    Store
    """
    __tablename__ = "stores"
    __table_args__ = {"schema": "default"}
    
    controller = db.Column(db.String(), default="")
    uri = db.Column(db.String, default=get_uri)
    name = db.Column(db.String(), nullable=True,)
    employees = db.relationship("Employee",  uselist=True,)


class Employee(MechanicBaseModelMixin, db.Model):
    """
    Employee
    """
    __tablename__ = "employees"
    __table_args__ = {"schema": "default"}
    
    controller = db.Column(db.String(), default="")
    uri = db.Column(db.String, default=get_uri)
    name = db.Column(db.String(), nullable=True,)
    eid = db.Column(db.String(), nullable=True,)
    age = db.Column(db.Integer(), nullable=True,)
    employee_id = db.Column(db.String(), db.ForeignKey("default.employees.identifier"), nullable=True,)
    store_id = db.Column(db.String(), db.ForeignKey("default.stores.identifier"), nullable=True,)
    subordinate = db.relationship("Employee",  uselist=False,)
    store = db.relationship("Store",  uselist=False,)


class Meat(MechanicBaseModelMixin, db.Model):
    """
    Meat
    """
    __tablename__ = "meats"
    __table_args__ = {"schema": "default"}
    
    controller = db.Column(db.String(), default="")
    uri = db.Column(db.String, default=get_uri)
    type = db.Column(db.String(), nullable=True,)
    animal = db.Column(db.String(), nullable=True,)


class Steak(MechanicBaseModelMixin, db.Model):
    """
    Steak
    """
    __tablename__ = "steaks"
    __table_args__ = {"schema": "default"}
    
    controller = db.Column(db.String(), default="")
    uri = db.Column(db.String, default=get_uri)
    steakType = db.Column(db.String(), nullable=True,)
    weight = db.Column(db.Float(), nullable=True,)
    type = db.Column(db.String(), nullable=True,)
    animal = db.Column(db.String(), nullable=True,)


class Groceries(MechanicBaseModelMixin, db.Model):
    """
    Groceries
    """
    __tablename__ = "groceries"
    __table_args__ = {"schema": "default"}
    
    controller = db.Column(db.String(), default="groceriesitemcontroller")
    uri = db.Column(db.String, default=get_uri)
    groceries = db.relationship("GroceryItem",  uselist=True,)


class Cart(MechanicBaseModelMixin, db.Model):
    """
    Cart
    """
    __tablename__ = "carts"
    __table_args__ = {"schema": "default"}
    
    controller = db.Column(db.String(), default="")
    uri = db.Column(db.String, default=get_uri)
    cartitems = db.relationship("GroceryItem",  uselist=True,)

