import logging
import app
import uuid

from flask import request, make_response
from flask_restful import Resource
from marshmallow.exceptions import ValidationError
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm.exc import UnmappedInstanceError

from app import db
from base.exceptions import TugboatException, TugboatNotFoundException, TugboatResourceAlreadyExistsException

logger = logging.getLogger(app.config['DEFAULT_LOG_NAME'])
PRIMARY_KEY_NAME = "identifier"


class BaseCollectionController(Resource):
    model = None
    schema = None
    required_roles = []
    service_class = None

    def post(self):
        try:
            request_body = request.get_json(force=True)

            # If user passes in 'identifier' field, but the resource already exists, raise exception
            if request_body.get(PRIMARY_KEY_NAME):
                model_instance = self.model.query.get(request_body.get(PRIMARY_KEY_NAME))

                if model_instance is not None:
                    logger.error("Resource with id %s already exists.", request_body.get(PRIMARY_KEY_NAME))
                    raise TugboatResourceAlreadyExistsException(
                        msg="Resource with " + PRIMARY_KEY_NAME + ": " + request_body.get(PRIMARY_KEY_NAME) +
                            " already exists.",
                        res="Remove the '" + PRIMARY_KEY_NAME + "' attribute from the request body and try again.")

            # do any work needed before validation
            service = self.service_class()
            modified_data = service.post_before_validation(request_body)

            schema = self.schema()
            model_instance, errors = schema.load(modified_data)
            schema.validate(modified_data)

            # do any work needed after initial schema validation
            service.post_after_validation(model_instance)

            # save to DB
            db.session.add(model_instance)
            db.session.commit()
        except ValidationError as e:
            error_response = {
                "message": e.messages,
                "resolution": "Retry the operation with a valid object."
            }
            return error_response, 400
        except DatabaseError as e:
            # TODO - make more meaningful errors
            db.session.close()
            logger.error(e.orig)
            error_response = {
                "message": "The given object is not valid.",
                "resolution": "Retry the operation with a valid object."
            }
            return error_response, 400
        except TugboatException as e:
            error_response = {
                "message": e.message,
                "resolution": e.resolution
            }
            logger.error(error_response)
            return error_response, e.status_code
        return make_response(schema.jsonify(model_instance), 201)

    def get(self):
        models = self.model.query.all()
        schema = self.schema(many=True)

        # If no items are found, return 204 'NO CONTENT'
        if len(models) is 0:
            resp_code = 204
        else:
            resp_code = 200
        return make_response(schema.jsonify(models), resp_code)


class BaseController(Resource):
    model = None
    schema = None
    required_roles = []
    service_class = None

    def get(self, resource_id):
        model_instance = self.model.query.get(resource_id)
        model_schema = self.schema()

        # If no item found, return 204 'NO CONTENT'
        if model_instance is None:
            resp_code = 204
        else:
            resp_code = 200

        return make_response(model_schema.jsonify(model_instance), resp_code)

    def put(self, resource_id):
        try:
            request_body = request.get_json(force=True)

            # TODO - etag validation

            # do any work needed before validation
            service = self.service_class()
            modified_request_body = service.put_before_validation(request_body)

            model_instance = self.model.query.get(resource_id)

            if model_instance is None:
                raise TugboatNotFoundException()

            schema = self.schema()

            # serialize existing model into dictionary
            obj_to_save = schema.dump(model_instance).data

            # update with new attributes
            for attribute in modified_request_body:
                obj_to_save[attribute] = modified_request_body[attribute]

            # deserialize into model object
            updated_model_instance = schema.load(obj_to_save)

            # do any work needed after initial schema validation
            service.put_after_validation(updated_model_instance.data)

            # save to DB
            db.session.commit()
        except ValidationError as e:
            error_response = {
                "message": e.messages,
                "resolution": "Retry the operation with a valid object."
            }
            logger.error(error_response)
            return error_response, 400
        except DatabaseError as e:
            db.session.close()
            logger.error(e.orig)
            error_response = {
                "message": "The given object is not valid.",
                "resolution": "Retry the operation with a valid object."
            }
            logger.error(error_response)
            return error_response, 400
        except TugboatException as e:
            error_response = {
                "message": e.message,
                "resolution": e.resolution
            }
            logger.error(error_response)
            return error_response, e.status_code
        return make_response(schema.jsonify(updated_model_instance.data), 200)

    def delete(self, resource_id):
        try:
            model_instance = self.model.query.get(resource_id)

            if model_instance is None:
                raise TugboatNotFoundException()

            db.session.delete(model_instance)
            db.session.commit()
        except TugboatException as e:
            error_response = {
                "message": e.message,
                "resolution": e.resolution
            }
            logger.error(error_response)
            return error_response, e.status_code

        return '', 204
