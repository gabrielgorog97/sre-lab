import asyncio
import random
import socket
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field
from starlette.routing import Match

app = FastAPI(title="sre-lab")

INDEX_HTML = Path(__file__).parent / "static" / "index.html"
POD_NAME = socket.gethostname()
CHAOS_TTL_SECONDS = 300

PRODUCTS = {
    "mug": {"name": "On-call Mug", "price": 14.0, "emoji": "☕", "tag": "Survives 3am pages"},
    "hoodie": {"name": "Incident Hoodie", "price": 49.0, "emoji": "🧥", "tag": "SEV1 comfort"},
    "stickers": {
        "name": "99.9% Sticker Pack",
        "price": 6.0,
        "emoji": "🏷️",
        "tag": "Three nines, no more",
    },
    "socks": {"name": "Rollback Socks", "price": 12.0, "emoji": "🧦", "tag": "Undo cold feet"},
    "notebook": {
        "name": "Postmortem Notebook",
        "price": 18.0,
        "emoji": "📓",
        "tag": "Blameless pages",
    },
    "plush": {"name": "Pod Plush", "price": 24.0, "emoji": "🐳", "tag": "Never CrashLoops"},
}

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
ORDERS = Counter(
    "shop_orders_total",
    "Checkout attempts by result",
    ["result"],
)

# Chaos lives in memory, so with several replicas it only affects the pod that received it.
chaos = {"latency_ms": 0, "error_rate": 0.0, "expires_at": 0.0}


class CartItem(BaseModel):
    id: str
    qty: int = Field(ge=1, le=20)


class Checkout(BaseModel):
    items: list[CartItem] = Field(min_length=1)


class Chaos(BaseModel):
    latency_ms: int = Field(ge=0, le=5000)
    error_rate: float = Field(ge=0.0, le=1.0)


def active_chaos() -> dict:
    if time.time() > chaos["expires_at"]:
        chaos.update(latency_ms=0, error_rate=0.0, expires_at=0.0)
    return chaos


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
def index():
    return FileResponse(INDEX_HTML)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/error")
def error():
    return JSONResponse(status_code=500, content={"error": "simulated failure"})


@app.get("/api/products")
def products():
    return [{"id": pid, **p} for pid, p in PRODUCTS.items()]


@app.post("/api/checkout")
async def checkout(order: Checkout):
    unknown = [i.id for i in order.items if i.id not in PRODUCTS]
    if unknown:
        raise HTTPException(status_code=400, detail=f"unknown products: {unknown}")

    c = active_chaos()
    if c["latency_ms"]:
        await asyncio.sleep(c["latency_ms"] / 1000)
    if random.random() < c["error_rate"]:
        ORDERS.labels(result="failed").inc()
        return JSONResponse(
            status_code=503,
            content={"error": "payment provider unavailable", "pod": POD_NAME},
        )

    total = sum(PRODUCTS[i.id]["price"] * i.qty for i in order.items)
    ORDERS.labels(result="ok").inc()
    return {"order_id": uuid.uuid4().hex[:8], "total": round(total, 2), "pod": POD_NAME}


@app.get("/api/chaos")
def get_chaos():
    c = active_chaos()
    remaining = max(0, int(c["expires_at"] - time.time()))
    return {
        "latency_ms": c["latency_ms"],
        "error_rate": c["error_rate"],
        "expires_in": remaining,
        "pod": POD_NAME,
    }


@app.post("/api/chaos")
def set_chaos(settings: Chaos):
    enabled = settings.latency_ms > 0 or settings.error_rate > 0
    chaos.update(
        latency_ms=settings.latency_ms,
        error_rate=settings.error_rate,
        expires_at=time.time() + CHAOS_TTL_SECONDS if enabled else 0.0,
    )
    return get_chaos()


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
