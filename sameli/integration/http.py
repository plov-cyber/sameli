import uuid
from typing import Any, Dict, Optional

import httpx


class SameliHttpClient:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(base_url=base_url)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    @staticmethod
    def generate_task_id() -> str:
        """Generate a random 8-character hex task ID"""
        return str(uuid.uuid4())

    async def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Any:
        """Internal method for making API requests"""
        url = f"{self.base_url}/api/v1/model/{endpoint}"
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    async def preprocess(self, raw_features: Dict[str, Any], task_id: Optional[str] = None) -> Dict[str, Any]:
        """Send raw features for preprocessing"""
        task_id = task_id or self.generate_task_id()
        return await self._make_request(
            "preprocess",
            {"task_id": task_id, "raw_features": raw_features}
        )

    async def predict(self, features: Dict[str, Any], task_id: Optional[str] = None) -> Any:
        """Get predictions from processed features"""
        task_id = task_id or self.generate_task_id()
        return await self._make_request(
            "predict",
            {"task_id": task_id, "features": features}
        )

    async def pipeline(self, raw_features: Dict[str, Any], task_id: Optional[str] = None) -> Any:
        """Run complete preprocessing + prediction pipeline"""
        task_id = task_id or self.generate_task_id()
        return await self._make_request(
            "pipeline",
            {"task_id": task_id, "raw_features": raw_features}
        )

    async def postprocess(self, predictions: Any, task_id: Optional[str] = None) -> Any:
        """Post-process model predictions"""
        task_id = task_id or self.generate_task_id()
        return await self._make_request(
            "postprocess",
            {"task_id": task_id, "predictions": predictions}
        )

    async def health_check(self) -> bool:
        """Check if service is alive"""
        url = f"{self.base_url}/api/v1/health/liveness"
        try:
            response = await self.client.get(url, timeout=2.0)
            return response.status_code == 200
        except httpx.RequestError:
            return False
