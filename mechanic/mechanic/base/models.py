import datetime

from flask import url_for

from {{ app_name }} import db
from mechanic import utils


def get_uri(context):
    try:
        return str(url_for(context.current_parameters["controller"], resource_id=context.current_parameters["identifier"]))
    except Exception as e:
        return None


class MechanicBaseModelMixin(object):
    identifier = db.Column(db.String(36), primary_key=True, nullable=False, default=utils.random_uuid)
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_modified = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    etag = db.Column(db.String(36), default=utils.random_uuid, onupdate=utils.random_uuid)
