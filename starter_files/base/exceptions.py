from werkzeug.exceptions import HTTPException


class TugboatException(HTTPException):
    message = None
    resolution = "Contact your support representative for more details."
    status_code = 500

    def __init__(self, message):
        self.message = message
        super(TugboatException, self).__init__(message)


class TugboatNotFoundException(TugboatException):
    message = "The requested resource was not found."
    resolution = "Retry the operation with a resource that exists."
    status_code = 404

    def __init__(self):
        super(TugboatNotFoundException, self).__init__(self.message)


class TugboatResourceAlreadyExistsException(TugboatException):
    message = "The resource already exists."
    resolution = "Retry the operation with a resource that does not exist."
    status_code = 409

    def __init__(self, msg=message, res=resolution):
        super(TugboatResourceAlreadyExistsException, self).__init__(self.message)
        self.message = msg
        self.resolution = res
