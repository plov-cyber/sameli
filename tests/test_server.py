import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from sameli.conf import Conf
from sameli.server import Server


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.settings_mock = MagicMock(spec=Conf)
        self.settings_mock.app_name = "TestApp"
        self.settings_mock.model_type = "PyTorchModel"
        self.settings_mock.model_conf = {
            "name":      "test_model",
            "artefacts": {"model": "path/to/model.pt"},
            "hparams":   {},
        }
        self.settings_mock.enable_kafka = True
        self.settings_mock.kafka_conf = {
            "consume_topic": "test-consume",
            "consumer_conf": {},
            "produce_topic": "test-produce",
            "producer_conf": {},
        }
        self.settings_mock.redis_conf = {"redis_url": "redis://localhost:6379"}
        self.settings_mock.http_conf = {"host": "127.0.0.1", "port": 8000}
        self.settings_mock.metrics_port = 9000

    @patch("sameli.server.prom.start_http_server")
    @patch("sameli.server.RedisClient")
    @patch("sameli.server.KafkaClient")
    @patch("sameli.server.sameli.models.PyTorchModel")
    def test_server_initializes_components(
        self, mock_model_cls, mock_kafka_cls, mock_redis_cls, mock_start_metrics
    ):
        mock_model_instance = MagicMock()
        mock_model_cls.return_value = mock_model_instance
        mock_model_instance.load.return_value = "loaded_model"

        server = Server(self.settings_mock)

        mock_start_metrics.assert_called_once_with(self.settings_mock.metrics_port)
        mock_model_cls.assert_called_once_with(**self.settings_mock.model_conf)
        mock_model_instance.save.assert_called_once_with("loaded_model")

        mock_redis_cls.assert_called_once_with(**self.settings_mock.redis_conf)
        mock_kafka_cls.assert_called_once_with(model=server.model, redis=server.redis_client,
                                               **self.settings_mock.kafka_conf)

        self.assertIsNotNone(server.app)

    @patch("sameli.server.prom.start_http_server")
    @patch("sameli.server.sameli.models")
    def test_setup_model_raises_on_unknown_type(self, mock_models, mock_start_metrics):
        self.settings_mock.model_type = "UnknownModel"
        mock_models.models_list = ["PyTorchModel"]

        with self.assertRaises(NotImplementedError):
            Server(self.settings_mock)

    @patch("sameli.server.prom.start_http_server")
    @patch("sameli.server.RedisClient")
    @patch("sameli.server.KafkaClient")
    @patch("sameli.server.sameli.models.PyTorchModel")
    def test_lifespan_starts_and_stops_resources(
        self, mock_model_cls, mock_kafka_cls, mock_redis_cls, mock_start_metrics
    ):
        mock_model_instance = MagicMock()
        mock_model_instance.load.return_value = "loaded_model"
        mock_model_cls.return_value = mock_model_instance

        mock_redis_instance = AsyncMock()
        mock_redis_cls.return_value = mock_redis_instance

        mock_kafka_instance = MagicMock()
        mock_kafka_cls.return_value = mock_kafka_instance

        server = Server(self.settings_mock)
        lifespan = server.lifespan_callback()

        async def run_lifespan():
            async with lifespan(server.app) as state:
                self.assertIn("model", state)
                self.assertIn("redis", state)
                mock_redis_instance.connect.assert_awaited_once()
                mock_kafka_instance.start.assert_called_once()

            mock_redis_instance.disconnect.assert_awaited_once()
            mock_kafka_instance.stop.assert_called_once()
            mock_kafka_instance.join.assert_called_once()

        asyncio.run(run_lifespan())

    @patch("sameli.server.RedisClient")
    @patch("sameli.server.KafkaClient")
    @patch("sameli.server.sameli.models.PyTorchModel")
    def test_http_setup_registers_routers_and_middleware(self, mock_model_cls, mock_kafka_cls, mock_redis_cls):
        mock_model_instance = MagicMock()
        mock_model_instance.load.return_value = "loaded_model"
        mock_model_cls.return_value = mock_model_instance

        server = Server(self.settings_mock)
        routes = [route.path for route in server.app.routes]

        self.assertIn("/api/v1/health/live", routes)
        self.assertIn("/api/v1/model/predict", routes)

        middlewares = [m for m in server.app.user_middleware]
        self.assertGreaterEqual(len(middlewares), 1)


if __name__ == "__main__":
    unittest.main()
