from abc import ABC, abstractmethod
from typing import Any


class BaseModel(ABC):
    actions: list[str] = ['preprocess', 'predict', 'postprocess', 'pipeline']

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError("Model should have name property.")

    @abstractmethod
    def load(self) -> Any:
        raise NotImplementedError("Model should have load method.")

    @abstractmethod
    def save(self, state: Any):
        raise NotImplementedError("Model should have save method.")

    @abstractmethod
    def preprocess(self, features: dict[str, Any]) -> Any:
        raise NotImplementedError("Model should have preprocess method.")

    @abstractmethod
    def predict(self, features: dict[str, Any]) -> Any:
        raise NotImplementedError("Model should have predict method.")

    @abstractmethod
    def postprocess(self, predictions: Any) -> Any:
        raise NotImplementedError("Model should have postprocess method.")

    def pipeline(self, features: dict[str, Any]) -> Any:
        return self.postprocess(self.predict(self.preprocess(features)))
