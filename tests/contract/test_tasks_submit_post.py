"""
Contract test for POST /api/v1/tasks/submit endpoint
This test MUST fail until the endpoint is implemented
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture
def valid_task_request():
    """Valid task submission request"""
    return {
        "project_id": "detective_series_001",
        "task_type": "generate_video",
        "task_data": {
            "storyboard_images": [
                "https://example.com/frame1.jpg",
                "https://example.com/frame2.jpg"
            ],
            "scene_description": "Detective enters the dark alley",
            "camera_angle": "wide_shot",
            "lighting": "noir_dramatic"
        },
        "priority": 1,
        "callback_url": "https://main-app.com/api/webhooks/task-complete",
        "metadata": {
            "user_id": "user123",
            "agent_id": "video_generation_agent",
            "scene_id": "scene_005"
        }
    }


def test_task_submit_requires_auth(client, valid_task_request):
    """Test that task submission requires API key"""
    response = client.post("/api/v1/tasks/submit", json=valid_task_request)
    assert response.status_code == 401


def test_task_submit_with_auth(client, valid_task_request):
    """Test successful task submission with valid API key"""
    headers = {"X-API-Key": "test-api-key"}
    response = client.post("/api/v1/tasks/submit", json=valid_task_request, headers=headers)
    assert response.status_code == 201
    
    data = response.json()
    assert "task_id" in data
    assert "status" in data
    assert "project_id" in data
    assert "estimated_duration" in data
    assert "queue_position" in data
    assert "created_at" in data
    
    assert data["status"] == "queued"
    assert data["project_id"] == "detective_series_001"


def test_task_submit_invalid_project_id(client):
    """Test validation of project_id format"""
    invalid_request = {
        "project_id": "invalid project id with spaces!",
        "task_type": "generate_video",
        "task_data": {}
    }
    headers = {"X-API-Key": "test-api-key"}
    response = client.post("/api/v1/tasks/submit", json=invalid_request, headers=headers)
    assert response.status_code == 400


def test_task_submit_invalid_task_type(client):
    """Test validation of task_type enum"""
    invalid_request = {
        "project_id": "detective_series_001",
        "task_type": "invalid_task_type",
        "task_data": {}
    }
    headers = {"X-API-Key": "test-api-key"}
    response = client.post("/api/v1/tasks/submit", json=invalid_request, headers=headers)
    assert response.status_code == 400


def test_task_submit_missing_required_fields(client):
    """Test validation of required fields"""
    incomplete_request = {
        "project_id": "detective_series_001"
        # Missing task_type and task_data
    }
    headers = {"X-API-Key": "test-api-key"}
    response = client.post("/api/v1/tasks/submit", json=incomplete_request, headers=headers)
    assert response.status_code == 400


def test_task_submit_priority_validation(client, valid_task_request):
    """Test priority field validation"""
    # Valid priority values: 1, 2, 3
    for priority in [1, 2, 3]:
        valid_task_request["priority"] = priority
        headers = {"X-API-Key": "test-api-key"}
        response = client.post("/api/v1/tasks/submit", json=valid_task_request, headers=headers)
        assert response.status_code == 201
    
    # Invalid priority value
    valid_task_request["priority"] = 4
    response = client.post("/api/v1/tasks/submit", json=valid_task_request, headers=headers)
    assert response.status_code == 400