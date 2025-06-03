import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from sameli.kafka import KafkaClient, Message
from sameli.models import BaseModel
from sameli.redis import RedisClient


class KafkaClientTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Patch Kafka client classes (not with new_callable=AsyncMock!)
        self.consumer_patcher = patch("sameli.kafka.AIOKafkaConsumer")
        self.producer_patcher = patch("sameli.kafka.AIOKafkaProducer")

        self.mock_consumer_class = self.consumer_patcher.start()
        self.mock_producer_class = self.producer_patcher.start()

        # Return AsyncMock instances when called
        self.mock_consumer_instance = AsyncMock()
        self.mock_producer_instance = AsyncMock()
        self.mock_consumer_class.return_value = self.mock_consumer_instance
        self.mock_producer_class.return_value = self.mock_producer_instance

        self.addCleanup(self.consumer_patcher.stop)
        self.addCleanup(self.producer_patcher.stop)

        # Mock model
        self.model = MagicMock(spec=BaseModel)
        self.model.name = "test_model"
        self.model.actions = ["predict"]
        self.model.predict = MagicMock(return_value="result")

        # Mock redis
        self.redis = AsyncMock(spec=RedisClient)
        self.redis.store_result = AsyncMock()

        # KafkaClient instance
        self.client = KafkaClient(
            model=self.model,
            redis=self.redis,
            consume_topic="input",
            consumer_conf={"bootstrap_servers": "localhost:9092"},
            produce_topic="output",
            producer_conf={"bootstrap_servers": "localhost:9092"},
            msg_wait_timeout=0.1
        )

    def tearDown(self):
        # Clean up event loop created by KafkaClient
        if self.client.loop.is_running():
            self.client.loop.stop()
        if not self.client.loop.is_closed():
            self.client.loop.close()

    async def test_prepare_starts_clients(self):
        await asyncio.wait_for(self.client.prepare(), timeout=1.5)

        self.mock_consumer_instance.start.assert_awaited_once()
        self.mock_producer_instance.start.assert_awaited_once()

    def test_is_skip_returns_true_on_wrong_model(self):
        msg = Message(action="predict", model_name="wrong_model", data={})
        self.assertTrue(self.client.is_skip(msg))

    def test_is_skip_returns_true_on_invalid_action(self):
        msg = Message(action="invalid_action", model_name="test_model", data={})
        self.assertTrue(self.client.is_skip(msg))

    def test_is_skip_returns_false_for_valid_message(self):
        msg = Message(action="predict", model_name="test_model", data={})
        self.assertFalse(self.client.is_skip(msg))

    async def test_get_message_success(self):
        mock_msg = MagicMock()
        mock_msg.value = json.dumps({
            "action":     "predict",
            "model_name": "test_model",
            "data":       {}
        }).encode("utf-8")
        mock_msg.topic = "input"
        mock_msg.partition = 0
        mock_msg.key = b"task_1"

        mock_consumer_instance = AsyncMock()
        mock_consumer_instance.__anext__.return_value = mock_msg
        self.client.consumer = mock_consumer_instance

        task_id, msg = await self.client.get_message()
        self.assertEqual(task_id, b"task_1")
        self.assertIsInstance(msg, Message)
        self.assertEqual(msg.action, "predict")

    def test_run_action_calls_model_method(self):
        msg = Message(action="predict", model_name="test_model", data={})
        result = self.client.run_action(msg)
        self.assertEqual(result, "result")
        self.model.predict.assert_called_once_with({})

    def test_run_action_handles_exception(self):
        msg = Message(action="predict", model_name="test_model", data={})
        self.client.model.predict.side_effect = Exception("fail")

        result = self.client.run_action(msg)
        self.assertIsNone(result)

    async def test_shutdown_stops_clients(self):
        mock_consumer = AsyncMock()
        mock_producer = AsyncMock()
        self.client.consumer = mock_consumer
        self.client.producer = mock_producer

        await self.client.shutdown()

        mock_consumer.stop.assert_awaited_once()
        mock_producer.stop.assert_awaited_once()

    async def test_process_messages_skips_invalid_and_stops(self):
        self.client.get_message = AsyncMock(side_effect=[
            (None, None),
            (b"task_1", Message(action="predict", model_name="wrong_model", data={})),
            asyncio.CancelledError
        ])
        self.client.is_skip = MagicMock(return_value=True)
        self.client._interrupt_event.set = MagicMock()

        with patch.object(self.client, "producer", AsyncMock()), \
                patch.object(self.client, "redis", AsyncMock()), \
                patch("sameli.metrics.Metrics"):
            task = asyncio.create_task(self.client.process_messages())

            await asyncio.sleep(0.2)
            task.cancel()

            with self.assertRaises(asyncio.CancelledError):
                await task

            self.assertTrue(self.client.is_skip.called)


if __name__ == "__main__":
    unittest.main()
