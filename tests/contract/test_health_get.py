"""
Contract test for GET /api/v1/health endpoint
This test MUST fail until the endpoint is implemented
"""
import pytest


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def test_health_endpoint_exists(client):
    """Test that health endpoint exists and returns correct structure"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert data["status"] == "healthy"


def test_health_endpoint_no_auth_required(client):
    """Test that health endpoint doesn't require authentication"""
    # Should work without X-API-Key header
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_response_schema(client):
    """Test that health response matches OpenAPI schema"""
    response = client.get("/api/v1/health")
    data = response.json()
    
    # Validate response structure
    assert isinstance(data["status"], str)
    assert isinstance(data["timestamp"], str)
    
    # Validate timestamp format (ISO 8601)
    import datetime
    datetime.datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))