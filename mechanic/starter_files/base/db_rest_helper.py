import uuid
from datetime import datetime
import logging
import app

from base.exceptions import MechanicResourceAlreadyExistsException, MechanicNotFoundException, \
    MechanicResourceLockedException, MechanicPreconditionFailedException, MechanicException, \
    MechanicInvalidETagException, MechanicNotModifiedException
from base.messaging import Producer
from app import db

logger = logging.getLogger(app.config["DEFAULT_LOG_NAME"])
producer = Producer(app.app_name)


def read(identifier, model_class, if_modified_since=None, if_unmodified_since=None, if_match=[], if_none_match=[]):
    """
    Retrieves an object from the DB.

    :param identifier: primary key of object.
    :param model_class: type of model to query
    :return: retrieved object or None
    """
    model = model_class.query.get(identifier)
    _validate_modified_headers(if_modified_since, if_unmodified_since, model)
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
        model_exists = model.__class__.query.get(model.identifier)

        if model_exists:
            logger.error("Resource already exists - type: %s, identifier: %s", model.__class__, model.identifier)
            raise MechanicResourceAlreadyExistsException()

    # set created and last_modified
    model.created = datetime.utcnow()
    model.last_modified = model.created
    db.session.add(model)
    db.session.commit()
    logger.debug("Successfully created new object - type: %s, identifier: %s", model.__class__, model.identifier)
    new_model = model.__class__.query.get(model.identifier)
    msg_obj = {
        "identifier": new_model.identifier,
        "etag": new_model.etag,
        "type": "create"
    }
    routing_key = app.app_name + "." + new_model.__table_args__["schema"] + "." + new_model.__tablename__ + ".create"
    producer.send(routing_key, msg_obj, websocket_send=routing_key)
    return new_model


def update(identifier, model_class, changed_attributes, lock=False, if_modified_since=None, if_unmodified_since=None,
           if_match=[], if_none_match=[]):
    """
    Updates an object with the dictionary of changed_attributes.

    Retrieves the object w/ the specified identifier:
    - Compare eTag values, if eTag validation fails, raise 412 precondition failed exception.
    - If 'locked' is set to True, raise 423 locked exception.
    - If above validations are successful, update object. If lock=True, set 'locked' to True in addition to updating
    the object.

    :param identifier: primary key of object.
    :param model_class: model class of the object.
    :param changed_attributes: dictionary of attributes to update.
    :param lock: boolean to determine if 'locked' attribute should be set or not.
    :param if_modified_since
    :param if_unmodified_since
    :param if_match
    :param if_none_match
    :return: updated object
    """

    model = model_class.query.get(identifier)

    if not model:
        raise MechanicNotFoundException()

    # validations
    _validate_resource_not_locked(model)
    _validate_modified_headers(if_modified_since, if_unmodified_since, model)
    _validate_match_headers(if_match, if_none_match, model)

    if lock:
        # mark resource as 'locked'
        model.locked = True

    # update model
    for key, value in changed_attributes.items():
        setattr(model, key, value)

    # object has been updated, change last_modified and etag
    model.last_modified = datetime.utcnow()
    model.etag = str(uuid.uuid4())
    db.session.commit()
    updated_model = model_class.query.get(identifier)

    msg_obj = {
        "identifier": updated_model.identifier,
        "etag": updated_model.etag,
        "type": "update"
    }
    routing_key = app.app_name + "." + updated_model.__table_args__["schema"] + "." + updated_model.__tablename__ + ".update"
    producer.send(routing_key, msg_obj)
    return updated_model


def replace(identifier, new_model, lock=False, if_modified_since=None, if_unmodified_since=None, if_match=[],
            if_none_match=[]):
    """
    Same as an update, except instead of only updating the specified attributes, it replaces the entire object.
    """
    model = new_model.__class__.query.get(identifier)

    if not model:
        raise MechanicNotFoundException()

    # validations
    _validate_resource_not_locked(model)
    _validate_modified_headers(if_modified_since, if_unmodified_since, model)
    _validate_match_headers(if_match, if_none_match, model)

    prev_created = model.created

    # first delete object
    delete(identifier, new_model.__class__, if_modified_since=if_modified_since, if_unmodified_since=if_unmodified_since, if_match=if_match, if_none_match=if_none_match)

    if lock:
        # mark resource as 'locked'
        new_model.locked = True

    new_model.identifier = identifier
    new_model.created = prev_created

    # object has been updated, change last_modified and etag
    new_model.last_modified = datetime.utcnow()
    new_model.etag = str(uuid.uuid4())
    db.session.delete(model)
    db.session.merge(new_model)
    db.session.commit()
    replaced_model = new_model.__class__.query.get(identifier)

    msg_obj = {
        "identifier": replaced_model.identifier,
        "etag": replaced_model.etag,
        "type": "replace"
    }
    routing_key = app.app_name + "." + replaced_model.__table_args__["schema"] + "." + replaced_model.__tablename__ + ".replaced"
    producer.send(routing_key, msg_obj)
    return replaced_model


def delete(identifier, model_class, force=False, if_modified_since=None, if_unmodified_since=None, if_match=[], if_none_match=[]):
    """
    Deletes object with given identifier.

    Retrieves the object w/ the specified identifier:
    - Compare eTag values, if eTag validation fails, raise 412 precondition failed exception.
    - If 'force' is set to True, delete object regardless of eTag validation and 'locked' attribute.
    - If above validations are successful, delete object.

    :param identifier: primary key of object.
    :param model_class
    :param force: if set to True, delete object regardless of 'locked' attribute.
    :param if_modified_since
    :param if_unmodified_since
    :param if_match
    :param if_none_match
    :
    """
    model = model_class.query.get(identifier)

    if not model:
        raise MechanicNotFoundException()

    # validations
    _validate_resource_not_locked(model)
    _validate_modified_headers(if_modified_since, if_unmodified_since, model)
    _validate_match_headers(if_match, if_none_match, model)

    db.session.delete(model)
    db.session.commit()

    msg_obj = {
        "identifier": identifier,
        "etag": None,
        "type": "delete"
    }
    routing_key = app.app_name + "." + model.__table_args__["schema"] + "." + model.__tablename__ + ".delete"
    producer.send(routing_key, msg_obj)


def _validate_resource_not_locked(model):
    if model.locked:
        logger.error("Resource is locked, cannot update - type: %s, identifier: %s", model.__class__, model.identifier)
        raise MechanicResourceLockedException()


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

    if len(if_none_match) > 0:
        # if any item in if_none_match matches the current etag, raise exception
        if any(val != "*" and val == model.etag for val in if_none_match):
            raise MechanicInvalidETagException(msg="The If-None-Match header given matches the resource.")
