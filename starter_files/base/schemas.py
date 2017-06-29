import uuid

from marshmallow import pre_load

from app import ma


class BaseSchema(ma.ModelSchema):
    @pre_load
    def auto_generate_id(self, data):
        if isinstance(data, dict) and data.get("identifier") is None:
            data["identifier"] = str(uuid.uuid4())
        return data
