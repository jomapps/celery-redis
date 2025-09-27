"""
Integration tests for Brain Service communication
Tests the MCP WebSocket client and task integration
"""
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.clients.brain_client import (
    BrainServiceClient,
    BrainServiceConnectionError,
    BrainServiceTimeoutError
)
from app.tasks.base_task import BaseTaskWithBrain
from app.tasks.video_tasks import VideoGenerationTask
from app.tasks.image_tasks import ImageGenerationTask
from app.tasks.audio_tasks import AudioGenerationTask


class TestBrainServiceClient:
    """Test Brain Service WebSocket client functionality"""

    @pytest.fixture
    def brain_client(self):
        """Create brain service client for testing"""
        return BrainServiceClient("wss://brain.ft.tc", max_retries=1, timeout=5.0)

    @pytest.mark.asyncio
    async def test_connection_success(self, brain_client):
        """Test successful WebSocket connection"""
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_connect.return_value = mock_websocket

            await brain_client.connect()

            assert brain_client.connected is True
            assert brain_client.websocket == mock_websocket
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_failure_retry(self, brain_client):
        """Test connection failure and retry logic"""
        with patch('websockets.connect') as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")

            with pytest.raises(BrainServiceConnectionError):
                await brain_client.connect()

            # Should retry according to max_retries setting
            assert mock_connect.call_count == brain_client.max_retries

    @pytest.mark.asyncio
    async def test_store_task_result(self, brain_client):
        """Test storing task result in brain service"""
        with patch.object(brain_client, '_send_request') as mock_send:
            mock_send.return_value = {"id": "test-node-id"}

            result = await brain_client.store_task_result(
                task_id="test-task-123",
                task_type="video_generation",
                result={"status": "completed", "url": "https://example.com/video.mp4"},
                metadata={"quality": "high"}
            )

            assert result == "test-node-id"
            mock_send.assert_called_once_with("store_knowledge", {
                "knowledge_type": "task_result",
                "content": {
                    "task_id": "test-task-123",
                    "task_type": "video_generation",
                    "result": {"status": "completed", "url": "https://example.com/video.mp4"},
                    "timestamp": mock_send.call_args[0][1]["content"]["timestamp"],
                    "metadata": {"quality": "high"}
                }
            })

    @pytest.mark.asyncio
    async def test_search_similar_tasks(self, brain_client):
        """Test searching for similar tasks"""
        with patch.object(brain_client, '_send_request') as mock_send:
            mock_send.return_value = {
                "results": [
                    {"content": {"task_id": "similar-1", "result": {"quality": 0.9}}},
                    {"content": {"task_id": "similar-2", "result": {"quality": 0.8}}}
                ]
            }

            results = await brain_client.search_similar_tasks(
                task_description="video generation cinematic style",
                task_type="video_generation",
                limit=5
            )

            assert len(results) == 2
            assert results[0]["content"]["task_id"] == "similar-1"
            mock_send.assert_called_once_with("search_embeddings", {
                "query": "video generation cinematic style task_type:video_generation",
                "limit": 5
            })

    @pytest.mark.asyncio
    async def test_cache_and_retrieve_result(self, brain_client):
        """Test caching and retrieving cached results"""
        # Test caching
        with patch.object(brain_client, '_send_request') as mock_send:
            mock_send.return_value = {"id": "cache-node-id"}

            cache_success = await brain_client.cache_task_result(
                cache_key="test-cache-key",
                result={"processed_data": "example"},
                ttl_seconds=3600
            )

            assert cache_success is True

        # Test retrieval - cache hit
        with patch.object(brain_client, '_send_request') as mock_send:
            mock_send.return_value = {
                "results": [{
                    "content": {
                        "cache_key": "test-cache-key",
                        "result": {"processed_data": "example"},
                        "created_at": datetime.utcnow().isoformat(),
                        "ttl_seconds": 3600
                    }
                }]
            }

            cached_result = await brain_client.get_cached_result("test-cache-key")

            assert cached_result == {"processed_data": "example"}

        # Test retrieval - cache miss
        with patch.object(brain_client, '_send_request') as mock_send:
            mock_send.return_value = {"results": []}

            cached_result = await brain_client.get_cached_result("non-existent-key")

            assert cached_result is None

    @pytest.mark.asyncio
    async def test_health_check(self, brain_client):
        """Test brain service health check"""
        with patch.object(brain_client, '_send_request') as mock_send:
            mock_send.return_value = {"status": "ok"}

            health = await brain_client.health_check()

            assert health is True
            mock_send.assert_called_once_with("ping", {})

    @pytest.mark.asyncio
    async def test_request_timeout(self, brain_client):
        """Test request timeout handling"""
        with patch.object(brain_client, 'connect'):
            with patch('asyncio.wait_for') as mock_wait:
                mock_wait.side_effect = asyncio.TimeoutError()

                with pytest.raises(BrainServiceTimeoutError):
                    await brain_client._send_request("test_method", {})


class TestTaskIntegration:
    """Test task integration with brain service"""

    @pytest.fixture
    def mock_brain_client(self):
        """Create mock brain client for task testing"""
        client = AsyncMock()
        client.store_task_result.return_value = "node-123"
        client.store_task_context.return_value = "context-456"
        client.get_task_history.return_value = []
        client.search_similar_tasks.return_value = []
        client.get_cached_result.return_value = None
        client.cache_task_result.return_value = True
        return client

    def test_video_generation_task_brain_integration(self, mock_brain_client):
        """Test video generation task with brain service integration"""
        task = VideoGenerationTask()
        task.request = MagicMock()
        task.request.id = "test-video-task-123"
        task.request.started_at = datetime.utcnow()

        with patch.object(task, 'get_brain_client', return_value=mock_brain_client):
            with patch.object(task, 'run_async_in_sync') as mock_run_async:
                # Mock the async calls
                mock_run_async.side_effect = [
                    [],  # search_similar_tasks
                    "context-456",  # store_task_context
                    "node-123",  # store_task_result
                    True  # cache_result
                ]

                result = task.execute_task(
                    project_id="test-project",
                    scene_data={"scene_id": "scene-1", "style": "cinematic"},
                    video_params={"duration": 30, "resolution": "1920x1080"}
                )

                assert result["task_id"] == "test-video-task-123"
                assert result["project_id"] == "test-project"
                assert result["status"] == "completed"
                assert "video_url" in result
                assert "processing_metadata" in result

    def test_image_generation_task_brain_integration(self, mock_brain_client):
        """Test image generation task with brain service integration"""
        task = ImageGenerationTask()
        task.request = MagicMock()
        task.request.id = "test-image-task-456"

        with patch.object(task, 'get_brain_client', return_value=mock_brain_client):
            with patch.object(task, 'run_async_in_sync') as mock_run_async:
                mock_run_async.side_effect = [
                    [],  # search_similar_tasks
                    [],  # get_task_history
                    "context-789",  # store_task_context
                    "node-456",  # store_task_result
                ]

                result = task.execute_task(
                    project_id="test-project",
                    image_prompt="a beautiful landscape",
                    image_params={"width": 1024, "height": 1024, "style": "photorealistic"}
                )

                assert result["task_id"] == "test-image-task-456"
                assert result["project_id"] == "test-project"
                assert result["status"] == "completed"
                assert result["prompt"] == "a beautiful landscape"

    def test_audio_generation_task_brain_integration(self, mock_brain_client):
        """Test audio generation task with brain service integration"""
        task = AudioGenerationTask()
        task.request = MagicMock()
        task.request.id = "test-audio-task-789"

        with patch.object(task, 'get_brain_client', return_value=mock_brain_client):
            with patch.object(task, 'run_async_in_sync') as mock_run_async:
                mock_run_async.side_effect = [
                    [],  # search_similar_tasks
                    [],  # get_task_history
                    "context-321",  # store_task_context
                    "node-789",  # store_task_result
                ]

                result = task.execute_task(
                    project_id="test-project",
                    audio_prompt="epic orchestral music",
                    audio_params={"duration": 60, "style": "cinematic", "tempo": 120}
                )

                assert result["task_id"] == "test-audio-task-789"
                assert result["project_id"] == "test-project"
                assert result["status"] == "completed"
                assert result["prompt"] == "epic orchestral music"

    def test_base_task_failure_handling(self, mock_brain_client):
        """Test base task failure handling with brain service"""
        task = BaseTaskWithBrain()
        task.request = MagicMock()
        task.request.id = "test-failure-task"

        with patch.object(task, 'get_brain_client', return_value=mock_brain_client):
            with patch.object(task, 'run_async_in_sync') as mock_run_async:
                # Simulate task failure
                exc = Exception("Task processing failed")
                task_id = "test-failure-task"
                args = ("arg1", "arg2")
                kwargs = {"key": "value"}
                einfo = MagicMock()
                einfo.traceback = "mock traceback"

                task.on_failure(exc, task_id, args, kwargs, einfo)

                # Verify that failure context was stored
                mock_run_async.assert_called_once()
                assert mock_brain_client.store_task_context.called is False  # called through run_async_in_sync

    def test_base_task_success_handling(self, mock_brain_client):
        """Test base task success handling with brain service"""
        task = BaseTaskWithBrain()
        task.request = MagicMock()
        task.request.id = "test-success-task"

        with patch.object(task, 'get_brain_client', return_value=mock_brain_client):
            with patch.object(task, 'run_async_in_sync') as mock_run_async:
                # Simulate task success
                retval = {"status": "completed", "result": "success"}
                task_id = "test-success-task"
                args = ("arg1", "arg2")
                kwargs = {"key": "value"}

                task.on_success(retval, task_id, args, kwargs)

                # Verify that success context was stored
                mock_run_async.assert_called_once()

    def test_cache_optimization(self, mock_brain_client):
        """Test task caching optimization"""
        class TestCacheTask(BaseTaskWithBrain):
            def execute_task(self, *args, **kwargs):
                return {"result": "expensive_computation"}

        task = TestCacheTask()
        task.request = MagicMock()
        task.request.id = "test-cache-task"

        with patch.object(task, 'get_brain_client', return_value=mock_brain_client):
            with patch.object(task, 'run_async_in_sync') as mock_run_async:
                # First call - cache miss
                mock_run_async.side_effect = [
                    None,  # get_cached_result (miss)
                    [],   # search_similar_tasks
                    "node-id",  # store_task_result
                    True  # cache_result
                ]

                result1 = task.run("arg1", key="value1")
                assert result1["result"] == "expensive_computation"

                # Second call - cache hit
                mock_run_async.reset_mock()
                mock_run_async.side_effect = [
                    {"result": "expensive_computation"}  # get_cached_result (hit)
                ]

                result2 = task.run("arg1", key="value1")
                assert result2["result"] == "expensive_computation"

                # Verify cache hit prevented expensive computation
                assert mock_run_async.call_count == 1


class TestErrorHandling:
    """Test error handling and resilience"""

    @pytest.mark.asyncio
    async def test_brain_service_unavailable_graceful_degradation(self):
        """Test graceful degradation when brain service is unavailable"""
        client = BrainServiceClient("wss://invalid-url", max_retries=1)

        with patch('websockets.connect') as mock_connect:
            mock_connect.side_effect = Exception("Service unavailable")

            # Should raise connection error after retries
            with pytest.raises(BrainServiceConnectionError):
                await client.connect()

    def test_task_execution_continues_on_brain_service_failure(self, mock_brain_client):
        """Test that task execution continues even if brain service fails"""
        class TestResilientTask(BaseTaskWithBrain):
            def execute_task(self, *args, **kwargs):
                return {"result": "task_completed"}

        task = TestResilientTask()
        task.request = MagicMock()
        task.request.id = "test-resilient-task"

        # Mock brain service failure
        mock_brain_client.store_task_result.side_effect = Exception("Brain service down")

        with patch.object(task, 'get_brain_client', return_value=mock_brain_client):
            with patch.object(task, 'run_async_in_sync') as mock_run_async:
                # Brain service calls fail, but task should still complete
                mock_run_async.side_effect = [
                    None,  # get_cached_result fails
                    [],    # search_similar_tasks fails
                    None,  # store_task_result fails
                    False  # cache_result fails
                ]

                # Task should still complete successfully
                result = task.run("test_arg")
                assert result["result"] == "task_completed"


@pytest.mark.integration
class TestFullIntegration:
    """Integration tests requiring actual brain service (skip in CI)"""

    @pytest.mark.skip(reason="Requires running brain service")
    @pytest.mark.asyncio
    async def test_real_brain_service_connection(self):
        """Test actual connection to brain service (integration test)"""
        client = BrainServiceClient("wss://brain.ft.tc")

        try:
            async with client.connection():
                health = await client.health_check()
                assert health is True

                # Test storing and retrieving knowledge
                node_id = await client.store_task_result(
                    task_id="integration-test-123",
                    task_type="test_task",
                    result={"test": "data"},
                    metadata={"integration_test": True}
                )

                assert node_id is not None
                assert len(node_id) > 0

        except Exception as e:
            pytest.skip(f"Brain service not available: {e}")

    @pytest.mark.skip(reason="Requires running brain service")
    @pytest.mark.asyncio
    async def test_real_semantic_search(self):
        """Test actual semantic search functionality"""
        client = BrainServiceClient("wss://brain.ft.tc")

        try:
            async with client.connection():
                # Store some test data first
                await client.store_task_result(
                    task_id="search-test-1",
                    task_type="video_generation",
                    result={"style": "cinematic", "quality": 0.9},
                    metadata={"test": True}
                )

                # Search for similar tasks
                results = await client.search_similar_tasks(
                    task_description="cinematic video generation",
                    task_type="video_generation",
                    limit=5
                )

                assert isinstance(results, list)

        except Exception as e:
            pytest.skip(f"Brain service not available: {e}")