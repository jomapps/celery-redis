"""
Task storage using Redis for persistence
Provides task tracking across API and worker processes
"""
import json
import redis
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from ..config.settings import settings
from ..models.task import Task, TaskStatus

logger = structlog.get_logger(__name__)


class TaskStorage:
    """Redis-based task storage for tracking tasks across processes"""
    
    def __init__(self):
        """Initialize Redis connection"""
        self.redis_client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True
        )
        self.task_prefix = "task:"
        self.project_tasks_prefix = "project_tasks:"
        self.task_metrics_key = "task_metrics"
    
    def save_task(self, task: Task) -> bool:
        """
        Save task to Redis
        
        Args:
            task: Task object to save
            
        Returns:
            True if successful
        """
        try:
            task_key = f"{self.task_prefix}{task.task_id}"
            project_key = f"{self.project_tasks_prefix}{task.project_id}"
            
            # Convert task to dict
            task_data = {
                "task_id": str(task.task_id),
                "project_id": task.project_id,
                "task_type": task.task_type,
                "status": task.status,
                "priority": task.priority,
                "task_data": json.dumps(task.task_data) if task.task_data else "{}",
                "callback_url": task.callback_url or "",
                "metadata": json.dumps(task.metadata) if task.metadata else "{}",
                "created_at": task.created_at.isoformat() if task.created_at else datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "estimated_duration": task.estimated_duration or 0,
                "queue_position": task.queue_position or 0,
                "result": json.dumps(task.result) if task.result else "",
                "error": task.error or ""
            }
            
            # Save task data
            self.redis_client.hset(task_key, mapping=task_data)
            
            # Add task to project's task list
            self.redis_client.sadd(project_key, str(task.task_id))
            
            # Set expiration (24 hours)
            self.redis_client.expire(task_key, 86400)
            self.redis_client.expire(project_key, 86400)
            
            logger.info(
                "Task saved to storage",
                task_id=str(task.task_id),
                project_id=task.project_id,
                status=task.status
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to save task",
                task_id=str(task.task_id),
                error=str(e)
            )
            return False
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task from Redis
        
        Args:
            task_id: Task UUID
            
        Returns:
            Task data dict or None if not found
        """
        try:
            task_key = f"{self.task_prefix}{task_id}"
            task_data = self.redis_client.hgetall(task_key)
            
            if not task_data:
                return None
            
            # Parse JSON fields
            if task_data.get("task_data"):
                task_data["task_data"] = json.loads(task_data["task_data"])
            if task_data.get("metadata"):
                task_data["metadata"] = json.loads(task_data["metadata"])
            if task_data.get("result"):
                task_data["result"] = json.loads(task_data["result"]) if task_data["result"] else None
            
            return task_data
            
        except Exception as e:
            logger.error(
                "Failed to get task",
                task_id=task_id,
                error=str(e)
            )
            return None
    
    def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> bool:
        """
        Update task status
        
        Args:
            task_id: Task UUID
            status: New status
            result: Task result (if completed)
            error: Error message (if failed)
            
        Returns:
            True if successful
        """
        try:
            task_key = f"{self.task_prefix}{task_id}"
            
            updates = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if result:
                updates["result"] = json.dumps(result)
            
            if error:
                updates["error"] = error
            
            self.redis_client.hset(task_key, mapping=updates)
            
            logger.info(
                "Task status updated",
                task_id=task_id,
                status=status
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to update task status",
                task_id=task_id,
                error=str(e)
            )
            return False
    
    def get_project_tasks(
        self,
        project_id: str,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all tasks for a project
        
        Args:
            project_id: Project ID
            status: Filter by status (optional)
            task_type: Filter by task type (optional)
            limit: Max number of tasks to return
            offset: Offset for pagination
            
        Returns:
            List of task data dicts
        """
        try:
            project_key = f"{self.project_tasks_prefix}{project_id}"
            task_ids = self.redis_client.smembers(project_key)
            
            tasks = []
            for task_id in task_ids:
                task_data = self.get_task(task_id)
                if task_data:
                    # Apply filters
                    if status and task_data.get("status") != status:
                        continue
                    if task_type and task_data.get("task_type") != task_type:
                        continue
                    
                    tasks.append(task_data)
            
            # Sort by created_at (newest first)
            tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            # Apply pagination
            return tasks[offset:offset + limit]
            
        except Exception as e:
            logger.error(
                "Failed to get project tasks",
                project_id=project_id,
                error=str(e)
            )
            return []
    
    def get_project_tasks_count(
        self,
        project_id: str,
        status: Optional[str] = None,
        task_type: Optional[str] = None
    ) -> int:
        """
        Get count of tasks for a project
        
        Args:
            project_id: Project ID
            status: Filter by status (optional)
            task_type: Filter by task type (optional)
            
        Returns:
            Number of tasks
        """
        try:
            project_key = f"{self.project_tasks_prefix}{project_id}"
            task_ids = self.redis_client.smembers(project_key)
            
            if not status and not task_type:
                return len(task_ids)
            
            count = 0
            for task_id in task_ids:
                task_data = self.get_task(task_id)
                if task_data:
                    if status and task_data.get("status") != status:
                        continue
                    if task_type and task_data.get("task_type") != task_type:
                        continue
                    count += 1
            
            return count
            
        except Exception as e:
            logger.error(
                "Failed to get project tasks count",
                project_id=project_id,
                error=str(e)
            )
            return 0
    
    def increment_metric(self, metric_name: str, value: int = 1):
        """Increment a metric counter"""
        try:
            self.redis_client.hincrby(self.task_metrics_key, metric_name, value)
        except Exception as e:
            logger.error(f"Failed to increment metric {metric_name}: {e}")
    
    def get_metrics(self) -> Dict[str, int]:
        """Get all metrics"""
        try:
            metrics = self.redis_client.hgetall(self.task_metrics_key)
            return {k: int(v) for k, v in metrics.items()}
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {}


# Global task storage instance
task_storage = TaskStorage()

