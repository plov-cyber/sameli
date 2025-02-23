from contextlib import asynccontextmanager

import fastapi
import uvicorn
from loguru import logger

import sameli
import sameli.models
from sameli.conf import Conf
from sameli.kafka import KafkaClient
from sameli.routers import liveness_router, model_router


class Server:
    def __init__(self, settings: Conf):
        self.settings = settings

    def start(self):
        self.prepare()
        self.run()

    def prepare(self):
        self.setup_model()

        if self.settings.enable_kafka:
            self.setup_kafka()

        self.setup_http()

    def setup_model(self):
        model_conf = self.settings.model_conf

        self.model = getattr(sameli.models, model_conf.get('type'))(**model_conf)
        self.model.load()

    def setup_kafka(self):
        kafka_conf = self.settings.kafka_conf

        self.kafka_client = KafkaClient(model=self.model, **kafka_conf)

    def setup_http(self):
        self.app = fastapi.FastAPI(
            title=self.settings.app_name,
            version=sameli.__version__,
            lifespan=self.lifespan_callback()
        )

        self.app.include_router(
            liveness_router,
            prefix="/api/v1/health",
            tags=["App Status"]
        )
        self.app.include_router(
            model_router,
            prefix="/api/v1/model",
            tags=["Model Functions"]
        )

    def run(self):
        uvicorn.run(self.app, **self.settings.http_conf)

    def lifespan_callback(self):
        @asynccontextmanager
        async def lifespan(app: fastapi.FastAPI):
            logger.info("Starting server")
            if self.settings.enable_kafka:
                self.kafka_client.start()

            yield {'model': self.model}

            logger.info("Stopping server")
            if self.settings.enable_kafka:
                self.kafka_client.stop()
                self.kafka_client.join()

        return lifespan
