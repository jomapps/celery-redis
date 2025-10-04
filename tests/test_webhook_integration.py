"""
Test webhook callback functionality
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from app.utils.webhook import (
    send_webhook_async,
    send_webhook_sync,
    build_success_webhook_payload,
    build_failure_webhook_payload
)


class TestWebhookPayloadBuilders:
    """Test webhook payload builder functions"""
    
    def test_build_success_webhook_payload_basic(self):
        """Test building basic success webhook payload"""
        payload = build_success_webhook_payload(
            task_id="test-task-123",
            project_id="test-project",
            result={"media_url": "https://example.com/video.mp4"}
        )
        
        assert payload["task_id"] == "test-task-123"
        assert payload["project_id"] == "test-project"
        assert payload["status"] == "completed"
        assert payload["result"]["media_url"] == "https://example.com/video.mp4"
        assert "completed_at" in payload
    
    def test_build_success_webhook_payload_with_metadata(self):
        """Test building success webhook payload with metadata"""
        payload = build_success_webhook_payload(
            task_id="test-task-123",
            project_id="test-project",
            result={"media_url": "https://example.com/video.mp4"},
            processing_time=45.2,
            metadata={"user_id": "user-123", "testResultId": "result-456"}
        )
        
        assert payload["processing_time"] == 45.2
        assert payload["metadata"]["user_id"] == "user-123"
        assert payload["metadata"]["testResultId"] == "result-456"
    
    def test_build_failure_webhook_payload_basic(self):
        """Test building basic failure webhook payload"""
        payload = build_failure_webhook_payload(
            task_id="test-task-123",
            project_id="test-project",
            error="Task execution failed"
        )
        
        assert payload["task_id"] == "test-task-123"
        assert payload["project_id"] == "test-project"
        assert payload["status"] == "failed"
        assert payload["error"] == "Task execution failed"
        assert "failed_at" in payload
    
    def test_build_failure_webhook_payload_with_traceback(self):
        """Test building failure webhook payload with traceback"""
        traceback = "Traceback (most recent call last):\n  File test.py, line 10"
        payload = build_failure_webhook_payload(
            task_id="test-task-123",
            project_id="test-project",
            error="Task execution failed",
            traceback=traceback,
            metadata={"retry_count": 3}
        )
        
        assert payload["traceback"] == traceback
        assert payload["metadata"]["retry_count"] == 3


class TestWebhookSending:
    """Test webhook sending functionality"""
    
    @pytest.mark.asyncio
    async def test_send_webhook_async_success(self):
        """Test successful webhook sending"""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock successful response
            mock_response = Mock()
            mock_response.status_code = 200
            
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            payload = {"task_id": "test-123", "status": "completed"}
            result = await send_webhook_async(
                "https://example.com/webhook",
                payload
            )
            
            assert result is True
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_webhook_async_retry_on_failure(self):
        """Test webhook retry logic on failure"""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock failed response
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            payload = {"task_id": "test-123", "status": "completed"}
            result = await send_webhook_async(
                "https://example.com/webhook",
                payload,
                max_retries=2
            )
            
            assert result is False
            assert mock_post.call_count == 2  # Should retry
    
    @pytest.mark.asyncio
    async def test_send_webhook_async_no_url(self):
        """Test webhook sending with no URL"""
        result = await send_webhook_async(
            "",
            {"task_id": "test-123"}
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_webhook_async_timeout(self):
        """Test webhook timeout handling"""
        with patch('httpx.AsyncClient') as mock_client:
            import httpx
            
            # Mock timeout exception
            mock_post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            payload = {"task_id": "test-123", "status": "completed"}
            result = await send_webhook_async(
                "https://example.com/webhook",
                payload,
                max_retries=2
            )
            
            assert result is False
            assert mock_post.call_count == 2  # Should retry
    
    def test_send_webhook_sync(self):
        """Test synchronous webhook sending wrapper"""
        with patch('app.utils.webhook.send_webhook_async') as mock_async:
            # Mock async function
            async def mock_send(*args, **kwargs):
                return True
            
            mock_async.return_value = mock_send()
            
            payload = {"task_id": "test-123", "status": "completed"}
            result = send_webhook_sync(
                "https://example.com/webhook",
                payload
            )
            
            # The sync wrapper should call the async function
            mock_async.assert_called_once()


class TestWebhookIntegrationWithTasks:
    """Test webhook integration with Celery tasks"""
    
    @patch('app.tasks.base_task.send_webhook_sync')
    def test_task_success_sends_webhook(self, mock_send_webhook):
        """Test that task success triggers webhook"""
        from app.tasks.base_task import BaseTaskWithBrain

        # Create a concrete implementation for testing
        class TestTask(BaseTaskWithBrain):
            def execute_task(self, *args, **kwargs):
                return {"result": "success"}

        task = TestTask()

        # Mock the brain service methods
        with patch.object(task, 'run_async_in_sync'):
            # Simulate on_success callback
            task.on_success(
                retval={"media_url": "https://example.com/video.mp4"},
                task_id="test-task-123",
                args=(),
                kwargs={
                    "project_id": "test-project",
                    "callback_url": "https://example.com/webhook"
                }
            )

        # Verify webhook was sent
        mock_send_webhook.assert_called_once()
        call_args = mock_send_webhook.call_args
        assert call_args[0][0] == "https://example.com/webhook"

        payload = call_args[0][1]
        assert payload["task_id"] == "test-task-123"
        assert payload["status"] == "completed"
        assert payload["project_id"] == "test-project"
    
    @patch('app.tasks.base_task.send_webhook_sync')
    def test_task_failure_sends_webhook(self, mock_send_webhook):
        """Test that task failure triggers webhook"""
        from app.tasks.base_task import BaseTaskWithBrain

        # Create a concrete implementation for testing
        class TestTask(BaseTaskWithBrain):
            def execute_task(self, *args, **kwargs):
                raise Exception("Task failed")

        task = TestTask()

        # Mock the brain service methods
        with patch.object(task, 'run_async_in_sync'):
            # Simulate on_failure callback
            exc = Exception("Task execution failed")
            einfo = Mock()
            einfo.traceback = "Traceback info here"

            task.on_failure(
                exc=exc,
                task_id="test-task-123",
                args=(),
                kwargs={
                    "project_id": "test-project",
                    "callback_url": "https://example.com/webhook"
                },
                einfo=einfo
            )

        # Verify webhook was sent
        mock_send_webhook.assert_called_once()
        call_args = mock_send_webhook.call_args
        assert call_args[0][0] == "https://example.com/webhook"

        payload = call_args[0][1]
        assert payload["task_id"] == "test-task-123"
        assert payload["status"] == "failed"
        assert payload["project_id"] == "test-project"
        assert "Task execution failed" in payload["error"]
    
    @patch('app.tasks.base_task.send_webhook_sync')
    def test_task_success_no_webhook_if_no_url(self, mock_send_webhook):
        """Test that no webhook is sent if callback_url is not provided"""
        from app.tasks.base_task import BaseTaskWithBrain

        class TestTask(BaseTaskWithBrain):
            def execute_task(self, *args, **kwargs):
                return {"result": "success"}

        task = TestTask()

        # Mock the brain service methods
        with patch.object(task, 'run_async_in_sync'):
            # Simulate on_success callback WITHOUT callback_url
            task.on_success(
                retval={"media_url": "https://example.com/video.mp4"},
                task_id="test-task-123",
                args=(),
                kwargs={"project_id": "test-project"}  # No callback_url
            )

        # Verify webhook was NOT sent
        mock_send_webhook.assert_not_called()

