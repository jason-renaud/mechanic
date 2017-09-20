from werkzeug.exceptions import HTTPException


class MechanicException(HTTPException):
    message = None
    resolution = "Contact your support representative for more details."
    status_code = 500

    def __init__(self, message):
        self.message = message
        super(MechanicException, self).__init__(message)


class MechanicNotSupportedException(MechanicException):
    message = "The requested operation is not supported."
    resolution = "Retry with a supported operation."
    status_code = 404

    def __init__(self, msg=message, res=resolution):
        self.message = msg
        self.resolution = res
        super(MechanicNotSupportedException, self).__init__(self.message)


class MechanicNotFoundException(MechanicException):
    message = "The requested resource was not found."
    resolution = "Retry the operation with a resource that exists."
    status_code = 404

    def __init__(self, uri=None):
        if uri:
            self.message = "The requested resource was not found: " + uri
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
    status_code = 400
    message = "The given request is invalid."
    resolution = "Retry the operation with valid request."

    def __init__(self, msg=message, res=resolution):
        super(MechanicBadRequestException, self).__init__(self.message)
        self.message = msg
        self.resolution = res


class MechanicResourceLockedException(MechanicException):
    status_code = 423
    message = "The resource is locked."
    resolution = "Wait until all operations are finished on the resource and try again."

    def __init__(self, msg=message, res=resolution):
        super(MechanicResourceLockedException, self).__init__(self.message)
        self.message = msg
        self.resolution = res


class MechanicPreconditionFailedException(MechanicException):
    status_code = 412
    message = "A precondition failed and it is unsafe to perform the operation."
    resolution = "Retry the operation with the most up-to-date resource."

    def __init__(self, msg=message, res=resolution):
        super(MechanicPreconditionFailedException, self).__init__(self.message)
        self.message = msg
        self.resolution = res


class MechanicInvalidETagException(MechanicPreconditionFailedException):
    message = "The given ETag does not match the resource's ETag."

    def __init__(self, msg=message):
        super(MechanicInvalidETagException, self).__init__(self.message)
        self.message = msg


class MechanicNotModifiedException(MechanicException):
    status_code = 304
    message = "The resource has not been modified since the specified time."
    resolution = "Use existing version of resource."

    def __init__(self, msg=message, res=resolution):
        super(MechanicNotModifiedException, self).__init__(self.message)
        self.message = msg
        self.resolution = res