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

    request_elapsed_summary = prom.Summary(
        namespace="sameli",
        subsystem="server",
        name="request_elapsed_summary",
        documentation="Total time spent for HTTP request.",
        labelnames=["method", "path"]
    )

    kafka_msgs_total = prom.Counter(
        namespace="sameli",
        subsystem="kafka",
        name="msgs_total",
        documentation="Total number of Kafka messages processed.",
        labelnames=["action", "outcome"]
    )

    kafka_msg_waiting_summary = prom.Summary(
        namespace="sameli",
        subsystem="kafka",
        name="msg_waiting",
        documentation="Total waiting time in Kafka topic in milliseconds.",
        labelnames=["topic", "partition"]
    )

    kafka_msgs_summary = prom.Summary(
        namespace="sameli",
        subsystem="kafka",
        name="msgs_summary",
        documentation="Total time spend for Kafka message.",
        labelnames=["action"]
    )

    kafka_error_total = prom.Counter(
        namespace="sameli",
        subsystem="kafka",
        name="error_total",
        documentation="Total errors in KafkaClient.",
        labelnames=["stage", "error"]
    )


async def log_request(request: fastapi.Request, call_next) -> fastapi.Response:
    with Metrics.request_elapsed_summary.labels(method=request.method, path=request.url.path).time():
        response: fastapi.Response = await call_next(request)

    Metrics.requests_total.labels(method=request.method, status=int(response.status_code), path=request.url.path).inc()

    return response
