import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def no_chaos():
    client.post("/api/chaos", json={"latency_ms": 0, "error_rate": 0})
    yield
    client.post("/api/chaos", json={"latency_ms": 0, "error_rate": 0})


def test_root_serves_the_store():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Demo store" in response.text


def test_products_are_listed():
    products = client.get("/api/products").json()
    assert len(products) == 6
    assert {"id", "name", "price"} <= products[0].keys()


def test_checkout_returns_total():
    response = client.post(
        "/api/checkout", json={"items": [{"id": "mug", "qty": 2}, {"id": "socks", "qty": 1}]}
    )
    assert response.status_code == 200
    assert response.json()["total"] == 40.0
    assert 'shop_orders_total{result="ok"}' in client.get("/metrics").text


def test_checkout_rejects_unknown_product():
    response = client.post("/api/checkout", json={"items": [{"id": "nope", "qty": 1}]})
    assert response.status_code == 400


def test_chaos_makes_checkout_fail_and_is_counted():
    client.post("/api/chaos", json={"latency_ms": 0, "error_rate": 1.0})
    assert client.get("/api/chaos").json()["expires_in"] > 0

    response = client.post("/api/checkout", json={"items": [{"id": "mug", "qty": 1}]})
    assert response.status_code == 503

    metrics = client.get("/metrics").text
    assert 'path="/api/checkout",status="503"' in metrics
    assert 'shop_orders_total{result="failed"}' in metrics


def test_chaos_rejects_out_of_range_values():
    response = client.post("/api/chaos", json={"latency_ms": 99999, "error_rate": 2})
    assert response.status_code == 422


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_metrics_counts_requests():
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert 'http_requests_total{method="GET",path="/health",status="200"}' in response.text


def test_error_returns_500_and_is_counted():
    response = client.get("/error")
    assert response.status_code == 500
    metrics = client.get("/metrics").text
    assert 'http_requests_total{method="GET",path="/error",status="500"}' in metrics


def test_unknown_paths_share_one_label():
    client.get("/does-not-exist-1")
    client.get("/does-not-exist-2")
    metrics = client.get("/metrics").text
    assert 'path="unmatched",status="404"' in metrics
    assert "does-not-exist" not in metrics
