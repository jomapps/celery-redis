"""
Tasks API endpoints for AI Movie Task Service
Follows constitutional requirements for API design and security
"""
from datetime import datetime
from uuid import uuid4
import uuid
from fastapi import APIRouter, Depends, HTTPException, Path
from typing import Dict, Any
import structlog

from ..models.task import (
    TaskSubmissionRequest,
    TaskSubmissionResponse,
    TaskStatusResponse,
    TaskStatus,
    TaskType,
    Task
)
from ..middleware.auth import verify_api_key, validate_task_id
from ..tasks import (
    process_video_generation,
    process_image_generation,
    process_audio_generation,
    evaluate_department
)
from ..clients.brain_client import BrainServiceClient
from ..config.settings import settings
from ..config.monitoring import get_task_metrics, check_task_health
from ..storage import task_storage

logger = structlog.get_logger()
router = APIRouter()


@router.post("/tasks/submit", response_model=TaskSubmissionResponse, status_code=201)
async def submit_task(
    task_request: TaskSubmissionRequest,
    api_key: str = Depends(verify_api_key)
) -> TaskSubmissionResponse:
    """
    Submit a new task for processing
    Constitutional requirement: Service-first architecture with clear API boundaries
    """
    logger.info(
        "Task submission received",
        project_id=task_request.project_id,
        task_type=task_request.task_type,
        priority=task_request.priority
    )
    
    # Generate unique task ID
    task_id = uuid4()
    
    # Create task instance
    task = Task(
        task_id=task_id,
        project_id=task_request.project_id,
        task_type=task_request.task_type,
        status=TaskStatus.QUEUED,
        priority=task_request.priority,
        task_data=task_request.task_data,
        callback_url=task_request.callback_url,
        metadata=task_request.metadata,
        created_at=datetime.utcnow(),
        estimated_duration=300,  # Default estimate
        queue_position=1  # TODO: Calculate actual queue position
    )
    
    # Submit task to appropriate Celery queue based on task type
    task_result = None

    if task_request.task_type == TaskType.GENERATE_VIDEO:
        task_result = process_video_generation.delay(
            project_id=task_request.project_id,
            scene_data=task_request.task_data.get('scene_data', {}),
            video_params=task_request.task_data.get('video_params', {}),
            callback_url=task_request.callback_url,
            metadata=task_request.metadata
        )
    elif task_request.task_type == TaskType.GENERATE_IMAGE:
        task_result = process_image_generation.delay(
            project_id=task_request.project_id,
            image_prompt=task_request.task_data.get('prompt', ''),
            image_params=task_request.task_data.get('image_params', {}),
            callback_url=task_request.callback_url,
            metadata=task_request.metadata
        )
    elif task_request.task_type == TaskType.PROCESS_AUDIO:
        task_result = process_audio_generation.delay(
            project_id=task_request.project_id,
            audio_prompt=task_request.task_data.get('prompt', ''),
            audio_params=task_request.task_data.get('audio_params', {}),
            callback_url=task_request.callback_url,
            metadata=task_request.metadata
        )
    elif task_request.task_type == TaskType.EVALUATE_DEPARTMENT:
        task_result = evaluate_department.delay(
            project_id=task_request.project_id,
            department_slug=task_request.task_data.get('department_slug'),
            department_number=task_request.task_data.get('department_number'),
            gather_data=task_request.task_data.get('gather_data', []),
            previous_evaluations=task_request.task_data.get('previous_evaluations', []),
            threshold=task_request.task_data.get('threshold', 80),
            callback_url=task_request.callback_url,
            metadata=task_request.metadata
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported task type: {task_request.task_type}"
        )

    # Update task with actual Celery task ID
    if task_result:
        task.task_id = uuid.UUID(task_result.id)
        task.status = TaskStatus.PROCESSING

    # Save task to storage
    task_storage.save_task(task)

    # Increment metrics
    task_storage.increment_metric("total_tasks")

    logger.info(
        "Task submitted successfully",
        task_id=str(task.task_id),
        celery_task_id=task_result.id if task_result else None,
        project_id=task_request.project_id
    )

    return TaskSubmissionResponse(
        task_id=task.task_id,
        status=task.status,
        project_id=task_request.project_id,
        estimated_duration=task.estimated_duration,
        queue_position=task.queue_position,
        created_at=task.created_at
    )


@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str = Path(..., description="Task UUID"),
    api_key: str = Depends(verify_api_key)
) -> TaskStatusResponse:
    """
    Get task status and progress
    Constitutional requirement: Real-time monitoring capabilities
    """
    # Validate task ID format
    validated_task_id = validate_task_id(task_id)
    
    logger.info(
        "Task status requested",
        task_id=validated_task_id
    )
    
    # Try to get task status from Celery and brain service
    try:
        from ..celery_app import celery_app

        # Get Celery task result
        task_result = celery_app.AsyncResult(validated_task_id)

        if task_result.state == 'PENDING':
            status = TaskStatus.QUEUED
        elif task_result.state == 'STARTED':
            status = TaskStatus.PROCESSING
        elif task_result.state == 'SUCCESS':
            status = TaskStatus.COMPLETED
        elif task_result.state == 'FAILURE':
            status = TaskStatus.FAILED
        else:
            status = TaskStatus.QUEUED

        # Try to get additional context from brain service
        brain_context = None
        try:
            brain_client = BrainServiceClient(settings.brain_service_base_url)
            async with brain_client.connection():
                brain_context = await brain_client.get_task_context(validated_task_id)
        except Exception as e:
            logger.warning("Could not retrieve brain service context",
                         task_id=validated_task_id, error=str(e))

        # Build response with available information
        response_data = {
            "task_id": validated_task_id,
            "status": status,
            "progress": task_result.info.get('progress', 0) if task_result.info else 0,
            "result": task_result.result if task_result.successful() else None,
            "error": str(task_result.info) if task_result.failed() else None,
            "created_at": brain_context.get('processing_start_time') if brain_context else datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        return TaskStatusResponse(**response_data)

    except Exception as e:
        logger.error("Failed to retrieve task status", task_id=validated_task_id, error=str(e))
        raise HTTPException(
            status_code=404,
            detail="Task not found or status unavailable"
        )


@router.delete("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str = Path(..., description="Task UUID"),
    api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Cancel a queued or processing task
    Constitutional requirement: Task lifecycle management
    """
    # Validate task ID format
    validated_task_id = validate_task_id(task_id)
    
    logger.info(
        "Task cancellation requested",
        task_id=validated_task_id
    )
    
    # TODO: Retrieve task from Redis
    # TODO: Cancel task in Celery
    
    # Mock task not found for now
    raise HTTPException(
        status_code=404,
        detail="Task not found"
    )


@router.post("/tasks/{task_id}/retry", response_model=TaskSubmissionResponse, status_code=201)
async def retry_task(
    task_id: str = Path(..., description="Task UUID"),
    api_key: str = Depends(verify_api_key)
) -> TaskSubmissionResponse:
    """
    Retry a failed task with same parameters
    Constitutional requirement: Reliability with retry mechanisms
    """
    # Validate task ID format
    validated_task_id = validate_task_id(task_id)
    
    logger.info(
        "Task retry requested",
        task_id=validated_task_id
    )
    
    # TODO: Retrieve original task from Redis
    # TODO: Validate task is in failed state
    # TODO: Create new task with same parameters
    
    # Mock task not found for now
    raise HTTPException(
        status_code=404,
        detail="Task not found"
    )


@router.delete("/tasks/{task_id}", status_code=200)
async def cancel_task(
    task_id: str = Path(..., description="Task UUID to cancel"),
    api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Cancel a running or queued task

    This endpoint revokes a task, preventing it from executing if queued,
    or terminating it if currently running.

    Args:
        task_id: UUID of the task to cancel
        api_key: API key for authentication

    Returns:
        Cancellation status and details

    Raises:
        HTTPException: If task_id is invalid or task cannot be cancelled
    """
    # Validate task ID format
    validated_task_id = validate_task_id(task_id)

    logger.info(
        "Task cancellation requested",
        task_id=validated_task_id
    )

    try:
        from ..celery_app import celery_app

        # Get task result to check current state
        task_result = celery_app.AsyncResult(validated_task_id)

        # Check if task exists and is cancellable
        if task_result.state == 'PENDING':
            # Task is queued, revoke it
            celery_app.control.revoke(
                validated_task_id,
                terminate=False,  # Don't terminate if not started
                signal='SIGTERM'
            )

            logger.info(
                "Queued task revoked",
                task_id=validated_task_id,
                previous_state='PENDING'
            )

            return {
                "task_id": validated_task_id,
                "status": "cancelled",
                "message": "Task was queued and has been revoked",
                "previous_state": "queued",
                "cancelled_at": datetime.utcnow().isoformat() + "Z"
            }

        elif task_result.state == 'STARTED':
            # Task is running, terminate it
            celery_app.control.revoke(
                validated_task_id,
                terminate=True,  # Terminate the running task
                signal='SIGTERM'
            )

            logger.info(
                "Running task terminated",
                task_id=validated_task_id,
                previous_state='STARTED'
            )

            return {
                "task_id": validated_task_id,
                "status": "cancelled",
                "message": "Task was running and has been terminated",
                "previous_state": "processing",
                "cancelled_at": datetime.utcnow().isoformat() + "Z"
            }

        elif task_result.state == 'SUCCESS':
            # Task already completed
            logger.warning(
                "Cannot cancel completed task",
                task_id=validated_task_id,
                state='SUCCESS'
            )

            raise HTTPException(
                status_code=400,
                detail="Task has already completed successfully and cannot be cancelled"
            )

        elif task_result.state == 'FAILURE':
            # Task already failed
            logger.warning(
                "Cannot cancel failed task",
                task_id=validated_task_id,
                state='FAILURE'
            )

            raise HTTPException(
                status_code=400,
                detail="Task has already failed and cannot be cancelled"
            )

        elif task_result.state == 'REVOKED':
            # Task already cancelled
            logger.warning(
                "Task already cancelled",
                task_id=validated_task_id,
                state='REVOKED'
            )

            return {
                "task_id": validated_task_id,
                "status": "cancelled",
                "message": "Task was already cancelled",
                "previous_state": "cancelled",
                "cancelled_at": datetime.utcnow().isoformat() + "Z"
            }

        else:
            # Unknown state, attempt revocation anyway
            celery_app.control.revoke(
                validated_task_id,
                terminate=True,
                signal='SIGTERM'
            )

            logger.warning(
                "Task in unknown state, revoked anyway",
                task_id=validated_task_id,
                state=task_result.state
            )

            return {
                "task_id": validated_task_id,
                "status": "cancelled",
                "message": f"Task in state '{task_result.state}' has been revoked",
                "previous_state": task_result.state.lower(),
                "cancelled_at": datetime.utcnow().isoformat() + "Z"
            }

    except Exception as e:
        logger.error(
            "Task cancellation failed",
            task_id=validated_task_id,
            error=str(e)
        )

        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel task: {str(e)}"
        )


@router.get("/tasks/metrics", status_code=200)
async def get_metrics(
    api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Get task queue metrics

    Returns current metrics including:
    - Total tasks processed
    - Success/failure rates
    - Average task durations
    - Currently running tasks

    Args:
        api_key: API key for authentication

    Returns:
        Dictionary containing task metrics
    """
    logger.info("Task metrics requested")

    # Get metrics from Redis storage
    redis_metrics = task_storage.get_metrics()

    total_tasks = redis_metrics.get("total_tasks", 0)
    completed_tasks = redis_metrics.get("completed_tasks", 0)
    failed_tasks = redis_metrics.get("failed_tasks", 0)

    metrics = {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
        "retried_tasks": redis_metrics.get("retried_tasks", 0),
        "cancelled_tasks": redis_metrics.get("cancelled_tasks", 0),
        "success_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
        "failure_rate": (failed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
        "average_durations": {},
        "currently_running": redis_metrics.get("currently_running", 0)
    }

    return {
        "metrics": metrics,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@router.get("/tasks/health", status_code=200)
async def get_health(
    api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Get task queue health status

    Returns health status with alerts for:
    - High failure rates
    - Long-running tasks
    - Other anomalies

    Args:
        api_key: API key for authentication

    Returns:
        Dictionary containing health status and alerts
    """
    logger.info("Task health check requested")

    health = check_task_health()

    return health