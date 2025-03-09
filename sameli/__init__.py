import importlib.metadata

import sameli.models
import sameli.routers
from sameli.conf import Conf
from sameli.kafka import KafkaClient
from sameli.metrics import Metrics
from sameli.server import Server

__version__ = importlib.metadata.version or (__package__ or __name__)

__all__ = ["Server", "Conf", "KafkaClient", "Metrics", "models", "routers"]
