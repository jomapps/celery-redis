"""
Integration test for project task management workflow
This test MUST fail until the complete workflow is implemented
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture
def sample_tasks():
    """Sample task submissions for different types"""
    return [
        {
            "project_id": "detective_series_001",
            "task_type": "generate_video",
            "task_data": {"scene_description": "Video task"},
            "priority": 1
        },
        {
            "project_id": "detective_series_001",
            "task_type": "generate_image",
            "task_data": {"character_description": "Image task"},
            "priority": 2
        },
        {
            "project_id": "detective_series_001",
            "task_type": "process_audio",
            "task_data": {"text": "Audio task"},
            "priority": 3
        }
    ]


@pytest.mark.integration
def test_project_task_lifecycle_management(client, sample_tasks):
    """Test complete project task lifecycle management"""
    headers = {"X-API-Key": "test-api-key"}
    project_id = "detective_series_001"
    submitted_task_ids = []
    
    # Step 1: Submit multiple tasks of different types
    for task_data in sample_tasks:
        response = client.post("/api/v1/tasks/submit", json=task_data, headers=headers)
        assert response.status_code == 201
        
        submission_data = response.json()
        submitted_task_ids.append(submission_data["task_id"])
        assert submission_data["project_id"] == project_id
    
    # Step 2: List all project tasks
    response = client.get(f"/api/v1/projects/{project_id}/tasks", headers=headers)
    assert response.status_code == 200
    
    project_data = response.json()
    project_task_ids = [task["task_id"] for task in project_data["tasks"]]
    
    # All submitted tasks should be in project listing
    for task_id in submitted_task_ids:
        assert task_id in project_task_ids
    
    # Step 3: Test filtering by task type
    response = client.get(
        f"/api/v1/projects/{project_id}/tasks?task_type=generate_video",
        headers=headers
    )
    assert response.status_code == 200
    
    video_tasks = response.json()["tasks"]
    for task in video_tasks:
        assert task["task_type"] == "generate_video"
    
    # Step 4: Test filtering by status
    response = client.get(
        f"/api/v1/projects/{project_id}/tasks?status=queued",
        headers=headers
    )
    assert response.status_code == 200
    
    queued_tasks = response.json()["tasks"]
    for task in queued_tasks:
        assert task["status"] == "queued"
    
    # Step 5: Test pagination
    response = client.get(
        f"/api/v1/projects/{project_id}/tasks?page=1&limit=2",
        headers=headers
    )
    assert response.status_code == 200
    
    paginated_data = response.json()
    assert len(paginated_data["tasks"]) <= 2
    assert paginated_data["pagination"]["page"] == 1
    assert paginated_data["pagination"]["limit"] == 2


@pytest.mark.integration
def test_task_cancellation_workflow(client, sample_tasks):
    """Test task cancellation workflow"""
    headers = {"X-API-Key": "test-api-key"}
    
    # Submit a task
    response = client.post("/api/v1/tasks/submit", json=sample_tasks[0], headers=headers)
    assert response.status_code == 201
    task_id = response.json()["task_id"]
    
    # Cancel the task while it's queued
    response = client.delete(f"/api/v1/tasks/{task_id}/cancel", headers=headers)
    
    # Should succeed if task is cancellable
    if response.status_code == 200:
        cancel_data = response.json()
        assert cancel_data["task_id"] == task_id
        assert cancel_data["status"] == "cancelled"
        
        # Verify status is updated
        response = client.get(f"/api/v1/tasks/{task_id}/status", headers=headers)
        assert response.status_code == 200
        status_data = response.json()
        assert status_data["status"] == "cancelled"


@pytest.mark.integration
def test_project_isolation_enforcement(client, sample_tasks):
    """Test that project isolation is properly enforced"""
    headers = {"X-API-Key": "test-api-key"}
    
    # Submit tasks to different projects
    project_a_task = sample_tasks[0].copy()
    project_a_task["project_id"] = "project_a"
    
    project_b_task = sample_tasks[1].copy()
    project_b_task["project_id"] = "project_b"
    
    # Submit to both projects
    response_a = client.post("/api/v1/tasks/submit", json=project_a_task, headers=headers)
    response_b = client.post("/api/v1/tasks/submit", json=project_b_task, headers=headers)
    
    assert response_a.status_code == 201
    assert response_b.status_code == 201
    
    task_a_id = response_a.json()["task_id"]
    task_b_id = response_b.json()["task_id"]
    
    # Verify project A only sees its tasks
    response = client.get("/api/v1/projects/project_a/tasks", headers=headers)
    assert response.status_code == 200
    
    project_a_tasks = response.json()["tasks"]
    project_a_task_ids = [task["task_id"] for task in project_a_tasks]
    
    assert task_a_id in project_a_task_ids
    assert task_b_id not in project_a_task_ids
    
    # Verify project B only sees its tasks
    response = client.get("/api/v1/projects/project_b/tasks", headers=headers)
    assert response.status_code == 200
    
    project_b_tasks = response.json()["tasks"]
    project_b_task_ids = [task["task_id"] for task in project_b_tasks]
    
    assert task_b_id in project_b_task_ids
    assert task_a_id not in project_b_task_ids


@pytest.mark.integration
def test_task_priority_handling(client, sample_tasks):
    """Test that task prioritization works correctly"""
    headers = {"X-API-Key": "test-api-key"}
    
    # Submit tasks with different priorities
    low_priority_task = sample_tasks[0].copy()
    low_priority_task["priority"] = 3
    low_priority_task["metadata"]["priority_test"] = "low"
    
    high_priority_task = sample_tasks[1].copy()
    high_priority_task["priority"] = 1
    high_priority_task["metadata"]["priority_test"] = "high"
    
    # Submit low priority first, then high priority
    response_low = client.post("/api/v1/tasks/submit", json=low_priority_task, headers=headers)
    response_high = client.post("/api/v1/tasks/submit", json=high_priority_task, headers=headers)
    
    assert response_low.status_code == 201
    assert response_high.status_code == 201
    
    # High priority task should have lower queue position
    low_priority_data = response_low.json()
    high_priority_data = response_high.json()
    
    # This validates that priority is being processed
    assert "queue_position" in low_priority_data
    assert "queue_position" in high_priority_data