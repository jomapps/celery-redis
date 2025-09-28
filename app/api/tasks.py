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
from ..tasks import process_video_generation, process_image_generation, process_audio_generation
from ..clients.brain_client import BrainServiceClient
from ..config.settings import settings

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
            video_params=task_request.task_data.get('video_params', {})
        )
    elif task_request.task_type == TaskType.GENERATE_IMAGE:
        task_result = process_image_generation.delay(
            project_id=task_request.project_id,
            image_prompt=task_request.task_data.get('prompt', ''),
            image_params=task_request.task_data.get('image_params', {})
        )
    elif task_request.task_type == TaskType.PROCESS_AUDIO:
        task_result = process_audio_generation.delay(
            project_id=task_request.project_id,
            audio_prompt=task_request.task_data.get('prompt', ''),
            audio_params=task_request.task_data.get('audio_params', {})
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
    
    logger.info(
        "Task submitted successfully",
        task_id=str(task_id),
        project_id=task_request.project_id
    )
    
    return TaskSubmissionResponse(
        task_id=task_id,
        status=TaskStatus.QUEUED,
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