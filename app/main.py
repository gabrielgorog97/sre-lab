import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.routing import Match

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


def route_template(request: Request) -> str:
    # Raw URLs would create a new time series for every unknown path.
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return route.path
    return "unmatched"


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    path = route_template(request)
    LATENCY.labels(path=path).observe(time.perf_counter() - start)
    REQUESTS.labels(method=request.method, path=path, status=response.status_code).inc()
    return response


@app.get("/")
def root():
    return {"message": "Hello from sre-lab"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/error")
def error():
    return JSONResponse(status_code=500, content={"error": "simulated failure"})


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
