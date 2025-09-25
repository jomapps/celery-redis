"""
Project model for AI Movie Task Service
Follows constitutional requirements for project isolation
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator, ConfigDict


class Project(BaseModel):
    """Project data model for task isolation"""
    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True
    )
    
    project_id: str
    project_name: str
    task_count: int = 0
    active_tasks: int = 0
    storage_prefix: str
    created_at: datetime
    last_activity: datetime
    
    @field_validator('project_id')
    @classmethod
    def validate_project_id(cls, v: str) -> str:
        """Validate project ID format for constitutional security requirements"""
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Project ID must contain only alphanumeric, underscore, and dash characters")
        if len(v) > 100:
            raise ValueError("Project ID too long (max 100 characters)")
        return v
    
    @field_validator('storage_prefix')
    @classmethod
    def validate_storage_prefix(cls, v: str) -> str:
        """Validate storage prefix format"""
        # Remove any path traversal attempts
        clean_prefix = v.replace('..', '').replace('//', '/')
        return f"projects/{clean_prefix.strip('/')}"
    
    def get_storage_path(self, media_type: str, filename: str) -> str:
        """Get full storage path for media file"""
        return f"{self.storage_prefix}/{media_type}/{filename}"
    
    def increment_task_count(self) -> None:
        """Increment total task count"""
        self.task_count += 1
        self.last_activity = datetime.utcnow()
    
    def increment_active_tasks(self) -> None:
        """Increment active task count"""
        self.active_tasks += 1
        self.last_activity = datetime.utcnow()
    
    def decrement_active_tasks(self) -> None:
        """Decrement active task count"""
        if self.active_tasks > 0:
            self.active_tasks -= 1
        self.last_activity = datetime.utcnow()


class ProjectTasksRequest(BaseModel):
    """Request model for project tasks listing"""
    status: Optional[str] = None
    task_type: Optional[str] = None
    page: int = 1
    limit: int = 20
    
    @field_validator('page')
    @classmethod
    def validate_page(cls, v: int) -> int:
        """Validate page number"""
        if v < 1:
            raise ValueError("Page must be >= 1")
        return v
    
    @field_validator('limit')
    @classmethod
    def validate_limit(cls, v: int) -> int:
        """Validate page limit"""
        if v < 1 or v > 100:
            raise ValueError("Limit must be between 1 and 100")
        return v


class ProjectTasksSummary(BaseModel):
    """Summary task data for project listings"""
    task_id: str
    task_type: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    result_url: Optional[str] = None


class ProjectTasksResponse(BaseModel):
    """Response model for project tasks listing"""
    tasks: list[ProjectTasksSummary]
    pagination: dict[str, int]