import time

from aiokafka import ConsumerRecord


def waited(msg: ConsumerRecord) -> float:
    ts = msg.timestamp
    return time.time() - ts / 1000


def snippet(msg: str, max_length: int = 10) -> str:
    return msg[:max_length] if max_length > 0 else msg
