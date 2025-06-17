import json
import unittest
from unittest.mock import AsyncMock, patch

from sameli.redis import RedisClient


class RedisClientTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.redis_url = "redis://localhost"
        self.result_prefix = "result"
        self.ttl = 3600
        self.client = RedisClient(self.redis_url, result_prefix=self.result_prefix, ttl=self.ttl)

        # Patch aioredis.from_url globally for the tests
        self.redis_patcher = patch("sameli.redis.aioredis.from_url", new_callable=AsyncMock)
        self.mock_from_url = self.redis_patcher.start()

        # Create a mock redis instance and assign to the patch's return value
        self.mock_redis_instance = AsyncMock()
        self.mock_from_url.return_value = self.mock_redis_instance

        self.addCleanup(self.redis_patcher.stop)

    async def asyncTearDown(self):
        if self.client.redis is not None:
            await self.client.disconnect()

    async def test_connect_creates_redis_client(self):
        await self.client.connect()
        self.mock_from_url.assert_awaited_once_with(
            url=self.redis_url,
            max_connections=self.client.pool_size,
            decode_responses=False,
        )
        self.assertEqual(self.client.redis, self.mock_redis_instance)

    async def test_disconnect_closes_connection(self):
        await self.client.connect()
        await self.client.disconnect()
        self.mock_redis_instance.close.assert_awaited_once()
        self.assertIsNone(self.client.redis)

    async def test_store_result_with_ttl(self):
        await self.client.connect()
        task_id = "task1"
        result_data = {"value": 123}

        result = await self.client.store_result(task_id, result_data)
        key = f"{self.result_prefix}:{task_id}"
        value = json.dumps(result_data).encode("utf-8")

        self.mock_redis_instance.setex.assert_awaited_once_with(key, self.ttl, value)
        self.assertTrue(result)

    async def test_store_result_without_ttl(self):
        self.client.ttl = None
        await self.client.connect()
        task_id = "task2"
        result_data = {"status": "ok"}

        result = await self.client.store_result(task_id, result_data)
        key = f"{self.result_prefix}:{task_id}"
        value = json.dumps(result_data).encode("utf-8")

        self.mock_redis_instance.set.assert_awaited_once_with(key, value)
        self.assertTrue(result)

    async def test_get_result_found_and_json_decoded(self):
        await self.client.connect()
        task_id = "task3"
        expected_data = {"result": "ok"}
        encoded_value = json.dumps(expected_data).encode("utf-8")

        self.mock_redis_instance.get.return_value = encoded_value

        result = await self.client.get_result(task_id)
        key = f"{self.result_prefix}:{task_id}"

        self.mock_redis_instance.get.assert_awaited_once_with(key)
        self.assertEqual(result, expected_data)

    async def test_get_result_not_found(self):
        await self.client.connect()
        task_id = "task4"

        self.mock_redis_instance.get.return_value = None

        result = await self.client.get_result(task_id)
        key = f"{self.result_prefix}:{task_id}"

        self.mock_redis_instance.get.assert_awaited_once_with(key)
        self.assertIsNone(result)

    async def test_get_result_with_invalid_json(self):
        await self.client.connect()
        task_id = "task5"
        raw_value = b"non-json-bytes"

        self.mock_redis_instance.get.return_value = raw_value

        result = await self.client.get_result(task_id)
        self.assertEqual(result, raw_value)

    async def test_delete_result_successful(self):
        await self.client.connect()
        task_id = "task6"

        self.mock_redis_instance.delete.return_value = 1

        result = await self.client.delete_result(task_id)
        key = f"{self.result_prefix}:{task_id}"

        self.mock_redis_instance.delete.assert_awaited_once_with(key)
        self.assertTrue(result)

    async def test_delete_result_not_found(self):
        await self.client.connect()
        task_id = "task7"

        self.mock_redis_instance.delete.return_value = 0

        result = await self.client.delete_result(task_id)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
