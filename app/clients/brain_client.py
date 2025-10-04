"""
Brain Service Client for Celery-Redis Task Service
Implements MCP WebSocket client with task-specific features for knowledge graph storage
"""
import asyncio
import websockets
import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import uuid
import structlog
from contextlib import asynccontextmanager

logger = structlog.get_logger(__name__)

class BrainServiceConnectionError(Exception):
    """Raised when brain service connection fails"""
    pass

class BrainServiceTimeoutError(Exception):
    """Raised when brain service request times out"""
    pass

class BrainServiceClient:
    """
    Enhanced Brain Service Client for Celery task integration
    Provides knowledge graph storage for task results and context queries
    """

    def __init__(self, brain_service_url: str, max_retries: int = 3, timeout: float = 30.0):
        self.base_url = brain_service_url
        self.ws_url = brain_service_url.replace('https://', 'wss://').replace('http://', 'ws://') + '/mcp'
        self.websocket = None
        self.request_id = 0
        self.pending_requests = {}
        self.max_retries = max_retries
        self.timeout = timeout
        self.connected = False
        self._listener_task = None

    async def connect(self):
        """Establish WebSocket connection to brain service with retry logic"""
        retry_count = 0
        last_error = None

        while retry_count < self.max_retries:
            try:
                logger.info("Attempting to connect to brain service",
                          url=self.ws_url, attempt=retry_count + 1)

                self.websocket = await websockets.connect(
                    self.ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10
                )

                self.connected = True
                logger.info("Successfully connected to brain service")

                # Start listening for responses
                self._listener_task = asyncio.create_task(self._listen_for_responses())
                return

            except Exception as e:
                retry_count += 1
                last_error = e
                logger.warning("Failed to connect to brain service",
                             attempt=retry_count, error=str(e))

                if retry_count < self.max_retries:
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff

        raise BrainServiceConnectionError(f"Failed to connect after {self.max_retries} attempts: {last_error}")

    async def _listen_for_responses(self):
        """Listen for WebSocket responses with error handling"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    request_id = data.get("id")

                    if request_id in self.pending_requests:
                        future = self.pending_requests.pop(request_id)
                        if not future.cancelled():
                            if "error" in data:
                                future.set_exception(Exception(f"Brain service error: {data['error']}"))
                            else:
                                future.set_result(data)

                except json.JSONDecodeError:
                    logger.warning("Received invalid JSON from brain service", message=message)
                except Exception as e:
                    logger.error("Error processing brain service message", error=str(e))

        except websockets.exceptions.ConnectionClosed:
            logger.warning("Brain service connection closed")
            self.connected = False
        except Exception as e:
            logger.error("WebSocket listener error", error=str(e))
            self.connected = False

    async def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send MCP request with retry logic and timeout handling"""
        if not self.connected or not self.websocket:
            await self.connect()

        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/call",
            "params": {
                "name": method,
                "arguments": params
            }
        }

        # Create future for response
        future = asyncio.Future()
        self.pending_requests[self.request_id] = future

        try:
            await self.websocket.send(json.dumps(request))
            logger.debug("Sent brain service request", method=method, request_id=self.request_id)

            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=self.timeout)
            result = response.get("result", {})

            logger.debug("Received brain service response", method=method, request_id=self.request_id)
            return result

        except asyncio.TimeoutError:
            logger.error("Brain service request timed out", method=method, request_id=self.request_id)
            self.pending_requests.pop(self.request_id, None)
            raise BrainServiceTimeoutError(f"Request {self.request_id} timed out")
        except Exception as e:
            logger.error("Brain service request failed", method=method, error=str(e))
            self.pending_requests.pop(self.request_id, None)
            raise

    # Task-specific methods for celery integration

    async def store_task_result(self, task_id: str, task_type: str, result: Dict[str, Any],
                               metadata: Dict[str, Any] = None) -> str:
        """Store task execution result in knowledge graph"""
        content = {
            "task_id": task_id,
            "task_type": task_type,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }

        params = {
            "knowledge_type": "task_result",
            "content": content
        }

        try:
            result = await self._send_request("store_knowledge", params)
            node_id = result.get("id", "")
            logger.info("Stored task result in brain service",
                       task_id=task_id, node_id=node_id)
            return node_id
        except Exception as e:
            logger.error("Failed to store task result", task_id=task_id, error=str(e))
            raise

    async def store_task_context(self, task_id: str, context: Dict[str, Any]) -> str:
        """Store task execution context for future reference"""
        content = {
            "task_id": task_id,
            "context": context,
            "timestamp": datetime.utcnow().isoformat()
        }

        params = {
            "knowledge_type": "task_context",
            "content": content
        }

        try:
            result = await self._send_request("store_knowledge", params)
            node_id = result.get("id", "")
            logger.info("Stored task context in brain service",
                       task_id=task_id, node_id=node_id)
            return node_id
        except Exception as e:
            logger.error("Failed to store task context", task_id=task_id, error=str(e))
            raise

    async def get_task_history(self, task_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve historical task results by type"""
        params = {
            "knowledge_type": "task_result",
            "query": {
                "task_type": task_type,
                "limit": limit
            }
        }

        try:
            result = await self._send_request("get_knowledge", params)
            history = result.get("results", [])
            logger.info("Retrieved task history", task_type=task_type, count=len(history))
            return history
        except Exception as e:
            logger.error("Failed to retrieve task history", task_type=task_type, error=str(e))
            return []

    async def get_task_context(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored context for a specific task"""
        params = {
            "knowledge_type": "task_context",
            "query": {"task_id": task_id}
        }

        try:
            result = await self._send_request("get_knowledge", params)
            contexts = result.get("results", [])
            if contexts:
                logger.info("Retrieved task context", task_id=task_id)
                return contexts[0].get("content", {})
            return None
        except Exception as e:
            logger.error("Failed to retrieve task context", task_id=task_id, error=str(e))
            return None

    async def search_similar_tasks(self, task_description: str, task_type: str = None,
                                  limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar tasks using semantic similarity"""
        # Create search query with task description
        query = task_description
        if task_type:
            query += f" task_type:{task_type}"

        params = {
            "query": query,
            "limit": limit
        }

        try:
            result = await self._send_request("search_embeddings", params)
            similar_tasks = result.get("results", [])
            logger.info("Found similar tasks", query=task_description, count=len(similar_tasks))
            return similar_tasks
        except Exception as e:
            logger.error("Failed to search similar tasks", query=task_description, error=str(e))
            return []

    async def cache_task_result(self, cache_key: str, result: Any, ttl_seconds: int = 3600) -> bool:
        """Cache task result with TTL for performance optimization"""
        content = {
            "cache_key": cache_key,
            "result": result,
            "created_at": datetime.utcnow().isoformat(),
            "ttl_seconds": ttl_seconds
        }

        params = {
            "knowledge_type": "task_cache",
            "content": content
        }

        try:
            await self._send_request("store_knowledge", params)
            logger.info("Cached task result", cache_key=cache_key, ttl=ttl_seconds)
            return True
        except Exception as e:
            logger.error("Failed to cache task result", cache_key=cache_key, error=str(e))
            return False

    async def get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Retrieve cached task result if still valid"""
        params = {
            "knowledge_type": "task_cache",
            "query": {"cache_key": cache_key}
        }

        try:
            result = await self._send_request("get_knowledge", params)
            cached_results = result.get("results", [])

            if cached_results:
                cached_data = cached_results[0].get("content", {})
                created_at = datetime.fromisoformat(cached_data.get("created_at", ""))
                ttl_seconds = cached_data.get("ttl_seconds", 3600)

                # Check if cache is still valid
                if (datetime.utcnow() - created_at).total_seconds() < ttl_seconds:
                    logger.info("Cache hit", cache_key=cache_key)
                    return cached_data.get("result")
                else:
                    logger.info("Cache expired", cache_key=cache_key)

            return None
        except Exception as e:
            logger.error("Failed to retrieve cached result", cache_key=cache_key, error=str(e))
            return None

    # Original methods from orchestrator (maintained for compatibility)

    async def store_embedding(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """Store content embedding in brain service"""
        params = {
            "content": content,
            "metadata": metadata or {}
        }
        result = await self._send_request("store_embedding", params)
        return result.get("id", "")

    async def search_embeddings(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar embeddings"""
        params = {
            "query": query,
            "limit": limit
        }
        result = await self._send_request("search_embeddings", params)
        return result.get("results", [])

    async def store_knowledge(self, knowledge_type: str, content: Dict[str, Any]) -> str:
        """Store structured knowledge in brain service"""
        params = {
            "knowledge_type": knowledge_type,
            "content": content
        }
        result = await self._send_request("store_knowledge", params)
        return result.get("id", "")

    async def get_knowledge(self, knowledge_type: str, query: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Retrieve knowledge from brain service"""
        params = {
            "knowledge_type": knowledge_type,
            "query": query or {}
        }
        result = await self._send_request("get_knowledge", params)
        return result.get("results", [])

    async def disconnect(self):
        """Close WebSocket connection gracefully"""
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self.websocket and not self.websocket.closed:
            await self.websocket.close()

        self.connected = False
        logger.info("Disconnected from brain service")

    async def get_brain_context_async(self, project_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get semantic context from Brain for a project

        Args:
            project_id: Project identifier
            limit: Maximum number of context items to return

        Returns:
            List of context items from Brain
        """
        try:
            result = await self._send_request("get_context", {
                "project_id": project_id,
                "limit": limit
            })
            return result.get("context", [])
        except Exception as e:
            logger.error("Error getting brain context", project_id=project_id, error=str(e))
            return []

    async def get_department_context_async(self, project_id: str, department: str) -> List[Dict[str, Any]]:
        """
        Get department-specific context from Brain

        Args:
            project_id: Project identifier
            department: Department slug

        Returns:
            List of department-specific context items
        """
        try:
            result = await self._send_request("get_department_context", {
                "project_id": project_id,
                "department": department
            })
            return result.get("context", [])
        except Exception as e:
            logger.error("Error getting department context",
                        project_id=project_id, department=department, error=str(e))
            return []

    async def index_in_brain_async(
        self,
        project_id: str,
        items: List[Dict[str, Any]],
        department: Dict[str, Any]
    ) -> bool:
        """
        Index gather items in Brain (Neo4j)

        Args:
            project_id: Project identifier
            items: List of gather items to index
            department: Department configuration

        Returns:
            True if indexed successfully
        """
        try:
            nodes = []
            for item in items:
                node = {
                    "id": item.get('_id', str(uuid.uuid4())),
                    "projectId": project_id,
                    "content": item.get('content', ''),
                    "summary": item.get('summary', ''),
                    "department": department['slug'],
                    "departmentName": department.get('name', ''),
                    "type": "GatherItem",
                    "automated": True,
                    "metadata": item.get('automationMetadata', {})
                }
                nodes.append(node)

            result = await self._send_request("batch_create_nodes", {
                "project_id": project_id,
                "nodes": nodes
            })

            success = result.get("success", False)
            if success:
                logger.info("Indexed items in brain",
                           project_id=project_id,
                           department=department['slug'],
                           count=len(items))
            return success

        except Exception as e:
            logger.error("Error indexing in brain",
                        project_id=project_id,
                        department=department.get('slug'),
                        error=str(e))
            return False

    async def health_check(self) -> bool:
        """Check if brain service is healthy and responsive"""
        try:
            # Simple ping to check connectivity
            result = await self._send_request("ping", {})
            return result.get("status") == "ok"
        except Exception as e:
            logger.warning("Brain service health check failed", error=str(e))
            return False

    @asynccontextmanager
    async def connection(self):
        """Async context manager for automatic connection management"""
        try:
            await self.connect()
            yield self
        finally:
            await self.disconnect()

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()


# Synchronous wrapper functions for use in Celery tasks
def get_brain_context(project_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Synchronous wrapper for getting brain context
    """
    import os
    brain_url = os.getenv('BRAIN_SERVICE_URL', 'http://localhost:8002')
    client = BrainServiceClient(brain_url)

    try:
        return asyncio.run(client.get_brain_context_async(project_id, limit))
    except Exception as e:
        logger.error("Error in get_brain_context", project_id=project_id, error=str(e))
        return []


def get_department_context(project_id: str, department: str) -> List[Dict[str, Any]]:
    """
    Synchronous wrapper for getting department context
    """
    import os
    brain_url = os.getenv('BRAIN_SERVICE_URL', 'http://localhost:8002')
    client = BrainServiceClient(brain_url)

    try:
        return asyncio.run(client.get_department_context_async(project_id, department))
    except Exception as e:
        logger.error("Error in get_department_context",
                    project_id=project_id, department=department, error=str(e))
        return []


def index_in_brain(
    project_id: str,
    items: List[Dict[str, Any]],
    department: Dict[str, Any]
) -> bool:
    """
    Synchronous wrapper for indexing in brain
    """
    import os
    brain_url = os.getenv('BRAIN_SERVICE_URL', 'http://localhost:8002')
    client = BrainServiceClient(brain_url)

    try:
        return asyncio.run(client.index_in_brain_async(project_id, items, department))
    except Exception as e:
        logger.error("Error in index_in_brain",
                    project_id=project_id,
                    department=department.get('slug'),
                    error=str(e))
        return False