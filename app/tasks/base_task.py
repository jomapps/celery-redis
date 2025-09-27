"""
Base task class with brain service integration
Provides common functionality for all AI Movie tasks
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog
from celery import Task
from celery.exceptions import Retry

from ..clients.brain_client import BrainServiceClient, BrainServiceConnectionError
from ..config.settings import settings

logger = structlog.get_logger(__name__)


class BaseTaskWithBrain(Task, ABC):
    """
    Abstract base class for Celery tasks with brain service integration
    Provides knowledge graph storage, context queries, and result caching
    """

    def __init__(self):
        super().__init__()
        self._brain_client = None

    async def get_brain_client(self) -> BrainServiceClient:
        """Get or create brain service client connection"""
        if self._brain_client is None:
            self._brain_client = BrainServiceClient(
                brain_service_url=settings.brain_service_base_url,
                max_retries=3,
                timeout=60.0
            )
        return self._brain_client

    async def store_task_result_in_brain(self, task_id: str, task_type: str,
                                       result: Dict[str, Any], metadata: Dict[str, Any] = None) -> Optional[str]:
        """Store task result in brain service knowledge graph"""
        try:
            brain_client = await self.get_brain_client()
            async with brain_client.connection():
                node_id = await brain_client.store_task_result(
                    task_id=task_id,
                    task_type=task_type,
                    result=result,
                    metadata=metadata
                )
                logger.info("Stored task result in brain service",
                          task_id=task_id, node_id=node_id)
                return node_id
        except Exception as e:
            logger.error("Failed to store task result in brain service",
                        task_id=task_id, error=str(e))
            return None

    async def store_task_context_in_brain(self, task_id: str, context: Dict[str, Any]) -> Optional[str]:
        """Store task execution context in brain service"""
        try:
            brain_client = await self.get_brain_client()
            async with brain_client.connection():
                node_id = await brain_client.store_task_context(
                    task_id=task_id,
                    context=context
                )
                logger.info("Stored task context in brain service",
                          task_id=task_id, node_id=node_id)
                return node_id
        except Exception as e:
            logger.error("Failed to store task context in brain service",
                        task_id=task_id, error=str(e))
            return None

    async def get_task_history_from_brain(self, task_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve historical task results from brain service"""
        try:
            brain_client = await self.get_brain_client()
            async with brain_client.connection():
                history = await brain_client.get_task_history(
                    task_type=task_type,
                    limit=limit
                )
                logger.info("Retrieved task history from brain service",
                          task_type=task_type, count=len(history))
                return history
        except Exception as e:
            logger.error("Failed to retrieve task history from brain service",
                        task_type=task_type, error=str(e))
            return []

    async def get_task_context_from_brain(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve task context from brain service"""
        try:
            brain_client = await self.get_brain_client()
            async with brain_client.connection():
                context = await brain_client.get_task_context(task_id)
                if context:
                    logger.info("Retrieved task context from brain service", task_id=task_id)
                return context
        except Exception as e:
            logger.error("Failed to retrieve task context from brain service",
                        task_id=task_id, error=str(e))
            return None

    async def search_similar_tasks_in_brain(self, task_description: str, task_type: str = None,
                                          limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar tasks using brain service semantic search"""
        try:
            brain_client = await self.get_brain_client()
            async with brain_client.connection():
                similar_tasks = await brain_client.search_similar_tasks(
                    task_description=task_description,
                    task_type=task_type,
                    limit=limit
                )
                logger.info("Found similar tasks in brain service",
                          query=task_description, count=len(similar_tasks))
                return similar_tasks
        except Exception as e:
            logger.error("Failed to search similar tasks in brain service",
                        query=task_description, error=str(e))
            return []

    async def cache_result_in_brain(self, cache_key: str, result: Any, ttl_seconds: int = 3600) -> bool:
        """Cache task result in brain service for performance optimization"""
        try:
            brain_client = await self.get_brain_client()
            async with brain_client.connection():
                success = await brain_client.cache_task_result(
                    cache_key=cache_key,
                    result=result,
                    ttl_seconds=ttl_seconds
                )
                if success:
                    logger.info("Cached result in brain service", cache_key=cache_key)
                return success
        except Exception as e:
            logger.error("Failed to cache result in brain service",
                        cache_key=cache_key, error=str(e))
            return False

    async def get_cached_result_from_brain(self, cache_key: str) -> Optional[Any]:
        """Retrieve cached result from brain service"""
        try:
            brain_client = await self.get_brain_client()
            async with brain_client.connection():
                cached_result = await brain_client.get_cached_result(cache_key)
                if cached_result is not None:
                    logger.info("Cache hit in brain service", cache_key=cache_key)
                return cached_result
        except Exception as e:
            logger.error("Failed to retrieve cached result from brain service",
                        cache_key=cache_key, error=str(e))
            return None

    async def check_brain_service_health(self) -> bool:
        """Check if brain service is healthy and responsive"""
        try:
            brain_client = await self.get_brain_client()
            async with brain_client.connection():
                return await brain_client.health_check()
        except Exception as e:
            logger.warning("Brain service health check failed", error=str(e))
            return False

    def run_async_in_sync(self, coro):
        """Helper to run async code in synchronous Celery task context"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(coro)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails - store failure information in brain service"""
        try:
            failure_context = {
                "error": str(exc),
                "task_id": task_id,
                "args": args,
                "kwargs": kwargs,
                "failure_time": datetime.utcnow().isoformat(),
                "traceback": str(einfo.traceback)
            }

            # Store failure context asynchronously
            self.run_async_in_sync(
                self.store_task_context_in_brain(task_id, failure_context)
            )

        except Exception as e:
            logger.error("Failed to store task failure in brain service",
                        task_id=task_id, error=str(e))

    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds - store success information in brain service"""
        try:
            success_context = {
                "task_id": task_id,
                "success_time": datetime.utcnow().isoformat(),
                "result_summary": str(retval)[:1000],  # Truncate for storage
                "execution_args": args,
                "execution_kwargs": kwargs
            }

            # Store success context asynchronously
            self.run_async_in_sync(
                self.store_task_context_in_brain(task_id, success_context)
            )

        except Exception as e:
            logger.error("Failed to store task success in brain service",
                        task_id=task_id, error=str(e))

    @abstractmethod
    def execute_task(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Abstract method to be implemented by concrete task classes
        This method should contain the main task logic
        """
        pass

    def run(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Main task execution method that wraps the abstract execute_task method
        Provides brain service integration hooks
        """
        task_id = self.request.id
        task_type = self.__class__.__name__

        logger.info("Starting task execution", task_id=task_id, task_type=task_type)

        try:
            # Check if we have a cached result
            cache_key = f"task:{task_type}:{hash(str(args) + str(kwargs))}"
            cached_result = self.run_async_in_sync(
                self.get_cached_result_from_brain(cache_key)
            )

            if cached_result is not None:
                logger.info("Returning cached result", task_id=task_id)
                return cached_result

            # Get historical context for similar tasks
            similar_tasks = self.run_async_in_sync(
                self.search_similar_tasks_in_brain(
                    task_description=f"{task_type} {str(kwargs)}",
                    task_type=task_type,
                    limit=3
                )
            )

            # Execute the main task logic
            result = self.execute_task(*args, **kwargs)

            # Store result in brain service
            self.run_async_in_sync(
                self.store_task_result_in_brain(
                    task_id=task_id,
                    task_type=task_type,
                    result=result,
                    metadata={
                        "similar_tasks_count": len(similar_tasks),
                        "execution_time": datetime.utcnow().isoformat()
                    }
                )
            )

            # Cache the result for future use
            self.run_async_in_sync(
                self.cache_result_in_brain(cache_key, result, ttl_seconds=1800)  # 30 min cache
            )

            logger.info("Task execution completed successfully", task_id=task_id)
            return result

        except Exception as e:
            logger.error("Task execution failed", task_id=task_id, error=str(e))
            raise

        finally:
            # Cleanup brain client connection
            if self._brain_client:
                try:
                    self.run_async_in_sync(self._brain_client.disconnect())
                except Exception as e:
                    logger.warning("Failed to cleanup brain client", error=str(e))