"""
Contract test for GET /api/v1/tasks/{task_id}/status endpoint
This test MUST fail until the endpoint is implemented
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    return TestClient(app)


def test_task_status_requires_auth(client):
    """Test that task status requires API key"""
    task_id = "abc123-def456-ghi789"
    response = client.get(f"/api/v1/tasks/{task_id}/status")
    assert response.status_code == 401


def test_task_status_valid_id(client):
    """Test task status retrieval with valid task ID"""
    task_id = "abc123-def456-ghi789"
    headers = {"X-API-Key": "test-api-key"}
    response = client.get(f"/api/v1/tasks/{task_id}/status", headers=headers)
    
    # Should return either 200 (found) or 404 (not found)
    assert response.status_code in [200, 404]
    
    if response.status_code == 200:
        data = response.json()
        assert "task_id" in data
        assert "project_id" in data
        assert "status" in data
        assert "progress" in data
        assert "current_step" in data
        assert "result" in data  # Can be null
        assert "error" in data   # Can be null
        assert "started_at" in data  # Can be null
        assert "completed_at" in data  # Can be null
        
        # Validate task_id matches request
        assert data["task_id"] == task_id
        
        # Validate status enum
        valid_statuses = ["queued", "processing", "completed", "failed", "cancelled"]
        assert data["status"] in valid_statuses
        
        # Validate progress range
        assert 0.0 <= data["progress"] <= 1.0


def test_task_status_invalid_uuid_format(client):
    """Test task status with invalid UUID format"""
    invalid_task_id = "not-a-valid-uuid"
    headers = {"X-API-Key": "test-api-key"}
    response = client.get(f"/api/v1/tasks/{invalid_task_id}/status", headers=headers)
    assert response.status_code == 400


def test_task_status_response_schema_completed(client):
    """Test response schema for completed task"""
    # This would typically use a known completed task ID in integration tests
    # For contract test, we validate the schema structure
    task_id = "completed-task-uuid"
    headers = {"X-API-Key": "test-api-key"}
    response = client.get(f"/api/v1/tasks/{task_id}/status", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        
        # For completed tasks, result should have specific structure
        if data["status"] == "completed" and data["result"]:
            result = data["result"]
            assert "media_url" in result
            assert "payload_media_id" in result
            assert "metadata" in result
            
            # Validate metadata structure
            metadata = result["metadata"]
            assert isinstance(metadata, dict)


def test_task_status_response_schema_failed(client):
    """Test response schema for failed task"""
    task_id = "failed-task-uuid"
    headers = {"X-API-Key": "test-api-key"}
    response = client.get(f"/api/v1/tasks/{task_id}/status", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        
        # For failed tasks, error should be present
        if data["status"] == "failed":
            assert data["error"] is not None
            assert isinstance(data["error"], str)
            assert len(data["error"]) > 0