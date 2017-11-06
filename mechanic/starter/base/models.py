import datetime

from flask import url_for
from sqlalchemy import Column, String, DateTime, create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from mechanic import utils

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
