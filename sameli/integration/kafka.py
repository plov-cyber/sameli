import asyncio
import json
import uuid
from typing import Any, Dict, Optional

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from loguru import logger

from sameli.kafka import Message


class SameliKafkaClient:
    def __init__(
        self,
        bootstrap_servers: str,
        consume_topic: str,
        produce_topic: str,
        group_id: str = "sameli-consumer-group",
        auto_offset_reset: str = "earliest"
    ):
        self.bootstrap_servers = bootstrap_servers
        self.consume_topic = consume_topic
        self.produce_topic = produce_topic

        self.consumer_config = {
            "bootstrap_servers": bootstrap_servers,
            "group_id":          group_id,
            "auto_offset_reset": auto_offset_reset
        }

        self.producer_config = {
            "bootstrap_servers": bootstrap_servers
        }

        self.producer: Optional[AIOKafkaProducer] = None
        self.consumer: Optional[AIOKafkaConsumer] = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def connect(self):
        """Initialize producer and consumer connections"""
        self.producer = AIOKafkaProducer(**self.producer_config)
        self.consumer = AIOKafkaConsumer(
            self.consume_topic,
            **self.consumer_config
        )
        await self.producer.start()
        await self.consumer.start()
        logger.info("Kafka client connected")

    async def disconnect(self):
        """Cleanly close connections"""
        if self.producer:
            await self.producer.stop()
        if self.consumer:
            await self.consumer.stop()
        logger.info("Kafka client disconnected")

    @staticmethod
    def generate_task_id() -> str:
        """Generate a unique task ID"""
        return str(uuid.uuid4())

    async def send_message(
        self,
        action: str,
        model_name: str,
        data: Any,
        task_id: Optional[str] = None,
        produce_topic: Optional[str] = None
    ) -> str:
        """
        Send a message to Kafka topic
        Returns the task_id used for the message
        """
        task_id = task_id or self.generate_task_id()
        message = Message(
            action=action,
            model_name=model_name,
            data=data
        )

        await self.producer.send_and_wait(
            topic=produce_topic or self.produce_topic,
            key=task_id.encode(),
            value=message.json().encode()
        )

        logger.info(f"Sent message for task {task_id}")
        return task_id

    async def consume_messages(
        self,
        timeout_ms: int = 1000,
        max_messages: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Consume messages from Kafka with optional timeout and max messages
        Returns dict of {task_id: message_data}
        """
        results = {}
        try:
            while max_messages is None or len(results) < max_messages:
                msg = await asyncio.wait_for(
                    self.consumer.__anext__(),
                    timeout=timeout_ms / 1000
                )

                task_id = msg.key.decode()
                message = Message(**json.loads(msg.value.decode()))
                results[task_id] = message.data

                if max_messages and len(results) >= max_messages:
                    break

        except asyncio.TimeoutError:
            pass

        return results

    async def get_result(
        self,
        task_id: str,
        timeout_ms: int = 5000,
        poll_interval_ms: int = 100
    ) -> Optional[Any]:
        """
        Wait for a specific task result
        Returns None if timeout reached
        """
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) * 1000 < timeout_ms:
            messages = await self.consume_messages(timeout_ms=poll_interval_ms)
            if task_id in messages:
                return messages[task_id]

        return None
