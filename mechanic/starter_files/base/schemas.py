import uuid
import requests

from marshmallow import fields, pre_load, post_dump

from app import ma


class BaseSchema(ma.ModelSchema):
    created = fields.DateTime(load_only=True, dump_only=True)
    last_modified = fields.DateTime(load_only=True, dump_only=True)
    locked = fields.Boolean(load_only=True, dump_only=True)
    etag = fields.String(load_only=True, dump_only=True)

    @pre_load
    def auto_generate_id(self, data):
        if isinstance(data, dict) and data.get("identifier") is None:
            data["identifier"] = str(uuid.uuid4())
        return data

    @post_dump
    def convert_to_uri(self, obj):
        embed = self.context.get("embed", [])

        for key, val in obj.items():
            if key not in embed and isinstance(val, dict):
                # only convert to uri if the object has a uri
                if val.get("uri"):
                    obj[key] = val.get("uri")
        return obj
