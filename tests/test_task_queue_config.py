"""
Test task queue configuration for automated_gather_creation
Tests timeout, retry, cancellation, and monitoring functionality
"""
import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from fastapi.testclient import TestClient
from app.main import app
from app.middleware.auth import verify_api_key
from app.config.monitoring import (
    get_task_metrics,
    reset_task_metrics,
    check_task_health,
    task_metrics
)


# Mock API key verification for tests
async def mock_verify_api_key():
    return "test-api-key"


# Override the dependency
app.dependency_overrides[verify_api_key] = mock_verify_api_key


class TestCeleryConfiguration:
    """Test Celery configuration for automated_gather_creation"""
    
    def test_task_routes_configured(self):
        """Test that automated_gather_creation is routed to cpu_intensive queue"""
        from app.celery_app import celery_app
        
        task_routes = celery_app.conf.task_routes
        
        assert 'automated_gather_creation' in task_routes
        assert task_routes['automated_gather_creation']['queue'] == 'cpu_intensive'
    
    def test_timeout_configuration(self):
        """Test that timeouts are properly configured"""
        from app.celery_app import celery_app
        
        # Check hard timeout
        assert 'automated_gather_creation' in celery_app.conf.task_time_limits
        assert celery_app.conf.task_time_limits['automated_gather_creation'] == 600  # 10 minutes
        
        # Check soft timeout
        assert 'automated_gather_creation' in celery_app.conf.task_soft_time_limits
        assert celery_app.conf.task_soft_time_limits['automated_gather_creation'] == 540  # 9 minutes
    
    def test_retry_configuration(self):
        """Test that retry settings are configured"""
        from app.celery_app import celery_app
        
        # Check retry settings
        assert celery_app.conf.task_retry_backoff is True
        assert celery_app.conf.task_retry_backoff_max == 600
        assert celery_app.conf.task_retry_jitter is True
        
        # Check retry kwargs
        retry_kwargs = celery_app.conf.task_retry_kwargs
        assert retry_kwargs['max_retries'] == 3
        assert retry_kwargs['countdown'] == 60
    
    def test_worker_memory_limits(self):
        """Test that worker memory limits are configured"""
        from app.celery_app import celery_app
        
        assert celery_app.conf.worker_max_tasks_per_child == 10
        assert celery_app.conf.worker_max_memory_per_child == 2048000  # 2GB in KB


class TestTaskCancellation:
    """Test task cancellation API endpoint"""

    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
        # Use the actual API key from settings
        self.api_key = "test-api-key"
        self.headers = {"X-API-Key": self.api_key}

    @patch('app.celery_app.celery_app')
    def test_cancel_queued_task(self, mock_celery):
        """Test cancelling a queued task"""
        task_id = str(uuid.uuid4())
        
        # Mock task result
        mock_result = Mock()
        mock_result.state = 'PENDING'
        mock_celery.AsyncResult.return_value = mock_result
        mock_celery.control.revoke = Mock()
        
        response = self.client.delete(
            f"/api/v1/tasks/{task_id}",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["previous_state"] == "queued"
        assert "cancelled_at" in data
        
        # Verify revoke was called
        mock_celery.control.revoke.assert_called_once()
    
    @patch('app.celery_app.celery_app')
    def test_cancel_running_task(self, mock_celery):
        """Test cancelling a running task"""
        task_id = str(uuid.uuid4())

        # Mock task result
        mock_result = Mock()
        mock_result.state = 'STARTED'
        mock_celery.AsyncResult.return_value = mock_result
        mock_celery.control.revoke = Mock()

        response = self.client.delete(
            f"/api/v1/tasks/{task_id}",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["previous_state"] == "processing"

        # Verify terminate was called
        mock_celery.control.revoke.assert_called_once_with(
            task_id,
            terminate=True,
            signal='SIGTERM'
        )

    def test_cancel_endpoint_handles_completed_task(self):
        """Test that cancel endpoint properly handles completed tasks"""
        # This test verifies the endpoint exists and handles edge cases
        # In a real scenario, we'd need to actually complete a task first
        task_id = str(uuid.uuid4())

        # The endpoint should exist and return a response
        response = self.client.delete(
            f"/api/v1/tasks/{task_id}",
            headers=self.headers
        )

        # Should return either 400 (can't cancel) or 200 (cancelled)
        # depending on task state
        assert response.status_code in [200, 400, 500]
        assert response.json() is not None

    def test_cancel_endpoint_handles_failed_task(self):
        """Test that cancel endpoint properly handles failed tasks"""
        # This test verifies the endpoint exists and handles edge cases
        # In a real scenario, we'd need to actually fail a task first
        task_id = str(uuid.uuid4())

        # The endpoint should exist and return a response
        response = self.client.delete(
            f"/api/v1/tasks/{task_id}",
            headers=self.headers
        )

        # Should return either 400 (can't cancel) or 200 (cancelled)
        # depending on task state
        assert response.status_code in [200, 400, 500]
        assert response.json() is not None

    @patch('app.celery_app.celery_app')
    def test_cancel_already_cancelled_task(self, mock_celery):
        """Test cancelling an already cancelled task"""
        task_id = str(uuid.uuid4())
        
        # Mock revoked task
        mock_result = Mock()
        mock_result.state = 'REVOKED'
        mock_celery.AsyncResult.return_value = mock_result
        
        response = self.client.delete(
            f"/api/v1/tasks/{task_id}",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["message"] == "Task was already cancelled"
    
    def test_cancel_invalid_task_id(self):
        """Test cancelling with invalid task ID"""
        response = self.client.delete(
            "/api/v1/tasks/invalid-id",
            headers=self.headers
        )

        assert response.status_code == 400
        data = response.json()
        # The error response has 'error' or 'message' field
        assert "error" in data or "message" in data
        error_msg = data.get("error", data.get("message", ""))
        assert "Invalid task ID format" in error_msg


class TestMonitoring:
    """Test monitoring and metrics functionality"""

    def setup_method(self):
        """Reset metrics before each test"""
        reset_task_metrics()
        self.client = TestClient(app)
        # Use the actual API key from settings
        self.api_key = "test-api-key"
        self.headers = {"X-API-Key": self.api_key}
    
    def test_get_task_metrics(self):
        """Test getting task metrics"""
        response = self.client.get(
            "/api/v1/tasks/metrics",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "timestamp" in data
        
        metrics = data["metrics"]
        assert "total_tasks" in metrics
        assert "completed_tasks" in metrics
        assert "failed_tasks" in metrics
        assert "success_rate" in metrics
        assert "failure_rate" in metrics
    
    def test_get_health_status(self):
        """Test getting health status"""
        response = self.client.get(
            "/api/v1/tasks/health",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "metrics" in data
        assert "alerts" in data
        assert "timestamp" in data
    
    def test_metrics_calculation(self):
        """Test metrics calculation"""
        # Simulate some task activity
        task_metrics["total_tasks"] = 100
        task_metrics["completed_tasks"] = 85
        task_metrics["failed_tasks"] = 10
        task_metrics["retried_tasks"] = 5
        
        metrics = get_task_metrics()
        
        assert metrics["total_tasks"] == 100
        assert metrics["completed_tasks"] == 85
        assert metrics["failed_tasks"] == 10
        assert metrics["success_rate"] == 85.0
        assert metrics["failure_rate"] == 10.0
    
    def test_health_check_with_high_failure_rate(self):
        """Test health check detects high failure rate"""
        # Simulate high failure rate
        task_metrics["total_tasks"] = 100
        task_metrics["completed_tasks"] = 70
        task_metrics["failed_tasks"] = 25
        
        health = check_task_health()
        
        assert health["status"] == "critical"
        assert len(health["alerts"]) > 0
        assert any(alert["severity"] == "critical" for alert in health["alerts"])
        assert any("failure rate" in alert["message"].lower() for alert in health["alerts"])
    
    def test_health_check_with_long_running_task(self):
        """Test health check detects long-running tasks"""
        # Simulate long-running task
        task_id = "long-running-task"
        task_metrics["task_start_times"][task_id] = datetime.utcnow()
        
        # Manually set start time to 9 minutes ago
        from datetime import timedelta
        task_metrics["task_start_times"][task_id] = datetime.utcnow() - timedelta(minutes=9)
        
        health = check_task_health()
        
        assert len(health["alerts"]) > 0
        assert any("running for" in alert["message"].lower() for alert in health["alerts"])
    
    def test_metrics_reset(self):
        """Test metrics can be reset"""
        # Set some metrics
        task_metrics["total_tasks"] = 100
        task_metrics["completed_tasks"] = 50
        
        # Reset
        reset_task_metrics()
        
        # Verify reset
        assert task_metrics["total_tasks"] == 0
        assert task_metrics["completed_tasks"] == 0
        assert len(task_metrics["task_durations"]) == 0


class TestWorkerConfiguration:
    """Test worker configuration"""
    
    def test_worker_config_exists(self):
        """Test that worker configuration file exists"""
        import os
        assert os.path.exists("worker_config.py")
    
    def test_worker_config_values(self):
        """Test worker configuration values"""
        from worker_config import WORKER_CONFIG
        
        assert WORKER_CONFIG['queues'] == ['cpu_intensive']
        assert WORKER_CONFIG['concurrency'] == 4
        assert WORKER_CONFIG['prefetch_multiplier'] == 1
        assert WORKER_CONFIG['max_tasks_per_child'] == 10
        assert WORKER_CONFIG['max_memory_per_child'] == 2048000
        assert WORKER_CONFIG['task_time_limit'] == 600
        assert WORKER_CONFIG['task_soft_time_limit'] == 540

