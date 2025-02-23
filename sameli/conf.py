from collections import UserDict
from pathlib import Path
from typing import Any

import yaml


class Conf(UserDict[str, Any]):
    @classmethod
    def from_yaml(cls, filename: str) -> "Conf":
        path = Path(filename)

        if path.exists() and path.is_file():
            with path.open() as file:
                return cls(yaml.safe_load(file))

        raise ValueError(f"Failed to create Conf because {path.absolute()} does not exist or not a file.")

    @property
    def app_name(self) -> str:
        return self.get("app_name", "Sameli")

    @property
    def metrics_port(self) -> int:
        return self.get("metrics_port", 5000)

    @property
    def enable_kafka(self) -> bool:
        return self.get("enable_kafka", False)

    @property
    def model_conf(self) -> dict[str, Any]:
        return self.get("model_conf", {})

    @property
    def kafka_conf(self) -> dict[str, Any]:
        return self.get("kafka_conf", {})

    @property
    def http_conf(self) -> dict[str, Any]:
        return self.get("http_conf", {})
