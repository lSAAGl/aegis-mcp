from fastapi.testclient import TestClient
from src.app.main import app

client = TestClient(app)

def test_health_endpoint_returns_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}