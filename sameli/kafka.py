import asyncio
import json
import threading
from json import JSONDecodeError
from typing import Any, Optional

import aiokafka.errors
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from loguru import logger
from pydantic import BaseModel as PydanticBase, ValidationError

from sameli.metrics import Metrics
from sameli.models import BaseModel


class Message(PydanticBase):
    action: str
    model_name: str
    data: Any


class KafkaClient(threading.Thread):
    def __init__(self,
                 model: BaseModel,
                 consume_topic: str, produce_topic: str,
                 consumer_conf: dict[str, Any], producer_conf: dict[str, Any],
                 wait_timeout: float = 1.0
                 ):
        super().__init__()

        self.model = model
        self.loop = asyncio.new_event_loop()
        self._interrupt_event = asyncio.Event()

        self.consume_topic = consume_topic
        self.produce_topic = produce_topic
        self.wait_timeout = wait_timeout

        self.consumer_conf = consumer_conf
        self.producer_conf = producer_conf

        self.consumer: Optional[AIOKafkaConsumer] = None
        self.producer: Optional[AIOKafkaProducer] = None

    async def prepare(self):
        self.consumer = AIOKafkaConsumer(self.consume_topic, **self.consumer_conf)
        self.producer = AIOKafkaProducer(**self.producer_conf)

        try:
            await self.consumer.start()
            await self.producer.start()
            logger.info("Started Kafka client")
        except aiokafka.errors.KafkaConnectionError as e:
            Metrics.kafka_error_total.labels(stage="prepare", error="connection_error").inc()
            logger.error(e)
            self.stop()

    def is_skip(self, msg: Message) -> bool:
        if msg.model_name != self.model.name:
            Metrics.kafka_msgs_total.labels(action=msg.action, outcome="skip_by_model_name").inc()
            return True
        elif msg.action not in self.model.actions:
            Metrics.kafka_msgs_total.labels(action=msg.action, outcome="skip_by_action").inc()
            return True

        return False

    async def get_message(self) -> Optional[Message]:
        try:
            msg = await asyncio.wait_for(fut=self.consumer.__anext__(), timeout=self.wait_timeout)
            msg = json.loads(msg.value.decode("utf-8"))
            msg = Message(**msg)

            return msg

        except asyncio.TimeoutError:
            pass
        except JSONDecodeError as e:
            Metrics.kafka_error_total.labels(stage="parse", error="bad_json").inc()
            logger.error(f"Error parsing Kafka message: {e}")
        except ValidationError as e:
            Metrics.kafka_error_total.labels(stage="parse", error="bad_format").inc()
            logger.error(f"Error parsing Kafka message: {e}")
        except Exception as e:
            Metrics.kafka_error_total.labels(stage="parse", error="unknown").inc()
            logger.error(f"Error parsing Kafka message: {e}")

        return None

    def run_action(self, msg: Message) -> Any:
        try:
            result = getattr(self.model, msg.action)(msg.data)

            return result
        except Exception as e:
            Metrics.kafka_error_total.labels(stage="action", error="unknown").inc()
            logger.error(f"Unkown error running action: {e}")

    async def process_messages(self):
        while not self._interrupt_event.is_set():
            msg = await self.get_message()
            if msg is None:
                continue

            with Metrics.kafka_msgs_summary.labels(action=msg.action).time():
                if self.is_skip(msg):
                    continue

                result = self.run_action(msg)

                if result is None:
                    Metrics.kafka_msgs_total.labels(action=msg.action, outcome="empty_result").inc()
                    continue

                try:
                    value = result.encode("utf-8")
                except AttributeError as e:
                    Metrics.kafka_error_total.labels(stage="produce", error="encode").inc()
                    value = str(result).encode("utf-8")

                await self.producer.send_and_wait(topic=self.produce_topic, value=value)

            Metrics.kafka_msgs_total.labels(action=msg.action, outcome="process").inc()

    async def shutdown(self):
        self._interrupt_event.set()
        await self.consumer.stop()
        await self.producer.stop()
        logger.info("Stopped Kafka client")

    def run(self):
        self.loop.run_until_complete(future=self.prepare())
        self.loop.run_until_complete(future=self.process_messages())
        self.loop.run_until_complete(future=self.shutdown())
        self.loop.close()

    def stop(self):
        self.loop.call_soon_threadsafe(callback=self._interrupt_event.set)
