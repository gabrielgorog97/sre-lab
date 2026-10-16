import time

from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

app = FastAPI(title="sre-lab")

REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["path"],
)


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    path = request.url.path
    LATENCY.labels(path=path).observe(time.perf_counter() - start)
    REQUESTS.labels(method=request.method, path=path, status=response.status_code).inc()
    return response


@app.get("/")
def root():
    return {"message": "Hello from sre-lab"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
