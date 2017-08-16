from importlib import util

from base.messaging.rabbitmq import Producer
from base.messaging.rabbitmq import Listener

# this is here so Listener can detect it's subclasses
messaging = util.find_spec("services.messaging")
if messaging:
    listeners = util.find_spec("services.messaging.listeners")
    from services.messaging.listeners import *
