import transformers
from transformers import AutoModel, AutoTokenizer
from transformers.utils import ModelOutput
import torch

from typing import Any, Optional, Tuple, List
from sameli.models import BaseModel


class TransformerModel(BaseModel):
    def __init__(self, name: str, hparams: dict[str, Any]):
        self.model_name = name
        self.hparams = hparams

        self.model_class = getattr(transformers, self.hparams.get("model_class", "AutoModel"))
        self.model_path = self.hparams.get("model_path", ".")
        self.labels = self.hparams.get("labels", [])

        self.model: Optional[AutoModel] = None
        self.tokenizer: Optional[AutoTokenizer] = None

    @property
    def name(self) -> str:
        return self.model_name

    def load(self) -> Tuple[AutoModel, AutoTokenizer]:
        model = self.model_class.from_pretrained(self.model_path)
        tokenizer = AutoTokenizer.from_pretrained(self.model_path)

        return model, tokenizer

    def save(self, model: Tuple[AutoModel, AutoTokenizer]) -> None:
        self.model, self.tokenizer = model

    def preprocess(self, features: dict[str, Any]) -> torch.Tensor:
        inputs = self.tokenizer(features.get("text", ""), return_tensors="pt")
        return inputs

    def predict(self, inputs: torch.Tensor) -> ModelOutput:
        with torch.no_grad():
            outputs = self.model(**inputs)

        return outputs

    def postprocess(self, outputs: ModelOutput) -> List[float]:
        proba = torch.sigmoid(outputs.logits)
        max_prob_idx = proba.argmax().item()
        return self.labels[max_prob_idx]
