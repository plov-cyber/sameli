import time

import fastapi
import prometheus_client as prom


class Metrics:
    requests_total = prom.Counter(
        namespace="sameli",
        subsystem="server",
        name="requests_total",
        documentation="Total number of HTTP requests processed.",
        labelnames=["method", "status", "path"]
    )

    request_time_seconds = prom.Histogram(
        namespace="sameli",
        subsystem="server",
        name="request_duration_seconds",
        documentation="Total time spent for HTTP request.",
        buckets=(0.001, 0.002, 0.003, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.00),
        labelnames=["method", "path"]
    )


async def log_request(request: fastapi.Request, call_next) -> fastapi.Response:
    start_time = time.perf_counter()
    response: fastapi.Response = await call_next(request)
    latency = time.perf_counter() - start_time

    if request.url.path.startswith("/api"):
        Metrics.requests_total.labels(method=request.method, status=int(response.status_code), path=request.url.path).inc()
        Metrics.request_time_seconds.labels(method=request.method, path=request.url.path).observe(latency)

    return response
