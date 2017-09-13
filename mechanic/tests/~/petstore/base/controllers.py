import flask_restful import Resource


class BaseController(Resource):
    def get(self):
        raise NotImplementedError()

    def put(self):
        raise NotImplementedError()

    def post(self):
        raise NotImplementedError()

    def delete(self):
        raise NotImplementedError()

    def patch(self):
        raise NotImplementedError()

    def handle_error(self, exc=None, db=None, response_code=500):
        return 1


class BaseItemController(BaseController):
    def get(self):
        """
        """
        # _get_item_get_caching_headers()
        # _get_item_apply_custom_query_params()
        # _get_item_retrieve_object()
        return self.__class__.__name__

    def put(self):
        """
        Replace existing object. If an attribute is left out of the request body, then don't edit the attribute?
        """
        # _put_item_get_caching_headers()
        # _put_item_apply_custom_query_params()
        # _put_item_retrieve_object()
        # _put_item_deserialize_request()
        # _put_item_db_update()
        # return response
        return self.__class__.__name__

    def delete(self):
        # _delete_item_get_caching_headers()
        # _delete_item_retrieve_object()
        # _delete_item_db_delete()
        # return response
        return self.__class__.__name__


class BaseCollectionController(BaseController):
    def get(self):
        """
        Get all resources of a certain type.
        """
        # _get_collection_retrieve_all_objects()
        # _get_collection_apply_filters()
        # _get_collection_apply_sort()
        # _get_collection_apply_limit()
        # _get_collection_apply_embed()
        # _get_collection_apply_custom_query_params()
        return self.__class__.__name__

    def post(self):
        """
        Create new object.
        """
        # _post_collection_verify_object()
        # _post_collection_deserialize_request()
        # _post_collection_apply_custom_query_params()
        # _post_collection_db_create()
        # return response
        return self.__class__.__name__
