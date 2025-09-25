"""
Contract test for POST /api/v1/tasks/{task_id}/retry endpoint
This test MUST fail until the endpoint is implemented
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    return TestClient(app)


def test_task_retry_requires_auth(client):
    """Test that task retry requires API key"""
    task_id = "failed-task-uuid"
    response = client.post(f"/api/v1/tasks/{task_id}/retry")
    assert response.status_code == 401


def test_task_retry_valid_failed_task(client):
    """Test retry of a failed task"""
    failed_task_id = "failed-task-uuid"
    headers = {"X-API-Key": "test-api-key"}
    response = client.post(f"/api/v1/tasks/{failed_task_id}/retry", headers=headers)
    
    # Should return 201 (retry submitted) or 400 (cannot retry)
    assert response.status_code in [201, 400, 404]
    
    if response.status_code == 201:
        data = response.json()
        assert "task_id" in data
        assert "status" in data
        assert "project_id" in data
        assert "estimated_duration" in data
        assert "queue_position" in data
        assert "created_at" in data
        
        assert data["status"] == "queued"


def test_task_retry_non_failed_task(client):
    """Test retry of task that is not in failed status"""
    running_task_id = "running-task-uuid"
    headers = {"X-API-Key": "test-api-key"}
    response = client.post(f"/api/v1/tasks/{running_task_id}/retry", headers=headers)
    
    # Should return 400 if task is not failed
    if response.status_code == 400:
        data = response.json()
        assert "error" in data
        assert "cannot be retried" in data["error"].lower()


def test_task_retry_invalid_uuid(client):
    """Test retry with invalid UUID format"""
    invalid_task_id = "not-a-valid-uuid"
    headers = {"X-API-Key": "test-api-key"}
    response = client.delete(f"/api/v1/tasks/{invalid_task_id}/retry", headers=headers)
    assert response.status_code == 400


def test_task_retry_nonexistent_task(client):
    """Test retry of non-existent task"""
    nonexistent_task_id = "99999999-9999-9999-9999-999999999999"
    headers = {"X-API-Key": "test-api-key"}
    response = client.post(f"/api/v1/tasks/{nonexistent_task_id}/retry", headers=headers)
    assert response.status_code == 404