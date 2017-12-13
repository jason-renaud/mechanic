import uuid
from datetime import datetime
import logging
import {{ app_name }}

from mechanic.base.exceptions import MechanicResourceAlreadyExistsException, MechanicNotFoundException, \
    MechanicResourceLockedException, MechanicPreconditionFailedException, MechanicException, \
    MechanicInvalidETagException, MechanicNotModifiedException, MechanicBadRequestException
from {{ app_name }} import db
from sqlalchemy.exc import DatabaseError, IntegrityError

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


def close_session():
    db.session.close()


def read(identifier, model_class, if_modified_since=None, if_unmodified_since=None, if_match=[], if_none_match=[]):
    """
    Retrieves an object from the DB.

    :param identifier: primary key of object.
    :param model_class: type of model to query
    :return: retrieved object or None
    """
    model = model_class.query.filter_by(identifier=identifier).one_or_none()
    _validate_modified_headers(if_modified_since, if_unmodified_since, model)

    if if_none_match and not if_match:
        try:
            _validate_match_headers(if_match, if_none_match, model)
        except MechanicInvalidETagException:
            raise MechanicNotModifiedException()
    else:
        _validate_match_headers(if_match, if_none_match, model)

    return model


def create(model):
    """
    Creates new object in DB.

    - If an "identifier" exists on the object, raise a 409 conflict.
    - If no "identifier" exists, simply create new object.

    :param identifier: primary key of object.
    :param model: new object to be created
    :return: newly created object
    """
    logger.debug("Attempting to create new object - type: %s", model.__class__)

    # check to see if model w/ identifier already exists
    if model.identifier:
        model_exists = model.__class__.query.filter_by(identifier=model.identifier).one()

        if model_exists:
            logger.error("Resource already exists - type: %s, identifier: %s", model.__class__.__name__, model.identifier)
            raise MechanicResourceAlreadyExistsException()

    # set created and last_modified
    model.created = datetime.utcnow()
    model.last_modified = model.created
    db.session.add(model)

    try:
        db.session.commit()
    except IntegrityError as e:
        logger.error(str(e))
        raise MechanicBadRequestException(msg="An error occurred while attempting to create the resource. Most likely "
                                              "you are attempting to create an object that violates some uniqueness "
                                              "criteria.",
                                          res="Verify the requested object does not exist and retry the request. If "
                                              "the error persists, contact your support representative for more help.")
    except DatabaseError as e:
        logger.error(str(e))
        raise MechanicException("An unknown error occurred while attempting to create %s " % model.__class__.__name__)
    logger.debug("Successfully created new object - type: %s, identifier: %s", model.__class__.__name__, model.identifier)
    obj = model.__class__.query.filter_by(identifier=model.identifier).one()
    return obj


def update(identifier, model_class, changed_attributes, if_modified_since=None, if_unmodified_since=None,
           if_match=[], if_none_match=[]):
    """
    Updates an object with the dictionary of changed_attributes.
    Retrieves the object w/ the specified identifier:
    - Compare eTag values, if eTag validation fails, raise 412 precondition failed exception.
    - If above validations are successful, update object.
    the object.
    :param identifier: primary key of object.
    :param model_class: model class of the object.
    :param changed_attributes: dictionary of attributes to update.
    :param if_modified_since
    :param if_unmodified_since
    :param if_match
    :param if_none_match
    :return: updated object
    """

    model = model_class.query.filter_by(identifier=identifier).one_or_none()

    if not model:
        raise MechanicNotFoundException()

    # validations
    _validate_modified_headers(if_modified_since, if_unmodified_since, model)
    _validate_match_headers(if_match, if_none_match, model)

    # update model
    for key, value in changed_attributes.items():
        setattr(model, key, value)

    # object has been updated, change last_modified and etag
    model.last_modified = datetime.utcnow()
    model.etag = str(uuid.uuid4())
    try:
        db.session.commit()
    except DatabaseError as e:
        logger.error(str(e))
        raise MechanicException(
            "An unknown error occurred while attempting to update %s %s" % (model.__class__.__name__, identifier))
    return model.__class__.query.filter_by(identifier=model.identifier).one()


def replace(identifier, new_model, if_modified_since=None, if_unmodified_since=None, if_match=[],
            if_none_match=[]):
    """
    Same as an update, except instead of only updating the specified attributes, it replaces the entire object.
    """
    model = new_model.__class__.query.filter_by(identifier=identifier).one_or_none()

    if not model:
        raise MechanicNotFoundException()

    # validations
    _validate_modified_headers(if_modified_since, if_unmodified_since, model)
    _validate_match_headers(if_match, if_none_match, model)

    created = model.created

    for col in new_model.__class__.__mapper__.columns:
        if col.key not in ["identifier", "last_modified", "etag", "created", "controller", "uri"]:
            if getattr(new_model, col.key):
                setattr(model, col.key, getattr(new_model, col.key))

    for rel in new_model.__class__.__mapper__.relationships:
        if rel.key not in ["identifier", "last_modified", "etag", "created", "controller", "uri"]:
            if getattr(new_model, rel.key):
                setattr(model, rel.key, getattr(new_model, rel.key))

    model.identifier = identifier
    model.last_modified = datetime.utcnow()
    model.etag = str(uuid.uuid4())
    model.created = created

    db.session.merge(model)
    try:
        db.session.commit()
    except DatabaseError as e:
        logger.error(str(e))
        raise MechanicException("An unknown error occurred while attempting to update %s %s" % (model.__class__.__name__, identifier))
    return new_model.__class__.query.filter_by(identifier=identifier).one()


def delete(identifier, model_class, force=False, if_modified_since=None, if_unmodified_since=None, if_match=[], if_none_match=[]):
    """
    Deletes object with given identifier.

    Retrieves the object w/ the specified identifier:
    - Compare eTag values, if eTag validation fails, raise 412 precondition failed exception.
    - If 'force' is set to True, delete object regardless of eTag validation.
    - If above validations are successful, delete object.

    :param identifier: primary key of object.
    :param model_class
    :param force: if set to True, delete object regardless of eTag validation.
    :param if_modified_since
    :param if_unmodified_since
    :param if_match
    :param if_none_match
    :
    """
    model = model_class.query.filter_by(identifier=identifier).one_or_none()

    if not model:
        raise MechanicNotFoundException()

    # validations
    if not force:
        _validate_modified_headers(if_modified_since, if_unmodified_since, model)
        _validate_match_headers(if_match, if_none_match, model)

    db.session.delete(model)
    try:
        db.session.commit()
    except IntegrityError as e:
        logger.error(str(e))
        raise MechanicBadRequestException(msg="An error occurred while attempting to delete %s %s. Most likely "
                                              "you are attempting to delete an object that has one or more resources "
                                              "dependent on it." % (model_class.__name__, identifier),
                                          res="Verify the requested object does not have objects that depend on it. If "
                                              "the error persists, contact your support representative for more help.")
    except DatabaseError as e:
        logger.error(str(e))
        raise MechanicException("An unknown error occurred while attempting to delete %s %s" % (model_class.__name__, identifier))


def _validate_modified_headers(if_modified_since, if_unmodified_since, model):
    if if_modified_since and if_unmodified_since:
        logger.error("If-Modified-Since and If-Unmodified-Since are mutually exclusive.")
        raise MechanicPreconditionFailedException(
            msg="If-Modified-Since and If-Unmodified-Since are mutually exclusive.",
            res="Remove one of these headers and retry the operation.")

    if if_modified_since:
        dt = datetime.strptime(if_modified_since, "%a, %d %b %Y %H:%M:%S GMT")

        if dt > model.last_modified:
            logger.info("Resource has not been modified since %s. Type: %s, identifier: %s", str(dt), model.__class__,
                        model.identifier)
            raise MechanicNotModifiedException()

    if if_unmodified_since:
        dt = datetime.strptime(if_unmodified_since, "%a, %d %b %Y %H:%M:%S GMT")

        if dt < model.last_modified:
            logger.error("Resource has been modified since %s. Type: %s, identifier: %s", str(dt), model.__class__,
                         model.identifier)
            raise MechanicPreconditionFailedException()


def _validate_match_headers(if_match, if_none_match, model):
    if len(if_match) > 0 and len(if_none_match) > 0:
        logger.error("If-Match and If-None-Match are mutually exclusive.")
        raise MechanicPreconditionFailedException(msg="If-Match and If-None-Match are mutually exclusive.",
                                                  res="Remove one of these headers and retry the operation.")

    if len(if_match) > 0:
        # if any item in if_match does not match the current etag, raise exception
        if not any(val == "*" or val == model.etag for val in if_match):
            raise MechanicInvalidETagException()
        if not any(val for val in if_match):
            logger.error("If-Match value cannot be empty")
            raise MechanicInvalidETagException()

    if len(if_none_match) > 0:
        # if any item in if_none_match matches the current etag, raise exception
        if any(val != "*" and val == model.etag for val in if_none_match):
            raise MechanicInvalidETagException(msg="The If-None-Match header given matches the resource.")
