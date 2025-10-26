import os
import pytest
from fastapi.testclient import TestClient

# Ensure test-friendly environment prior to importing the app
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("METRICS_ENABLED", "1")

from app.main import app  # noqa: E402

@pytest.fixture(scope="session")
def client():
    return TestClient(app)

def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] in ("healthy", "ok")

def test_openapi_json(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "openapi" in data
    assert "paths" in data

def test_docs_page(client):
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")

def test_metrics_endpoint(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    # Content may vary depending on prometheus_client availability,
    # but it should be plaintext with metrics payload when enabled.
    assert "text" in resp.headers.get("content-type", "").lower()