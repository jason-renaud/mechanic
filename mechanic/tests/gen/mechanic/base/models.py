import datetime

from flask import url_for
from sqlalchemy import Column, String, DateTime, create_engine, MetaData
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.ext.declarative import declarative_base

from grocery import db
from mechanic import utils

# engine = create_engine("sqlite:///:memory:", echo=False)
# metadata = MetaData()
#
# Base = declarative_base()
# Session = sessionmaker(bind=engine)
# session = Session()


def get_uri(context):
    try:
        print("####", context)
        return str(url_for(context.current_parameters["controller"], resource_id=context.current_parameters["identifier"]))
    except Exception as e:
        print("@@@@", e)
        return None


class MechanicBaseModelMixin(object):
    identifier = db.Column(db.String(36), primary_key=True, nullable=False, default=utils.random_uuid)
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_modified = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    etag = db.Column(db.String(36), default=utils.random_uuid, onupdate=utils.random_uuid)