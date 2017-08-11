from importlib import util

from base.messaging.rabbitmq import Producer
from base.messaging.rabbitmq import Listener

listeners = util.find_spec("services.messaging.listeners")
if listeners:
    from services.messaging.listeners import *

# this is here so Listener can detect it's subclasses
