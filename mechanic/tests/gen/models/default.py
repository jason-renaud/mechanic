# do not modify - generated code at UTC 2017-11-03 20:55:37.452313
"""
import uuid
import datetime

from flask import url_for
from sqlalchemy.ext.hybrid import hybrid_property

from mechanic import utils
from grocery import db

from mechanic.base.models import MechanicBaseModelMixin
"""

import datetime

from flask import url_for
from sqlalchemy import Column, String, Integer, ForeignKey, Float, DateTime, create_engine, MetaData
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base

from mechanic.starter.base import utils

engine = create_engine("sqlite:///:memory:", echo=False)
metadata = MetaData()

Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()


def get_uri(context):
    try:
        return str(url_for(context.current_parameters["controller"], resource_id=context.current_parameters["identifier"]))
    except Exception:
        return None


class MechanicBaseModelMixin(object):
    identifier = Column(String(36), primary_key=True, nullable=False, default=utils.random_uuid)
    created = Column(DateTime, default=datetime.datetime.utcnow)
    last_modified = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    etag = Column(String(36), default=utils.random_uuid, onupdate=utils.random_uuid)
    controller = Column(String, default="orgcontactitemcontroller")
    uri = Column(String, default=get_uri)

"""



def get_uri(context):
    try:
        return str(url_for(context.current_parameters["controller"], resource_id=context.current_parameters["identifier"]))
    except Exception:
        return None
"""


class GroceryItem(MechanicBaseModelMixin, Base):
    """
    GroceryItem
    """
    __tablename__ = "groceryitems"
    #__table_args__ = {"schema": "default"}
    
    cart = Column(String(), nullable=False,)
    name = Column(String(), nullable=True,)
    price = Column(Float(), nullable=False,)
    quantity = Column(Integer(), nullable=False,)
    cart_id = Column(String(), ForeignKey("carts.identifier"), nullable=True,)
    groceries_id = Column(String(), ForeignKey("groceries.identifier"), nullable=True,)

    
class Wallet(MechanicBaseModelMixin, Base):
    """
    Wallet
    """
    __tablename__ = "my_wallet_tablename"
    #__table_args__ = {"schema": "default"}
    
    cash = Column(Float(), nullable=True,)
    owner = Column(String(), nullable=False,)
    shopper_id = Column(String(), ForeignKey("shoppers.identifier"), nullable=True,)
    cart_id = Column(String(), ForeignKey("carts.identifier"), nullable=True,)

    
class Shopper(MechanicBaseModelMixin, Base):
    """
    Shopper
    """
    __tablename__ = "shoppers"
    #__table_args__ = {"schema": "default"}
    
    name = Column(String(), nullable=False,)
    age = Column(Integer(), nullable=False,)
    wallet_string = Column(String(), nullable=False,)
    wallet_wallet = relationship("Wallet",  uselist=False,)

    
class Fruit(MechanicBaseModelMixin, Base):
    """
    Fruit
    """
    __tablename__ = "fruits"
    #__table_args__ = {"schema": "default"}
    
    fruit_string = Column(String(), nullable=False,)
    fruit_apple = relationship("Apple",  uselist=False,)
    fruit_banana = relationship("Banana",  uselist=False,)

    
class Apple(MechanicBaseModelMixin, Base):
    """
    Apple
    """
    __tablename__ = "apples"
    #__table_args__ = {"schema": "default"}
    
    kind = Column(String(), nullable=False,)
    fruit_id = Column(String(), ForeignKey("fruits.identifier"), nullable=True,)

    
class Banana(MechanicBaseModelMixin, Base):
    """
    Banana
    """
    __tablename__ = "bananas"
    #__table_args__ = {"schema": "default"}
    
    brand = Column(String(), nullable=False,)
    fruit_id = Column(String(), ForeignKey("fruits.identifier"), nullable=True,)

    
class Store(MechanicBaseModelMixin, Base):
    """
    Store
    """
    __tablename__ = "stores"
    #__table_args__ = {"schema": "default"}
    
    name = Column(String(), nullable=False,)
    employees = relationship("Employee", backref="store", uselist=True,)

    
class Employee(MechanicBaseModelMixin, Base):
    """
    Employee
    """
    __tablename__ = "employees"
    #__table_args__ = {"schema": "default"}
    
    name = Column(String(), nullable=False,)
    employeeid = Column(String(), nullable=False,)
    age = Column(Integer(), nullable=False,)
    store_id = Column(String(), ForeignKey("stores.identifier"), nullable=True,)

    
class Steak(MechanicBaseModelMixin, Base):
    """
    Steak
    """
    __tablename__ = "steaks"
    #__table_args__ = {"schema": "default"}
    
    steakType = Column(String(), nullable=False,)
    weight = Column(Float(), nullable=False,)
    cart = Column(String(), nullable=False,)
    name = Column(String(), nullable=True,)
    price = Column(Float(), nullable=False,)
    quantity = Column(Integer(), nullable=False,)

    
class Groceries(MechanicBaseModelMixin, Base):
    """
    Groceries
    """
    __tablename__ = "groceries"
    #__table_args__ = {"schema": "default"}
    
    groceries = relationship("GroceryItem", backref="groceries", uselist=True,)

    
class Cart(MechanicBaseModelMixin, Base):
    """
    Cart
    """
    __tablename__ = "carts"
    #__table_args__ = {"schema": "default"}
    
    cartitems_array_string = Column(String(), nullable=False,)
    cartitems_groceryitem = relationship("GroceryItem",  uselist=True,)
    cartitems_wallet = relationship("Wallet",  uselist=True,)

    
class Error(MechanicBaseModelMixin, Base):
    """
    Error
    """
    __tablename__ = "errors"
    #__table_args__ = {"schema": "default"}
    
    code = Column(Integer(), nullable=True,)
    message = Column(String(), nullable=True,)

    

Base.metadata.create_all(engine)
e1 = Employee(name="John", employeeid="123", age=32)
print(e1.name, e1.employeeid, e1.age, e1.store)
s = Store(name="ab", employees=[e1])
print(s.name)
print(s.employees)
print(e1.store)