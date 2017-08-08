import logging
import app
import functools
import requests

from flask import request, make_response
from flask_restful import Resource
from marshmallow.exceptions import ValidationError
from sqlalchemy.exc import DatabaseError
from requests.exceptions import ConnectionError

from app import db
from base import db_rest_helper as db_helper
from base.exceptions import MechanicException, MechanicNotFoundException, MechanicResourceAlreadyExistsException, \
    MechanicBadRequestException, MechanicNotModifiedException

logger = logging.getLogger(app.config['DEFAULT_LOG_NAME'])
PRIMARY_KEY_NAME = "identifier"
DEFAULT_COLLECTION_LIMIT = 100


def convert_to_uri(request_obj, model_obj):
    uri = request_obj.path + "/" + model_obj.identifier
    return uri


def parse_query_params(request_obj, valid_filters, supported_queries):
    params = dict()
    limit_val = DEFAULT_COLLECTION_LIMIT
    sort_key = None
    embed_list = []
    filter_list = []
    custom_list = []

    for param, param_val in request_obj.args.items():
        if param == "limit" and param in supported_queries:
            try:
                if int(param_val) < 0 or int(param_val) > DEFAULT_COLLECTION_LIMIT:
                    logger.warning(
                        "Query param 'limit' with value [%s] is invalid, ignoring. Must be between 0 and 100.",
                        param_val)
                else:
                    limit_val = int(param_val)
            except ValueError as e:
                logger.warning("Query param 'limit' with value [%s] is invalid, ignoring.", param_val)

        elif param == "sort" and param in supported_queries:
            sort_key = param_val
        elif param == "embed" and param in supported_queries:
            embed_list.append(param_val)
        elif param in valid_filters:
            filter_list.append((param, param_val))
        elif param in supported_queries:
            custom_list.append((param, param_val))

    params["limit"] = limit_val
    params["filters"] = filter_list
    params["sort"] = sort_key
    params["embed"] = embed_list
    params["custom"] = custom_list
    return params


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
            created_model = db_helper.create(model_instance)
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

        return make_response(schema.jsonify(created_model), self.responses["post"]["code"])

    def get(self):
        """
        Order of operations of query parameters:
            1) filter
            2) sort
            3) apply limit
            4) apply embed
        """
        model_obj = self.responses["get"]["model"]

        # Use attributes from model as valid filters, unless it starts with a "_", implying it's a hidden attribute.
        valid_filters = [item for item in dir(model_obj()) if not item.startswith("_")]

        # parse all query params
        params = parse_query_params(request, valid_filters, self.requests["get"]["query_params"])
        filtered_models = []

        # apply filters
        if params.get("filters"):
            for filter_key, filter_val in params.get("filters"):
                filtered_models.append(model_obj.query.filter_by(**{filter_key: filter_val}).all())

            models = functools.reduce(lambda x, y: list(set(x) & set(y)), filtered_models)
        else:
            models = model_obj.query.all()

        # apply sorting
        if params.get("sort"):
            reverse_order = params.get("sort").startswith("-")
            sort_key = params.get("sort")[1:] if params.get("sort").startswith("-") else params.get("sort")
            models.sort(key=lambda x: getattr(x, sort_key), reverse=reverse_order)

        # apply limit
        if params.get("limit"):
            models = models[:int(params.get("limit"))]

        # TODO - apply 'embed'

        # Handle custom query parameters defined in openapi spec
        service = self.service_class()
        models = service.handle_custom_query_params(params, models)

        # If no items are found, return 204 'NO CONTENT'
        if models is None or len(models) is 0:
            resp_code = 204
        else:
            resp_code = self.responses["get"]["code"]

        schema = self.responses["get"]["schema"](many=True)
        return make_response(schema.jsonify(models), resp_code)


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
        if_match = request.headers.get("If-Match", "").split(",")
        if "" in if_match:
            if_match.remove("")

        if_none_match = request.headers.get("If-None-Match", "").split(",")
        if "" in if_none_match:
            if_none_match.remove("")

        if_modified_since = request.headers.get("If-Modified-Since")
        if_unmodified_since = request.headers.get("If-Unmodified-Since")

        try:
            model_instance = db_helper.read(resource_id, self.responses["get"]["model"], if_modified_since=if_modified_since, if_unmodified_since=if_unmodified_since, if_match=if_match, if_none_match=if_none_match)
        except MechanicException as e:
            error_response = {
                "message": e.message,
                "resolution": e.resolution
            }
            logger.error(error_response)
            return error_response, e.status_code

        # parse all query params, valid_filters N/A for GET {id}
        params = parse_query_params(request, [], self.requests["get"]["query_params"])
        model_schema = self.responses["get"]["schema"]()
        model_schema.context = {"embed": params.get("embed")}

        # If no item found, return 204 'NO CONTENT'
        if model_instance is None:
            resp_code = 204
            return "", resp_code
        else:
            resp_code = self.responses["get"]["code"]
            return make_response(model_schema.jsonify(model_instance), resp_code, {"ETag": model_instance.etag})

    def put(self, resource_id):
        try:
            request_body = request.get_json(force=True)
            if_match = request.headers.get("If-Match", "").split(",")
            if "" in if_match:
                if_match.remove("")

            if_none_match = request.headers.get("If-None-Match", "").split(",")
            if "" in if_none_match:
                if_none_match.remove("")

            if_modified_since = request.headers.get("If-Modified-Since")
            if_unmodified_since = request.headers.get("If-Unmodified-Since")

            # do any work needed before validation
            service = self.service_class()
            modified_request_body = service.put_before_validation(request_body)

            model_instance = db_helper.read(resource_id, self.responses["get"]["model"])

            if model_instance is None:
                raise MechanicNotFoundException()

            schema = self.responses["put"]["schema"]()

            # update with new attributes
            obj_to_save = modified_request_body

            # deserialize into model object
            updated_model_instance, errors = schema.load(obj_to_save)
            updated_model_instance.identifier = resource_id

            # do any work needed after initial schema validation
            service.put_after_validation(updated_model_instance)

            # save to DB
            updated_db_model = db_helper.replace(resource_id, updated_model_instance,
                                                 if_modified_since=if_modified_since,
                                                 if_unmodified_since=if_unmodified_since, if_match=if_match,
                                                 if_none_match=if_none_match)
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
        return make_response(schema.jsonify(updated_db_model), self.responses["put"]["code"])

    def delete(self, resource_id):
        try:
            db_helper.delete(resource_id, self.responses["delete"]["model"] or self.responses["get"]["model"])
        except MechanicException as e:
            error_response = {
                "message": e.message,
                "resolution": e.resolution
            }
            logger.error(error_response)
            return error_response, e.status_code

        return "", self.responses["delete"]["code"]


class BaseCommandController(Resource):
    """
    This type of controller is used for endpoints that aren't actual resources, but instead are commands. For example,
    if you had an endpoint /api/dogs/{id}/sit - "sit" is not a resource, it's a command you are executing on a 'dog'
    resource.

    Because this endpoint maps to a command instead of an actual resource, it has much different behavior. It assumes
    the model for this type of endpoint is a task object. You can still define your task object in the OpenAPI spec
    files, but will need to update this task object in your service class methods.

    It also assumes a command only uses a POST. mechanic currently does not support command endpoints with anything
    other than a POST method.
    """

    service_class = None
    resource_host_url = None
    resource_uri = None
    responses = {}
    requests = {}

    def post(self, resource_id):
        try:
            request_body = request.get_json(force=True)

            host_url = self.resource_host_url + "/" if not self.resource_host_url.endswith("/") \
                else self.resource_host_url

            resource_url = host_url + self.resource_uri[1:] if self.resource_uri.endswith(
                "/") else host_url + self.resource_uri
            resource_url = resource_url + "/" if not resource_url.endswith("/") else resource_url

            schema = self.requests["post"]["schema"]()
            schema.validate(request_body)
            service = self.service_class()

            # responsible for doing additional validation of the command and creating a task object
            task_model = service.validate_command_and_create_task(request_body, resource_url)

            # retrieve the resource being operated on
            r = requests.get(resource_url + resource_id)

            if r.status_code == 404 or r.status_code == 204:
                raise MechanicNotFoundException()
            elif r.status_code == 400:
                raise MechanicBadRequestException()

            # Other error codes still raise HTTP exception. If it is not an error, this line does nothing
            r.raise_for_status()

            # TODO - verify the retrieved object is consistent with expectations, throw error otherwise
            service.validate_retrieved_resource(r)

            # responsible for marking task as "Running" and executing the command.
            service.initiate_command(task_model, r.json(), resource_url + resource_id, async_exec=self.responses["post"]["async"])

            # responsible for marking task as "Completed" or "Error" and other command-specific completion items.
            # also responsible for calling correct url and updating the appropriate resource
            service.finish_command(task_model)
            new_task = db_helper.create(task_model)
        except ValidationError as e:
            error_response = {
                "message": e.messages,
                "resolution": "Retry the operation with a valid object."
            }
            logger.error(error_response)
            return error_response, 400
        except ConnectionError as e:
            error_response = {
                "message": "Unable to connect to required service at address: " + self.resource_host_url,
                "resolution": "Ensure service is running and retry the operation."
            }
            logger.error(error_response)
            return error_response, 500
        except MechanicException as e:
            error_response = {
                "message": e.message,
                "resolution": e.resolution
            }
            logger.error(error_response)
            return error_response, e.status_code
        return make_response(schema.jsonify(new_task), self.responses["post"]["code"])
