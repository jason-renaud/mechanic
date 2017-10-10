from marshmallow import fields
from marshmallow.exceptions import ValidationError


class OneOf(fields.Field):
    def __init__(self, field_types=[], **kwargs):
        super(OneOf, self).__init__(**kwargs)
        self.field_types = field_types

    def _serialize(self, value, attr, obj):
        vals = []
        for item in self.field_types:
            # add serialized values to array
            vals.append(item._serialize(value, attr, obj))

        # return the first value that is not None, [], {}, etc.
        for val in vals:
            if val:
                return val
        return None

    def _deserialize(self, value, attr, data):
        for item in self.field_types:
            try:
                item._validate(value)
                return item._deserialize(value, attr, data)
            except ValidationError:
                pass
        raise ValidationError(attr + ": does not match any of the possible field types.")

