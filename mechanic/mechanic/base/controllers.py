# python native
import logging

# third party libs
from flask import request, make_response, jsonify
from flask_restful import Resource
from marshmallow.exceptions import ValidationError
from sqlalchemy.exc import DatabaseError

# project imports
import {{ app_name }}
import mechanic.utils.db_helper as db_helper
from mechanic.base.exceptions import MechanicException, MechanicNotFoundException, MechanicNotSupportedException, \
    MechanicBadRequestException

IF_MATCH = "If-Match"
IF_NONE_MATCH = "If-None-Match"
IF_MODIFIED_SINCE = "If-Modified-Since"
IF_UNMODIFIED_SINCE = "If-Unmodified-Since"
ETAG_HEADER = "ETag"

logger = logging.getLogger(__name__)


class MechanicBaseController(Resource):
    """
    BaseController to define base functionilty/methods for concrete controllers.
    """
    responses = dict()
    requests = dict()

    def get(self, *args, **kwargs):
        return self._not_implemented_response("GET")

    def put(self, *args, **kwargs):
        return self._not_implemented_response("PUT")

    def post(self, *args, **kwargs):
        return self._not_implemented_response("POST")

    def delete(self, *args, **kwargs):
        return self._not_implemented_response("DELETE")

    def patch(self, *args, **kwargs):
        return self._not_implemented_response("PATCH")

    def _not_implemented_response(self, method_type):
        """
        Returns a response for methods that are not implemented.

        :param method_type: the HTTP method type. GET, PUT, POST, etc.
        :return: Flask response with formatted error.
        """
        error = dict()
        error["message"] = "The request method type: %s for path: %s is not supported." % (method_type, request.path)
        error["resolution"] = "Retry using a valid request."
        return make_response(jsonify(error), 400)

    def _convert_to_error(self, exc):
        """
        Converts an exception to a json friendly error response.

        :param exc: Exception that caused the error.
        :return: json representation of the error response.
        """
        error_response = dict()
        if isinstance(exc, ValidationError):
            error_response["message"] = exc.messages
            error_response["resolution"] = "Retry the operation with a valid object."
        elif isinstance(exc, DatabaseError):
            db_helper.close_session()
            logger.error(exc.orig)
            error_response["message"] = "The given object is not valid."
            error_response["resolution"] = "Retry the operation with a valid object."
        elif isinstance(exc, MechanicException):
            error_response["message"] = exc.message
            error_response["resolution"] = exc.resolution
            logger.error(error_response)
        return jsonify(error_response)

    def _get_caching_headers(self):
        """
        Parses caching relevant headers from the request object.

        :return: Dictionary of caching headers.
        """
        headers = dict()

        # Get If-Match header
        headers[IF_MATCH] = request.headers.get(IF_MATCH, "").split(",")
        if "" in headers[IF_MATCH]:
            headers[IF_MATCH].remove("")

        # Get If-None-Match header
        headers[IF_NONE_MATCH] = request.headers.get(IF_NONE_MATCH, "").split(",")
        if "" in headers[IF_NONE_MATCH]:
            headers[IF_NONE_MATCH].remove("")

        headers[IF_MODIFIED_SINCE] = request.headers.get(IF_MODIFIED_SINCE)
        headers[IF_UNMODIFIED_SINCE] = request.headers.get(IF_UNMODIFIED_SINCE)
        return headers

    def _retrieve_object(self, resource_id, caching_headers=None):
        """
        Retrieves an object from the database based on the resource_id and the model defined in the controller response.

        :param resource_id: identifier of the resource in the database.
        :param caching_headers: request headers sent in by the request.
        :return: the retrieved object from the database as a SQLAlchemy model.
        """
        if not caching_headers:
            model = db_helper.read(resource_id, self.responses["get"]["model"])
        else:
            model = db_helper.read(resource_id,
                                  self.responses["get"]["model"],
                                  if_modified_since=caching_headers[IF_MODIFIED_SINCE],
                                  if_unmodified_since=caching_headers[IF_UNMODIFIED_SINCE],
                                  if_match=caching_headers[IF_MATCH],
                                  if_none_match=caching_headers[IF_NONE_MATCH])
        return model

    def _get_success_response_code(self, method_type):
        """
        Gets the controller's success response code for the method type.

        :param method_type: an HTTP method. GET, PUT, POST, DELETE, etc
        :return: the HTTP response code number
        """
        return self.responses[method_type.lower()]["code"]

    def _verify_request(self):
        """
        Verifies the request. This base method only verifies that the request format is in json. This method can be
        overridden and additional verification can be added if needed.
        """
        if not request.is_json:
            raise MechanicNotSupportedException(msg="Only application/json is supported at this time.")

    def _verify_serialized_model(self, serialized_model):
        """
        Verifies the serialized model. This base method only verifies that the model is not None. This method can be
        overridden and additional verification can be added if needed.

        :param serialized_model: The already serialized model (i.e. a dictionary representation of the model.)
        """
        if not serialized_model:
            raise MechanicNotFoundException(uri=request.path)

    def _parse_query_params(self):
        params = dict()

        for param, param_val in request.args.items():
            params[param] = param_val

        self.query_params = params

    def _sanitize_embed_params(self):
        embed = self.query_params.get("embed", "")
        embed = embed.split(",")
        return embed


class MechanicBaseItemController(MechanicBaseController):
    """
    Base class that handles API endpoints that map to a specific resource. I.e., endpoints that end with a resource id.
    Example endpoints that match this could be:
    /api/dogs/{id}
    /v1/airplanes/{id}

    In both cases, the {id} implies that the uri represents a specific dog or a specific airplane resource.
    """
    def get(self, resource_id, **kwargs):
        try:
            caching_headers = self._get_caching_headers()
            self._parse_query_params()
            model = self._retrieve_object(resource_id, caching_headers=caching_headers)
            model_data = self._get_item_serialize_model(model)
            self._verify_serialized_model(model_data)
            resp_code = self._get_success_response_code("get")
            ret = make_response(jsonify(model_data), resp_code, { ETAG_HEADER: model.etag })
        except MechanicException as e:
            logger.error(e.message)
            error_response = self._convert_to_error(e)
            resp_code = e.status_code

            # If object not found, return 204 No Content, not 404 Not Found
            if e.status_code == 404:
                resp_code = 204
            ret = make_response(error_response, resp_code)
        return ret

    def put(self, resource_id):
        try:
            caching_headers = self._get_caching_headers()
            self._parse_query_params()

            self._put_item_verify_request()
            deserialized_request = self._put_item_deserialize_request()
            self._put_item_verify_deserialized_request(deserialized_request)

            existing_model = self._retrieve_object(resource_id)
            updated_model = self._put_item_db_update(deserialized_request, existing_model, caching_headers=caching_headers)
            serialized_model = self._put_item_serialize_model(updated_model)

            resp_code = self._get_success_response_code("put")
            ret = make_response(jsonify(serialized_model), resp_code, { ETAG_HEADER: updated_model.etag })
        except MechanicException as e:
            logger.error(e.message)

            error_response = self._convert_to_error(e)

            resp_code = e.status_code
            ret = make_response(error_response, resp_code)
        return ret

    def delete(self, resource_id):
        try:
            caching_headers = self._get_caching_headers()
            self._parse_query_params()

            existing_model = self._retrieve_object(resource_id)

            self._delete_item_db_delete(existing_model, caching_headers=caching_headers)

            resp_code = self._get_success_response_code("delete")
            ret = make_response("", resp_code)
        except MechanicException as e:
            logger.error(e.message)

            error_response = self._convert_to_error(e)

            resp_code = e.status_code
            ret = make_response(error_response, resp_code)
        return ret

    def _get_item_serialize_model(self, model):
        """
        Serializes the model into a python dictionary.

        :param model: SQLAlchemy model to serialize.
        :return: Dictionary represenation of the model.
        """
        embed = self._sanitize_embed_params()
        schema = self.responses["get"]["schema"](context={"embed": embed})
        serialized_model = schema.dump(model)
        return serialized_model.data

    def _put_item_verify_request(self):
        super(MechanicBaseItemController, self)._verify_request()

    def _put_item_deserialize_request(self):
        """
        Deserializes the json request body into a SQLAlchemy model instance.

        :return: SQLAlchemy model created from the request body.
        """
        request_body = request.get_json()
        schema = self.requests.get("put", {}).get("schema") or self.responses.get("put", {}).get("schema")
        embed = self._sanitize_embed_params()
        schema = schema(context={"embed": embed})

        try:
            # load() will raise an exception if an error occurs because all Marshmallow schemas have the Meta attribute
            # "strict = True". Therefore, no need to check the 'errors' value, so we use a '_' instead.
            model_instance, _ = schema.load(request_body)
        except ValidationError as e:
            # If the request body did not succeed through Marshmallow validation
            raise MechanicBadRequestException(msg=e.messages)
        return model_instance

    def _put_item_verify_deserialized_request(self, deserialized_request):
        """
        No-op by default, but can be overridden to add some verification.

        :param deserialized_request: SQLAlchemy model deserialized from a json request body.
        """
        pass

    def _put_item_db_update(self, deserialized_request, existing_model, caching_headers=None):
        """
        Replace existing object. The object passed in should be the exact object that is saved. This means that is an
        attribute is not present, then the attribute will not exist in the new object. For example:

        Original object:
        {
            "dog": "fido",
            "cat": "sparky"
        }

        Put request body:
        {
            "dog": "spot"
        }

        The new object will be:
        {
            "dog": "spot"
            "cat": null
        }

        **NOT**
        {
            "dog": "spot",
            "cat": "sparky"
        }

        :param deserialized_request: the new SQLAlchemy model to replace the old one.
        :param existing_model: SQLAlchemy model already in the database.
        :param caching_headers: Dictionary of caching headers (If-Match, If-Modified-Since, etc.)
        :return: Updated SQLAlchemy model that is in the database.
        """
        if not existing_model:
            raise MechanicNotFoundException(uri=request.path)

        if not caching_headers:
            model = db_helper.replace(existing_model.identifier, deserialized_request)
            # model = db_helper.update(existing_model.identifier, deserialized_request)
        else:
            model = db_helper.replace(existing_model.identifier,
                                      deserialized_request,
                                      if_modified_since=caching_headers[IF_MODIFIED_SINCE],
                                      if_unmodified_since=caching_headers[IF_UNMODIFIED_SINCE],
                                      if_match=caching_headers[IF_MATCH],
                                      if_none_match=caching_headers[IF_NONE_MATCH])
            # model = db_helper.update(existing_model.identifier,
            #                          deserialized_request,
            #                          if_modified_since=caching_headers[IF_MODIFIED_SINCE],
            #                          if_unmodified_since=caching_headers[IF_UNMODIFIED_SINCE],
            #                          if_match=caching_headers[IF_MATCH],
            #                          if_none_match=caching_headers[IF_NONE_MATCH])
        return model

    def _put_item_serialize_model(self, updated_model):
        """
        Serializes a SQLAlchemy model into a python dictionary.

        :param updated_model: SQLAlchemy model that was just recently updated.
        :return: Python dictionary representation of the model.
        """
        embed = self._sanitize_embed_params()
        schema = self.responses["put"]["schema"](context={"embed": embed})
        serialized_model = schema.dump(updated_model)
        return serialized_model.data

    def _delete_item_db_delete(self, existing_model, caching_headers=None):
        """
        Deletes the model in the database.

        :param existing_model: model in the database to delete.
        :param caching_headers: Dictionary of caching headers (If-Match, If-Modified-Since, etc.)
        """
        if not existing_model:
            raise MechanicNotFoundException(uri=request.path)

        if not caching_headers:
            db_helper.delete(existing_model.identifier)
        else:
            db_helper.delete(existing_model.identifier,
                                     existing_model.__class__,
                                     if_modified_since=caching_headers[IF_MODIFIED_SINCE],
                                     if_unmodified_since=caching_headers[IF_UNMODIFIED_SINCE],
                                     if_match=caching_headers[IF_MATCH],
                                     if_none_match=caching_headers[IF_NONE_MATCH])


class MechanicBaseCollectionController(MechanicBaseController):
    """
    Base class that handles API endpoints that map to a collection of resources.
    Example endpoints that match this could be:
    /api/dogs
    /v1/airplanes

    In both cases, the lack of {id} implies that the uri represents a collection of dogs or a collection of airplane
    resources.
    """
    def get(self):
        try:
            self._parse_query_params()
            models = self._get_collection_retrieve_all_objects()
            serialized_models = self._get_collection_serialize_models(models)
            resp_code = self._get_success_response_code("get")
            ret = make_response(jsonify(serialized_models), resp_code)
        except MechanicException as e:
            logger.error(e.message)
            error_response = self._convert_to_error(e)
            resp_code = e.status_code
            ret = make_response(error_response, resp_code)
        return ret

    def post(self):
        try:
            self._parse_query_params()
            self._post_collection_verify_request()
            deserialized_request = self._post_collection_deserialize_request()
            self._post_collection_verify_deserialized_request(deserialized_request)
            created_model = self._post_collection_db_create(deserialized_request)
            serialized_model = self._post_collection_serialize_model(created_model)
            resp_code = self._get_success_response_code("post")
            ret = make_response(jsonify(serialized_model), resp_code, { ETAG_HEADER: created_model.etag })
        except MechanicException as e:
            logger.error(e.message)
            error_response = self._convert_to_error(e)
            resp_code = e.status_code
            ret = make_response(error_response, resp_code)
        return ret

    def _get_collection_retrieve_all_objects(self):
        """
        Retrieve all objects of the model defined in the controller's responses.get attribute.

        :return: A list of SQLAlchemy macros.
        """
        return self.responses["get"]["model"].query.all()

    def _get_collection_serialize_models(self, models):
        """
        Serialize a collection of SQLAlchemy macros into a python list of dictionaries.

        :param models: List of SQLAlchemy macros.
        :return: List of python dictionaries.
        """
        embed = self._sanitize_embed_params()
        schema = self.responses["get"]["schema"](many=True, context={"embed": embed})
        serialized_models = schema.dump(models)
        return serialized_models.data

    def _post_collection_verify_request(self):
        super(MechanicBaseCollectionController, self)._verify_request()

    def _post_collection_deserialize_request(self):
        """
        Deserializes the json request body into a SQLAlchemy model instance.

        :return: SQLAlchemy model created from the request body.
        """
        request_body = request.get_json()

        schema = self.requests.get("post", {}).get("schema") or self.responses.get("post", {}).get("schema")
        embed = self._sanitize_embed_params()
        schema = schema(context={"embed": embed})

        try:
            # load() will raise an exception if an error occurs because all Marshmallow schemas have the Meta attribute
            # "strict = True"
            model_instance, _ = schema.load(request_body)
        except ValidationError as e:
            raise MechanicBadRequestException(msg=e.messages)

        return model_instance

    def _post_collection_verify_deserialized_request(self, deserialized_request):
        """
        No-op by default, but can be overridden to add some verification.

        :param deserialized_request: SQLAlchemy model deserialized from a json request body.
        """
        pass

    def _post_collection_db_create(self, deserialized_request):
        """
        Creates a record in the database for the deserialized request.

        :param deserialized_request: SQLAlchemy model deserialized from json request body.
        :return:
        """
        return db_helper.create(deserialized_request)

    def _post_collection_serialize_model(self, model):
        """
        Serializes a SQLAlchemy model into a python dictionary.

        :param updated_model: SQLAlchemy model that was just recently created.
        :return: Python dictionary representation of the model.
        """
        schema = self.responses["post"]["schema"]()
        serialized_model = schema.dump(model)
        return serialized_model.data
