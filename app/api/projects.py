"""
Projects API endpoints for AI Movie Task Service
Follows constitutional requirements for project isolation
"""
from fastapi import APIRouter, Depends, Query, Path
import structlog

from ..models.project import ProjectTasksRequest, ProjectTasksResponse, ProjectTasksSummary
from ..middleware.auth import verify_api_key, validate_project_id
from ..storage import task_storage

logger = structlog.get_logger()
router = APIRouter()


@router.get("/projects/{project_id}/tasks", response_model=ProjectTasksResponse)
async def get_project_tasks(
    project_id: str = Path(..., description="Project identifier"),
    status: str = Query(None, description="Filter by task status"),
    task_type: str = Query(None, description="Filter by task type"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    api_key: str = Depends(verify_api_key)
) -> ProjectTasksResponse:
    """
    Get all tasks for a specific project with filtering and pagination
    Constitutional requirement: Project isolation enforcement
    """
    # Validate project ID format
    validated_project_id = validate_project_id(project_id)
    
    logger.info(
        "Project tasks listing requested",
        project_id=validated_project_id,
        status_filter=status,
        task_type_filter=task_type,
        page=page,
        limit=limit
    )
    
    # Create request model for validation
    request = ProjectTasksRequest(
        status=status,
        task_type=task_type,
        page=page,
        limit=limit
    )

    # Calculate offset for pagination
    offset = (page - 1) * limit

    # Retrieve tasks from storage
    tasks = task_storage.get_project_tasks(
        project_id=validated_project_id,
        status=status,
        task_type=task_type,
        limit=limit,
        offset=offset
    )

    # Get total count for pagination
    total = task_storage.get_project_tasks_count(
        project_id=validated_project_id,
        status=status,
        task_type=task_type
    )

    total_pages = (total + limit - 1) // limit if total > 0 else 0

    logger.info(
        "Project tasks retrieved",
        project_id=validated_project_id,
        count=len(tasks),
        total=total
    )

    return ProjectTasksResponse(
        tasks=tasks,
        pagination={
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages
        }
    )