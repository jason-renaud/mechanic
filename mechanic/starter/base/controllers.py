# python native
import logging

# third party libs
from flask import request, make_response, jsonify
from flask_restful import Resource
from marshmallow.exceptions import ValidationError
from sqlalchemy.exc import DatabaseError

# project imports
import app
from app import db
import base.db_helper as db_helper
from base.exceptions import MechanicException, MechanicNotFoundException, MechanicNotSupportedException, \
    MechanicBadRequestException

IF_MATCH = "If-Match"
IF_NONE_MATCH = "If-None-Match"
IF_MODIFIED_SINCE = "If-Modified-Since"
IF_UNMODIFIED_SINCE = "If-Unmodified-Since"
ETAG_HEADER = "ETag"

logger = logging.getLogger(app.config["DEFAULT_LOG_NAME"])


class BaseController(Resource):
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
            db.session.close()
            logger.error(exc.orig)
            error_response["message"] = "The given object is not valid."
            error_response["resolution"] = "Retry the operation with a valid object."
        elif isinstance(exc, MechanicException):
            error_response["message"] = exc.message
            error_response["resolution"] = exc.resolution
            logger.error(error_response)
        return jsonify(error_response)

    def _get_caching_headers(self):
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

    def _get_item_apply_query_params(self):
        pass

    def _retrieve_object(self, resource_id, caching_headers=None, *args, **kwargs):
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
        return self.responses[method_type]["code"]

    def _verify_request(self):
        if not request.is_json:
            raise MechanicNotSupportedException(msg="Only application/json is supported at this time.")

    def _verify_serialized_model(self, serialized_model):
        if not serialized_model:
            raise MechanicNotFoundException(uri=request.path)


class BaseItemController(BaseController):
    def get(self, resource_id):
        """
        """
        try:
            caching_headers = self._get_caching_headers()
            self._get_item_apply_query_params()
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
        """
        Replace existing object. If an attribute is left out of the request body, then don't edit the attribute?
        """
        try:
            caching_headers = self._get_caching_headers()

            self._put_item_verify_request()
            deserialized_request = self._put_item_deserialize_request()
            self._put_item_verify_deserialized_request(deserialized_request)

            existing_model = self._retrieve_object(resource_id, caching_headers=caching_headers)
            updated_model = self._put_item_db_update(deserialized_request, existing_model, caching_headers=caching_headers)
            serialized_model = self._put_item_serialize_model(updated_model)

            resp_code = self._get_success_response_code("put")
            ret = make_response(serialized_model, resp_code, { ETAG_HEADER: updated_model.etag })
        except MechanicException as e:
            logger.error(e.message)

            error_response = self._convert_to_error(e)

            resp_code = e.status_code
            ret = make_response(error_response, resp_code)
        return ret

    def delete(self, resource_id):
        try:
            caching_headers = self._get_caching_headers()
            existing_model = self._retrieve_object(resource_id, caching_headers=caching_headers)

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
        schema = self.responses["get"]["schema"]()
        serialized_model = schema.dump(model)
        return serialized_model.data

    def _put_item_verify_request(self):
        super(BaseItemController, self)._verify_request()

    def _put_item_deserialize_request(self):
        request_body = request.get_json()
        schema = self.responses["put"]["schema"]()

        try:
            # load() will raise an exception if an error occurs because all Marshmallow schemas have the Meta attribute
            # "strict = True"
            model_instance, _ = schema.load(request_body)
        except ValidationError as e:
            raise MechanicBadRequestException(msg=e.messages)
        return model_instance

    def _put_item_verify_deserialized_request(self, deserialized_request):
        pass

    def _put_item_db_update(self, deserialized_request, existing_model, caching_headers=None):
        if not existing_model:
            raise MechanicNotFoundException(uri=request.path)

        if not caching_headers:
            model = db_helper.replace(existing_model, deserialized_request)
        else:
            model = db_helper.replace(existing_model,
                                      deserialized_request,
                                  if_modified_since=caching_headers[IF_MODIFIED_SINCE],
                                  if_unmodified_since=caching_headers[IF_UNMODIFIED_SINCE],
                                  if_match=caching_headers[IF_MATCH],
                                  if_none_match=caching_headers[IF_NONE_MATCH])
        return model

    def _put_item_serialize_model(self, updated_model):
        schema = self.responses["put"]["schema"]()
        serialized_model = schema.dump(updated_model)
        return jsonify(serialized_model.data)

    def _delete_item_db_delete(self, existing_model, caching_headers=None):
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


class BaseCollectionController(BaseController):
    def get(self):
        """
        Get all resources of a certain type.
        """
        try:
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
        """
        Create new object.
        """
        try:
            self._post_collection_verify_request()
            deserialized_request = self._post_collection_deserialize_request()
            self._post_collection_verify_deserialized_request(deserialized_request)
            created_model = self._post_collection_db_create(deserialized_request)
            serialized_model = self._post_collection_serialize_model(created_model)
            resp_code = self._get_success_response_code("post")
            ret = make_response(serialized_model, resp_code, { ETAG_HEADER: created_model.etag })
        except MechanicException as e:
            logger.error(e.message)
            error_response = self._convert_to_error(e)
            resp_code = e.status_code
            ret = make_response(error_response, resp_code)
        return ret

    def _get_collection_retrieve_all_objects(self):
        return self.responses["get"]["model"].query.all()

    def _get_collection_serialize_models(self, models):
        schema = self.responses["get"]["schema"](many=True)
        serialized_models = schema.dump(models)
        return serialized_models.data

    def _post_collection_verify_request(self):
        super(BaseCollectionController, self)._verify_request()

    def _post_collection_deserialize_request(self):
        request_body = request.get_json()

        schema = self.responses["post"]["schema"]()

        try:
            # load() will raise an exception if an error occurs because all Marshmallow schemas have the Meta attribute
            # "strict = True"
            model_instance, _ = schema.load(request_body)
        except ValidationError as e:
            raise MechanicBadRequestException(msg=e.messages)

        return model_instance

    def _post_collection_verify_deserialized_request(self, deserialized_request):
        pass

    def _post_collection_db_create(self, deserialized_request):
        return db_helper.create(deserialized_request)

    def _post_collection_serialize_model(self, model):
        schema = self.responses["post"]["schema"]()
        serialized_model = schema.dump(model)
        return jsonify(serialized_model.data)
