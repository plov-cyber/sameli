import random
import string
import uuid

from locust import HttpUser, between, task


def generate_random_string(min_len=100, max_len=200):
    """Generate random string of length between min_len and max_len"""
    length = random.randint(min_len, max_len)
    return ''.join(random.choices(
        string.ascii_letters + string.digits + ' ',  # Include space
        k=length
    ))


class SameliModelUser(HttpUser):
    wait_time = between(0.5, 2.5)  # More aggressive wait time

    @task
    def predict(self):
        # Generate random task_id using UUIDv4
        task_id = str(uuid.uuid4())

        payload = {
            "raw_features": {
                "text": generate_random_string(),  # Random string
            },
            "task_id":      task_id  # Random UUID
        }

        headers = {"Content-Type": "application/json"}

        with self.client.post(
                "/api/v1/model/pipeline",
                json=payload,
                headers=headers,
                catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Status code: {response.status_code}")
