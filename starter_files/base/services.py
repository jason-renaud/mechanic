import logging
import app


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

    # handles the query parameters and returns a modified response
    def handle_query_parameters(self, request, current_response, supported_queries):
        self.logger.info("Handling query parameters...")
        query_key_vals = []

        for param in supported_queries:
            param_val = request.args.get(param)

            if param_val is not None:
                query_key_vals.append((param, param_val))

        # TODO - handle 'limit'
        # TODO - handle 'filter'
        # TODO - handle 'sort'
        # TODO - handle 'embed'

        return current_response
