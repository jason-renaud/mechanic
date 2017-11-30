from marshmallow import fields

from {{ app_name}} import ma, db


class MechanicBaseModelSchema(ma.ModelSchema):
    created = fields.DateTime(load_only=True, dump_only=True)
    last_modified = fields.DateTime(load_only=True, dump_only=True)
    locked = fields.Boolean(load_only=True, dump_only=True)
    etag = fields.String(load_only=True, dump_only=True)
    controller = fields.String(load_only=True, dump_only=True)
    uri = fields.String(dump_only=True)
    identifier = fields.String(dump_only=True)

    class Meta:
        strict = True
        sqla_session = db.session


class MechanicBaseSchema(ma.Schema):
    created = fields.DateTime(load_only=True, dump_only=True)
    last_modified = fields.DateTime(load_only=True, dump_only=True)
    locked = fields.Boolean(load_only=True, dump_only=True)
    etag = fields.String(load_only=True, dump_only=True)
    uri = fields.String(dump_only=True)
    identifier = fields.String(dump_only=True)
