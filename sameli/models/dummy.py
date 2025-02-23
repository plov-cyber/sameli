from typing import Any

from sameli.models import BaseModel


class DummyModel(BaseModel):
    def __init__(self, name, **kwargs):
        self.model_name = name

    def name(self) -> str:
        return self.model_name

    def load(self):
        pass

    def save(self, state: Any):
        pass

    def preprocess(self, features: dict[str, Any]) -> dict[str, Any]:
        return features

    def predict(self, features: dict[str, Any]) -> int:
        return 0

    def postprocess(self, predictions: int) -> int:
        return predictions
