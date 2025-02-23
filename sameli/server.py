import fastapi
import uvicorn
from contextlib import asynccontextmanager
from loguru import logger

import sameli
from sameli.conf import Conf
from sameli.routers import liveness_router, model_router
import sameli.models


class Server:
    def __init__(self, settings: Conf):
        self.settings = settings

    def start(self):
        self.prepare()
        self.run()

    def prepare(self):
        self.setup_model()
        # self.setup_kafka()
        self.setup_app()

    def run(self):
        uvicorn.run(self.app, **self.settings.http_conf)

    def setup_model(self):
        model_conf = self.settings.model_conf

        self.model = getattr(sameli.models, model_conf.get('type'))(**model_conf)
        self.model.load()

    # def setup_kafka(self):
    #     pass

    def setup_app(self):
        self.app = fastapi.FastAPI(
            title=self.settings.app_name,
            version=sameli.__version__,
            lifespan=self.lifespan_callback()
        )

        self.app.include_router(
            liveness_router,
            prefix="/api/v1/health",
            tags=["Get App Status"]
        )
        self.app.include_router(
            model_router,
            prefix="/api/v1/model",
            tags=["Run Model Functions"]
        )

    def lifespan_callback(self):
        @asynccontextmanager
        async def lifespan(app: fastapi.FastAPI):
            logger.info("Start up server")
            yield {'model': self.model}
            logger.info("Shutting down server")

        return lifespan