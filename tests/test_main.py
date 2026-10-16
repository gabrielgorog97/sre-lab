from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_returns_message():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello from sre-lab"}


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
