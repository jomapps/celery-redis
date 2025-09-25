"""
Contract test for GET /api/v1/projects/{project_id}/tasks endpoint
This test MUST fail until the endpoint is implemented
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    return TestClient(app)


def test_project_tasks_requires_auth(client):
    """Test that project tasks listing requires API key"""
    project_id = "detective_series_001"
    response = client.get(f"/api/v1/projects/{project_id}/tasks")
    assert response.status_code == 401


def test_project_tasks_basic_listing(client):
    """Test basic project tasks listing"""
    project_id = "detective_series_001"
    headers = {"X-API-Key": "test-api-key"}
    response = client.get(f"/api/v1/projects/{project_id}/tasks", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "tasks" in data
    assert "pagination" in data
    
    # Validate pagination structure
    pagination = data["pagination"]
    assert "page" in pagination
    assert "limit" in pagination
    assert "total" in pagination
    assert "total_pages" in pagination
    
    # Validate tasks array
    assert isinstance(data["tasks"], list)


def test_project_tasks_pagination_params(client):
    """Test pagination parameters"""
    project_id = "detective_series_001"
    headers = {"X-API-Key": "test-api-key"}
    
    # Test with page and limit parameters
    response = client.get(
        f"/api/v1/projects/{project_id}/tasks?page=2&limit=10", 
        headers=headers
    )
    assert response.status_code == 200
    
    data = response.json()
    pagination = data["pagination"]
    assert pagination["page"] == 2
    assert pagination["limit"] == 10


def test_project_tasks_status_filter(client):
    """Test filtering by task status"""
    project_id = "detective_series_001"
    headers = {"X-API-Key": "test-api-key"}
    
    # Test each valid status filter
    valid_statuses = ["queued", "processing", "completed", "failed", "cancelled"]
    for status in valid_statuses:
        response = client.get(
            f"/api/v1/projects/{project_id}/tasks?status={status}",
            headers=headers
        )
        assert response.status_code == 200


def test_project_tasks_type_filter(client):
    """Test filtering by task type"""
    project_id = "detective_series_001"
    headers = {"X-API-Key": "test-api-key"}
    
    # Test each valid task type filter
    valid_types = ["generate_video", "generate_image", "process_audio", "render_animation"]
    for task_type in valid_types:
        response = client.get(
            f"/api/v1/projects/{project_id}/tasks?task_type={task_type}",
            headers=headers
        )
        assert response.status_code == 200


def test_project_tasks_invalid_project_id(client):
    """Test with invalid project ID format"""
    invalid_project_id = "invalid project id!"
    headers = {"X-API-Key": "test-api-key"}
    response = client.get(f"/api/v1/projects/{invalid_project_id}/tasks", headers=headers)
    assert response.status_code == 400


def test_project_tasks_pagination_limits(client):
    """Test pagination limit validation"""
    project_id = "detective_series_001"
    headers = {"X-API-Key": "test-api-key"}
    
    # Test maximum limit (should be 100)
    response = client.get(
        f"/api/v1/projects/{project_id}/tasks?limit=101",
        headers=headers
    )
    assert response.status_code == 400
    
    # Test valid limit
    response = client.get(
        f"/api/v1/projects/{project_id}/tasks?limit=100",
        headers=headers
    )
    assert response.status_code == 200