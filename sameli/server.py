from contextlib import asynccontextmanager

import fastapi
import prometheus_client as prom
import uvicorn
from fastapi import FastAPI
from loguru import logger

import sameli
import sameli.models
from sameli.conf import Conf
from sameli.kafka import KafkaClient
from sameli.metrics import log_request
from sameli.models import BaseModel, models_list
from sameli.redis import RedisClient
from sameli.routers import liveness_router, model_router


class Server:
    def __init__(self, settings: Conf):
        self.settings = settings
        prom.start_http_server(self.settings.metrics_port)

        self.model: BaseModel = self.setup_model()
        self.redis_client: RedisClient = self.setup_redis()

        if self.settings.enable_kafka:
            self.kafka_client: KafkaClient = self.setup_kafka()

        self.app: FastAPI = self.setup_http()

    def setup_model(self) -> BaseModel:
        if self.settings.model_type not in models_list:
            raise NotImplementedError(f"Unknown model type: {self.settings.model_type}")

        model = getattr(sameli.models, self.settings.model_type)(**self.settings.model_conf)
        model.save(model.load())

        return model

    def setup_kafka(self) -> KafkaClient:
        kafka_conf = self.settings.kafka_conf
        return KafkaClient(model=self.model, redis=self.redis_client, **kafka_conf)

    def setup_redis(self) -> RedisClient:
        redis_conf = self.settings.redis_conf
        return RedisClient(**redis_conf)

    def setup_http(self) -> FastAPI:
        app = fastapi.FastAPI(
            title=self.settings.app_name,
            version=sameli.__version__,
            lifespan=self.lifespan_callback()
        )

        app.include_router(liveness_router, prefix="/api/v1/health", tags=["App Status"])
        app.include_router(model_router, prefix="/api/v1/model", tags=["Model Functions"])
        app.middleware("http")(log_request)

        return app

    def run(self) -> None:
        uvicorn.run(self.app, **self.settings.http_conf)

    def lifespan_callback(self):
        @asynccontextmanager
        async def lifespan(app: fastapi.FastAPI):
            logger.info("Starting server")
            await self.redis_client.connect()
            if self.settings.enable_kafka:
                self.kafka_client.start()

            yield {'model': self.model, 'redis': self.redis_client}

            logger.info("Stopping server")
            await self.redis_client.disconnect()
            if self.settings.enable_kafka:
                self.kafka_client.stop()
                self.kafka_client.join()

        return lifespan
