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


class CustomBaseSchema(BaseSchema):
    pass


class CustomBaseModelSchema(BaseModelSchema):
    pass
    # @post_dump
    # def convert_to_uri(self, obj):
    #     embed = self.context.get("embed", [])
    #
    #     for key, val in obj.items():
    #         if key not in embed and isinstance(val, dict):
    #             # only convert to uri if the object has a uri
    #             if val.get("uri"):
    #                 obj[key] = val.get("uri")
    #     return obj
