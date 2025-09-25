"""
Contract test for GET /api/v1/workers/status endpoint
This test MUST fail until the endpoint is implemented
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    return TestClient(app)


def test_workers_status_requires_auth(client):
    """Test that workers status requires API key"""
    response = client.get("/api/v1/workers/status")
    assert response.status_code == 401


def test_workers_status_response_structure(client):
    """Test workers status response structure"""
    headers = {"X-API-Key": "test-api-key"}
    response = client.get("/api/v1/workers/status", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "workers" in data
    assert "total_workers" in data
    assert "active_workers" in data
    assert "gpu_utilization" in data
    
    # Validate workers array
    assert isinstance(data["workers"], list)
    assert isinstance(data["total_workers"], int)
    assert isinstance(data["active_workers"], int)
    assert isinstance(data["gpu_utilization"], (int, float))
    
    # Validate GPU utilization range
    assert 0.0 <= data["gpu_utilization"] <= 1.0


def test_workers_status_worker_schema(client):
    """Test individual worker status schema"""
    headers = {"X-API-Key": "test-api-key"}
    response = client.get("/api/v1/workers/status", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        
        # If workers exist, validate their schema
        for worker in data["workers"]:
            assert "worker_id" in worker
            assert "worker_type" in worker
            assert "status" in worker
            assert "current_task_id" in worker  # Can be null
            assert "gpu_utilization" in worker
            assert "memory_usage" in worker
            assert "tasks_completed" in worker
            assert "last_heartbeat" in worker
            
            # Validate worker_type enum
            valid_types = ["gpu_heavy", "gpu_medium", "cpu_intensive"]
            assert worker["worker_type"] in valid_types
            
            # Validate status enum
            valid_statuses = ["active", "idle", "busy", "offline"]
            assert worker["status"] in valid_statuses
            
            # Validate numeric fields
            assert isinstance(worker["gpu_utilization"], (int, float))
            assert isinstance(worker["memory_usage"], int)
            assert isinstance(worker["tasks_completed"], int)
            assert 0.0 <= worker["gpu_utilization"] <= 1.0
            assert worker["memory_usage"] >= 0
            assert worker["tasks_completed"] >= 0


def test_workers_status_empty_workers(client):
    """Test response when no workers are available"""
    headers = {"X-API-Key": "test-api-key"}
    response = client.get("/api/v1/workers/status", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        
        # Even with no workers, structure should be valid
        assert data["total_workers"] >= 0
        assert data["active_workers"] >= 0
        assert len(data["workers"]) == data["total_workers"]
        
        # GPU utilization should be 0 if no workers
        if data["total_workers"] == 0:
            assert data["gpu_utilization"] == 0.0