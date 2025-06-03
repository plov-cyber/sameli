import time
from typing import Any

import torch
from aiokafka import ConsumerRecord


def waited(msg: ConsumerRecord) -> float:
    ts = msg.timestamp
    return time.time() - ts / 1000


def snippet(msg: str, max_length: int = 10) -> str:
    return msg[:max_length] if max_length > 0 else msg


def make_serializable(result: Any):
    if isinstance(result, torch.Tensor):
        return result.cpu().numpy().tolist()
