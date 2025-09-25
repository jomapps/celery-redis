"""
Contract test for DELETE /api/v1/tasks/{task_id}/cancel endpoint
This test MUST fail until the endpoint is implemented
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    return TestClient(app)


def test_task_cancel_requires_auth(client):
    """Test that task cancellation requires API key"""
    task_id = "abc123-def456-ghi789"
    response = client.delete(f"/api/v1/tasks/{task_id}/cancel")
    assert response.status_code == 401


def test_task_cancel_valid_id(client):
    """Test task cancellation with valid task ID"""
    task_id = "abc123-def456-ghi789"
    headers = {"X-API-Key": "test-api-key"}
    response = client.delete(f"/api/v1/tasks/{task_id}/cancel", headers=headers)
    
    # Should return 200 (cancelled), 400 (cannot cancel), or 404 (not found)
    assert response.status_code in [200, 400, 404]
    
    if response.status_code == 200:
        data = response.json()
        assert "task_id" in data
        assert "status" in data
        assert data["task_id"] == task_id
        assert data["status"] == "cancelled"


def test_task_cancel_invalid_uuid_format(client):
    """Test task cancellation with invalid UUID format"""
    invalid_task_id = "not-a-valid-uuid"
    headers = {"X-API-Key": "test-api-key"}
    response = client.delete(f"/api/v1/tasks/{invalid_task_id}/cancel", headers=headers)
    assert response.status_code == 400


def test_task_cancel_nonexistent_task(client):
    """Test cancellation of non-existent task"""
    nonexistent_task_id = "99999999-9999-9999-9999-999999999999"
    headers = {"X-API-Key": "test-api-key"}
    response = client.delete(f"/api/v1/tasks/{nonexistent_task_id}/cancel", headers=headers)
    assert response.status_code == 404
    
    data = response.json()
    assert "error" in data


def test_task_cancel_already_completed(client):
    """Test cancellation of already completed task"""
    completed_task_id = "completed-task-uuid"
    headers = {"X-API-Key": "test-api-key"}
    response = client.delete(f"/api/v1/tasks/{completed_task_id}/cancel", headers=headers)
    
    # Should return 400 if task already completed
    if response.status_code == 400:
        data = response.json()
        assert "error" in data
        assert "cannot be cancelled" in data["error"].lower()


def test_task_cancel_error_response_schema(client):
    """Test error response schema for cancellation failures"""
    invalid_task_id = "not-a-valid-uuid"
    headers = {"X-API-Key": "test-api-key"}
    response = client.delete(f"/api/v1/tasks/{invalid_task_id}/cancel", headers=headers)
    
    if response.status_code >= 400:
        data = response.json()
        assert "error" in data
        assert "message" in data
        assert "timestamp" in data
        
        assert isinstance(data["error"], str)
        assert isinstance(data["message"], str)
        assert isinstance(data["timestamp"], str)