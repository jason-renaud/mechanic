import uuid

from marshmallow import fields, pre_load, post_dump

from app import ma, db


class BaseModelSchema(ma.ModelSchema):
    created = fields.DateTime(load_only=True, dump_only=True)
    last_modified = fields.DateTime(load_only=True, dump_only=True)
    locked = fields.Boolean(load_only=True, dump_only=True)
    etag = fields.String(load_only=True, dump_only=True)
    controller = fields.String(load_only=True, dump_only=True)

    class Meta:
        strict = True
        sqla_session = db.session


class BaseSchema(ma.Schema):
    created = fields.DateTime(load_only=True, dump_only=True)
    last_modified = fields.DateTime(load_only=True, dump_only=True)
    locked = fields.Boolean(load_only=True, dump_only=True)
    etag = fields.String(load_only=True, dump_only=True)

