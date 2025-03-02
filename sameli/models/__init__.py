from sameli.models.base import BaseModel
from sameli.models.dummy import DummyModel
from sameli.models.pytorch import PyTorchModel

models_list = [
    "BaseModel",
    "DummyModel",
    "PyTorchModel"
]

__all__ = models_list + ["models_list"]
