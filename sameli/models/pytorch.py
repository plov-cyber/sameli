from typing import Any, Optional

import torch

from sameli.models import BaseModel


class PyTorchModel(BaseModel):
    def __init__(self, name: str, artefacts: dict[str, Any], hparams: dict[str, Any]):
        self.model_name = name
        self.artefacts = artefacts
        self.hparams = hparams

        self.model: Optional[torch.ScriptModule] = None

    @property
    def name(self) -> str:
        return self.model_name

    @property
    def feature_names(self) -> list[str]:
        return self.hparams.get("feature_names", [])

    def load(self) -> torch.ScriptModule:
        model = torch.jit.load(self.artefacts["model"], map_location=self.hparams.get("device", "cpu"))
        model = model.eval()

        return model

    def save(self, model: torch.ScriptModule) -> None:
        self.model: torch.ScriptModule = model

    def preprocess(self, features: dict[str, Any]) -> torch.Tensor:
        features_list = [features[key] for key in features]
        return torch.Tensor(features_list)

    def predict(self, features: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            outputs = self.model(features)

        return outputs

    def postprocess(self, predictions: torch.Tensor) -> float:
        return predictions.item()
