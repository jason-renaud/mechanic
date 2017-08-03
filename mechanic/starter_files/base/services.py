import logging
import app

DEFAULT_COLLECTION_LIMIT = 100


class BaseService:
    logger = logging.getLogger(app.config['DEFAULT_LOG_NAME'])

    def put_before_validation(self, request_body):
        self.logger.info("PUT before validation for %s service", self.__class__.__name__)
        return request_body

    def put_after_validation(self, model):
        self.logger.info("PUT after validation for %s service", self.__class__.__name__)

    def post_before_validation(self, request_body):
        self.logger.info("POST before validation for %s service", self.__class__.__name__)
        return request_body

    def post_after_validation(self, model):
        self.logger.info("POST after validation for %s service", self.__class__.__name__)

    """
    params - a dictionary of custom query parameters
    models - list of models after sort, filter, and limit queries have been executed
    """
    def handle_custom_query_params(self, params, models):
        return models


class BaseCommandService:
    def validate_command_and_create_task(self, command_parameters, resource_url):
        pass

    def validate_retrieved_resource(self, json_data):
        pass

    def initiate_command(self, task, get_response, resource_url, async_exec=False):
        pass

    def finish_command(self, task):
        pass

