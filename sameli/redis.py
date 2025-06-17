import asyncio
import json
from typing import Any, Optional

import aioredis
from loguru import logger

from sameli.metrics import Metrics


class RedisClient:
    def __init__(
        self,
        redis_url: str,
        result_prefix: str = "result",
        ttl: Optional[int] = None,
        pool_size: int = 10,
    ):
        self.redis_url = redis_url
        self.result_prefix = result_prefix
        self.ttl = ttl
        self.pool_size = pool_size
        self.redis: Optional[aioredis.Redis] = None
        self._lock = asyncio.Lock()

    async def connect(self):
        if self.redis is not None and self.redis.connection is not None and not self.redis.connection.is_connected:
            await self.redis.close()
            self.redis = None

        if self.redis is None:
            try:
                self.redis = await aioredis.from_url(
                    url=self.redis_url,
                    max_connections=self.pool_size,
                    decode_responses=False,
                )
                logger.info("Connected to Redis")
            except (aioredis.ConnectionError, aioredis.RedisError) as e:
                Metrics.redis_error_total.labels(stage="connect", error="connection_error").inc()
                logger.error(f"Redis connection error: {e}")
                raise

    async def disconnect(self):
        if self.redis is not None:
            await self.redis.close()
            self.redis = None
            logger.info("Disconnected from Redis")

    async def store_result(
        self, task_id: str, result: Any, ttl: Optional[int] = None
    ) -> bool:
        async with self._lock:
            try:
                await self.connect()

                key = f"{self.result_prefix}:{task_id}"
                value = (
                    json.dumps(result).encode("utf-8")
                    if not isinstance(result, (bytes, bytearray))
                    else result
                )

                effective_ttl = ttl if ttl is not None else self.ttl

                if effective_ttl is not None:
                    await self.redis.setex(key, effective_ttl, value)
                else:
                    await self.redis.set(key, value)

                Metrics.redis_operations_total.labels(operation="store").inc()
                return True

            except aioredis.RedisError as e:
                Metrics.redis_error_total.labels(stage="store", error="operation_failed").inc()
                logger.error(f"Failed to store result in Redis: {e}")
                return False

    async def get_result(self, task_id: str) -> Optional[Any]:
        async with self._lock:
            try:
                await self.connect()

                key = f"{self.result_prefix}:{task_id}"
                value = await self.redis.get(key)

                if value is None:
                    Metrics.redis_operations_total.labels(operation="get_miss").inc()
                    return None

                try:
                    result = json.loads(value.decode("utf-8"))
                    Metrics.redis_operations_total.labels(operation="get_hit").inc()
                    return result
                except json.JSONDecodeError:
                    return value

            except aioredis.RedisError as e:
                Metrics.redis_error_total.labels(stage="get", error="operation_failed").inc()
                logger.error(f"Failed to get result from Redis: {e}")
                return None

    async def delete_result(self, task_id: str) -> bool:
        async with self._lock:
            try:
                await self.connect()

                key = f"{self.result_prefix}:{task_id}"
                deleted = await self.redis.delete(key)

                Metrics.redis_operations_total.labels(operation="delete").inc()
                return deleted > 0

            except aioredis.RedisError as e:
                Metrics.redis_error_total.labels(stage="delete", error="operation_failed").inc()
                logger.error(f"Failed to delete result from Redis: {e}")
                return False