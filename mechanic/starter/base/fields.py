from marshmallow import fields, pprint
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
        raise ValidationError(attr + ": does not match any of the possible field types.")

    def _deserialize(self, value, attr, data):
        for item in self.field_types:
            try:
                item._validate(value)
                return item._deserialize(value, attr, data)
            except ValidationError:
                pass
        raise ValidationError(attr + ": does not match any of the possible field types.")


# class Expandable(OneOf):
#     """
#     Allows an object to be expanded by it's uri.
#
#     :param nested_schema
#     :param nested_model
#     """
#     def __init__(self, nested_schema=None, nested_model=None, **kwargs):
#         super(Expandable, self).__init__(field_types=[nested_schema, fields.String()], **kwargs)
#         self.nested_model = nested_model
#         self.nested_schema = nested_schema
#
#     def _serialize(self, value, attr, obj):
#         for type in self.field_types:
#             try:
#                 type._validate(value)
#                 return type._serialize(value, attr, obj)
#             except ValidationError as e:
#                 pass
#         raise ValidationError(attr + ": does not match any of the possible field types.")
#
#     def _deserialize(self, value, attr, data):
#         if isinstance(value, str):
#             # the String() field type
#             self.field_types[1]._validate(value)
#
#             # expand the uri
#             obj_from_uri = self.nested_model.query.get(value.rsplit("/", 1)[1])
#             if not obj_from_uri:
#                 raise ValidationError("Resource with uri: '" + value + "' not found.")
#
#             schema = self.nested_schema.schema
#             return self.nested_schema._deserialize(schema.dump(obj_from_uri).data, attr, data)
#         else:
#             # the Nested() schema field type
#             return self.field_types[0]._deserialize(value, attr, data)
