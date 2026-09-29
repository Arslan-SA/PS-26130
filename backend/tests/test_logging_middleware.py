"""
Unit tests for RequestContextMiddleware and X-Request-ID propagation.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_request_id_generated_automatically():
    """Verify that an incoming request without X-Request-ID receives a new UUID."""
    response = client.get("/")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    req_id = response.headers["x-request-id"]
    assert len(req_id) == 36  # Standard UUID length


def test_request_id_forwarded_from_client():
    """Verify that a client-provided X-Request-ID is preserved and returned."""
    custom_id = "test-custom-correlation-12345"
    response = client.get("/", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == custom_id
