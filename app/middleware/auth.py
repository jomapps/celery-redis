"""
Authentication middleware for API key validation
Follows constitutional security and isolation requirements
"""
from fastapi import HTTPException, Depends, Header
from typing import Optional, List
import structlog
from ..config import settings

logger = structlog.get_logger()


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    Verify API key for authenticated endpoints
    
    Args:
        x_api_key: API key from X-API-Key header
        
    Returns:
        str: Validated API key
        
    Raises:
        HTTPException: 401 if key is missing or invalid
    """
    if not x_api_key:
        logger.warning("API request missing X-API-Key header")
        raise HTTPException(
            status_code=401,
            detail="API key required in X-API-Key header"
        )
    
    # Get valid API keys from configuration
    valid_keys = settings.get_api_keys()
    
    if x_api_key not in valid_keys:
        logger.warning(
            "Invalid API key attempted",
            provided_key_prefix=x_api_key[:8] if len(x_api_key) > 8 else "short_key"
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    logger.debug("API key validated successfully")
    return x_api_key


def validate_project_id(project_id: str) -> str:
    """
    Validate project ID format for security
    
    Args:
        project_id: Project identifier to validate
        
    Returns:
        str: Validated project ID
        
    Raises:
        HTTPException: 400 if format is invalid
    """
    import re
    
    # Constitutional requirement: project isolation validation
    if not re.match(r'^[a-zA-Z0-9_-]+$', project_id):
        logger.warning(
            "Invalid project ID format attempted",
            project_id=project_id
        )
        raise HTTPException(
            status_code=400,
            detail="Invalid project ID format. Only alphanumeric, underscore, and dash characters allowed."
        )
    
    if len(project_id) > 100:  # Reasonable length limit
        raise HTTPException(
            status_code=400,
            detail="Project ID too long. Maximum 100 characters allowed."
        )
    
    return project_id


def validate_task_id(task_id: str) -> str:
    """
    Validate task ID format (UUID)
    
    Args:
        task_id: Task identifier to validate
        
    Returns:
        str: Validated task ID
        
    Raises:
        HTTPException: 400 if format is invalid
    """
    import uuid
    
    try:
        # Validate UUID format
        uuid.UUID(task_id)
        return task_id
    except ValueError:
        logger.warning(
            "Invalid task ID format attempted",
            task_id=task_id
        )
        raise HTTPException(
            status_code=400,
            detail="Invalid task ID format. Must be a valid UUID."
        )


class ProjectIsolationMixin:
    """
    Mixin for enforcing project isolation at the API level
    Constitutional requirement for security and isolation
    """
    
    @staticmethod
    def ensure_project_access(project_id: str, user_context: Optional[dict] = None) -> bool:
        """
        Ensure user has access to the specified project
        
        Args:
            project_id: Project to check access for
            user_context: Optional user context for access control
            
        Returns:
            bool: True if access is allowed
            
        Raises:
            HTTPException: 403 if access is denied
        """
        # Validate project ID format first
        validate_project_id(project_id)
        
        # TODO: Implement actual project access control
        # This would typically check against PayloadCMS or user database
        # For now, allow all access in development mode
        
        if settings.environment == "production" and not user_context:
            logger.warning(
                "Project access attempted without user context in production",
                project_id=project_id
            )
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions for project access"
            )
        
        return True
    
    @staticmethod
    def sanitize_file_paths(project_id: str, file_path: str) -> str:
        """
        Sanitize file paths to prevent directory traversal
        Constitutional requirement for security
        
        Args:
            project_id: Project identifier for path scoping
            file_path: File path to sanitize
            
        Returns:
            str: Sanitized file path scoped to project
        """
        # Remove any path traversal attempts
        clean_path = file_path.replace('..', '').replace('//', '/')
        
        # Ensure path starts with project prefix
        sanitized_path = f"projects/{project_id}/{clean_path.lstrip('/')}"
        
        logger.debug(
            "File path sanitized",
            original_path=file_path,
            sanitized_path=sanitized_path,
            project_id=project_id
        )
        
        return sanitized_path