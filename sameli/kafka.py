import asyncio
import json
import threading
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from loguru import logger

from sameli.models import BaseModel


class KafkaClient(threading.Thread):
    def __init__(self,
                 model: BaseModel,
                 consume_topic: str, produce_topic: str,
                 consumer_conf: dict[str, Any], producer_conf: dict[str, Any]
                 ):
        super().__init__()

        self.model = model

        self.consume_topic = consume_topic
        self.produce_topic = produce_topic

        self.consumer_conf = consumer_conf
        self.producer_conf = producer_conf

        self.loop = asyncio.new_event_loop()
        self._interrupt_event = asyncio.Event()

    async def prepare(self):
        self.consumer = AIOKafkaConsumer(self.consume_topic, **self.consumer_conf)
        self.producer = AIOKafkaProducer(**self.producer_conf)

        await self.consumer.start()
        await self.producer.start()
        logger.info("Started Kafka client")

    async def process_message(self, message: dict[str, Any]) -> str:
        try:
            action, data = message['action'], message['data']

            result = getattr(self.model, action)(data)

            return json.dumps(result)
        except Exception as e:
            logger.error(f"Unexpected error parsing message '{message}': {e}")
            return None

    async def process_messages(self):
        while not self._interrupt_event.is_set():
            try:
                msg = await asyncio.wait_for(self.consumer.__anext__(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            try:
                consumed_message = json.loads(msg.value.decode('utf-8'))
                if consumed_message.get('model_name') != self.model.name:
                    continue

                logger.debug(f"Processing message: {consumed_message}")

                processed_message = await self.process_message(consumed_message)

                if processed_message is not None:
                    await self.producer.send_and_wait(self.produce_topic, processed_message.encode('utf-8'))
            except Exception as e:
                logger.error(f"Unexpected error while processing message: {e}")

    async def shutdown(self):
        self._interrupt_event.set()
        await self.consumer.stop()
        await self.producer.stop()
        logger.info("Stopped Kafka client")

    def run(self):
        self.loop.run_until_complete(self.prepare())
        self.loop.run_until_complete(self.process_messages())
        self.loop.run_until_complete(self.shutdown())
        self.loop.close()

    def stop(self):
        self.loop.call_soon_threadsafe(self._interrupt_event.set)
