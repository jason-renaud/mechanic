import logging
import app
import uuid

from flask import request, make_response
from flask_restful import Resource
from marshmallow.exceptions import ValidationError
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm.exc import UnmappedInstanceError

from app import db
from base.exceptions import MechanicException, MechanicNotFoundException, MechanicResourceAlreadyExistsException

logger = logging.getLogger(app.config['DEFAULT_LOG_NAME'])
PRIMARY_KEY_NAME = "identifier"


class BaseCollectionController(Resource):
    schema = None
    required_roles = []
    service_class = None
    responses = {
        "get": {
            "code": 200,
            "model": None,
            "schema": None,
            "query_params": []
        },
        "post": {
            "code": 201,
            "model": None,
            "schema": None,
            "query_params": []
        }
    }

    def post(self):
        try:
            request_body = request.get_json(force=True)

            # If user passes in 'identifier' field, but the resource already exists, raise exception
            if request_body.get(PRIMARY_KEY_NAME):
                model_instance = self.responses["post"]["model"].query.get(request_body.get(PRIMARY_KEY_NAME))

                if model_instance is not None:
                    logger.error("Resource with id %s already exists.", request_body.get(PRIMARY_KEY_NAME))
                    raise MechanicResourceAlreadyExistsException(
                        msg="Resource with " + PRIMARY_KEY_NAME + ": " + request_body.get(PRIMARY_KEY_NAME) +
                            " already exists.",
                        res="Remove the '" + PRIMARY_KEY_NAME + "' attribute from the request body and try again.")

            # do any work needed before validation
            service = self.service_class()
            modified_data = service.post_before_validation(request_body)

            # validate the schema
            schema = self.responses["post"]["schema"]()
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
        except MechanicException as e:
            error_response = {
                "message": e.message,
                "resolution": e.resolution
            }
            logger.error(error_response)
            return error_response, e.status_code

        updated_response = service.handle_query_parameters(request, schema.jsonify(model_instance), self.responses["post"]["query_params"])
        return make_response(updated_response, self.responses["post"]["code"])

    def get(self):
        models = self.responses["get"]["model"].query.all()
        schema = self.responses["get"]["schema"](many=True)

        # If no items are found, return 204 'NO CONTENT'
        if len(models) is 0:
            resp_code = 204
        else:
            resp_code = self.responses["get"]["code"]

        service = self.service_class()
        updated_response = service.handle_query_parameters(request, schema.jsonify(models), self.responses["get"]["query_params"])
        return make_response(updated_response, resp_code)


class BaseController(Resource):
    schema = None
    required_roles = []
    service_class = None
    responses = {
        "get": {
            "code": 200,
            "model": None,
            "schema": None,
            "query_params": []
        },
        "put": {
            "code": 200,
            "model": None,
            "schema": None,
            "query_params": []
        },
        "delete": {
            "code": 204,
            "model": None,
            "schema": None,
            "query_params": []
        }
    }

    def get(self, resource_id):
        model_instance = self.responses["get"]["model"].query.get(resource_id)
        model_schema = self.responses["get"]["schema"]()

        # If no item found, return 204 'NO CONTENT'
        if model_instance is None:
            resp_code = 204
        else:
            resp_code = self.responses["get"]["code"]

        service = self.service_class()
        updated_response = service.handle_query_parameters(request, model_schema.jsonify(model_instance), self.responses["get"]["query_params"])
        return make_response(updated_response, resp_code)

    def put(self, resource_id):
        try:
            request_body = request.get_json(force=True)

            # TODO - etag validation

            # do any work needed before validation
            service = self.service_class()
            modified_request_body = service.put_before_validation(request_body)

            model_instance = self.responses["get"]["model"].query.get(resource_id)

            if model_instance is None:
                raise MechanicNotFoundException()

            schema = self.responses["put"]["schema"]()

            # serialize existing model into dictionary
            obj_to_save = schema.dump(model_instance).data

            # update with new attributes
            for attribute in modified_request_body:
                obj_to_save[attribute] = modified_request_body[attribute]

            # deserialize into model object
            updated_model_instance = schema.load(obj_to_save)

            # do any work needed after initial schema validation
            service.put_after_validation(updated_model_instance.data)
            updated_response = service.handle_query_parameters(request, schema.jsonify(updated_model_instance.data), self.responses["put"]["query_params"])

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
        except MechanicException as e:
            error_response = {
                "message": e.message,
                "resolution": e.resolution
            }
            logger.error(error_response)
            return error_response, e.status_code
        return make_response(updated_response, self.responses["put"]["code"])

    def delete(self, resource_id):
        try:
            model_class = self.responses["delete"]["model"] or self.responses["get"]["model"]
            model_instance = model_class.query.get(resource_id)

            if model_instance is None:
                raise MechanicNotFoundException()

            service = self.service_class()
            updated_response = service.handle_query_parameters(request, '', self.responses["delete"]["query_params"])

            db.session.delete(model_instance)
            db.session.commit()
        except MechanicException as e:
            error_response = {
                "message": e.message,
                "resolution": e.resolution
            }
            logger.error(error_response)
            return error_response, e.status_code

        return updated_response, self.responses["delete"]["code"]
