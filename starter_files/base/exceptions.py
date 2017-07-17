from werkzeug.exceptions import HTTPException


class MechanicException(HTTPException):
    message = None
    resolution = "Contact your support representative for more details."
    status_code = 500

    def __init__(self, message):
        self.message = message
        super(MechanicException, self).__init__(message)


class MechanicNotFoundException(MechanicException):
    message = "The requested resource was not found."
    resolution = "Retry the operation with a resource that exists."
    status_code = 404

    def __init__(self):
        super(MechanicNotFoundException, self).__init__(self.message)


class MechanicResourceAlreadyExistsException(MechanicException):
    message = "The resource already exists."
    resolution = "Retry the operation with a resource that does not exist."
    status_code = 409

    def __init__(self, msg=message, res=resolution):
        super(MechanicResourceAlreadyExistsException, self).__init__(self.message)
        self.message = msg
        self.resolution = res


class MechanicBadRequestException(MechanicException):
    message = "The given request is invalid."
    resolution = "Retry the operation with valid request."

    def __init__(self, msg=message, res=resolution):
        super(MechanicBadRequestException, self).__init__(self.message)
        self.message = msg
        self.resolution = res
