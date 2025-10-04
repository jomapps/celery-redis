"""
Task model for AI Movie Task Service
Follows constitutional requirements for data validation and type safety
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, field_validator, ConfigDict


class TaskType(str, Enum):
    """Enumeration of supported task types"""
    GENERATE_VIDEO = "generate_video"
    GENERATE_IMAGE = "generate_image"
    PROCESS_AUDIO = "process_audio"
    RENDER_ANIMATION = "render_animation"
    TEST_PROMPT = "test_prompt"  # For Auto-Movie App prompt testing integration
    EVALUATE_DEPARTMENT = "evaluate_department"  # For Aladdin project readiness evaluation
    AUTOMATED_GATHER_CREATION = "automated_gather_creation"  # For Aladdin automated gather creation


class TaskStatus(str, Enum):
    """Enumeration of task status values"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    """Task priority levels"""
    HIGH = 1
    NORMAL = 2
    LOW = 3


class TaskSubmissionRequest(BaseModel):
    """Request model for task submission"""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    project_id: str
    task_type: TaskType
    task_data: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    callback_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @field_validator('project_id')
    @classmethod
    def validate_project_id(cls, v: str) -> str:
        """Validate project ID format for security"""
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Project ID must contain only alphanumeric, underscore, and dash characters")
        if len(v) > 100:
            raise ValueError("Project ID too long (max 100 characters)")
        return v
    
    @field_validator('callback_url')
    @classmethod
    def validate_callback_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate callback URL format"""
        if v is not None:
            if not (v.startswith('http://') or v.startswith('https://')):
                raise ValueError("Callback URL must be HTTP or HTTPS")
        return v


class TaskSubmissionResponse(BaseModel):
    """Response model for task submission"""
    task_id: UUID
    status: TaskStatus
    project_id: str
    estimated_duration: int
    queue_position: int
    created_at: datetime


class TaskResult(BaseModel):
    """Task result data model"""
    media_url: str
    payload_media_id: str
    metadata: Dict[str, Any]


class TaskStatusResponse(BaseModel):
    """Response model for task status"""
    task_id: UUID
    project_id: str
    status: TaskStatus
    progress: float
    current_step: str
    result: Optional[TaskResult] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @field_validator('progress')
    @classmethod
    def validate_progress(cls, v: float) -> float:
        """Validate progress is between 0.0 and 1.0"""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Progress must be between 0.0 and 1.0")
        return v


class Task(BaseModel):
    """Core task data model"""
    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True
    )
    
    task_id: UUID
    project_id: str
    task_type: TaskType
    status: TaskStatus
    priority: TaskPriority
    task_data: Dict[str, Any]
    progress: float = 0.0
    current_step: str = "queued"
    result: Optional[TaskResult] = None
    error: Optional[str] = None
    callback_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_duration: int = 0
    queue_position: int = 0
    
    @field_validator('progress')
    @classmethod
    def validate_progress(cls, v: float) -> float:
        """Validate progress is between 0.0 and 1.0"""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Progress must be between 0.0 and 1.0")
        return v
    
    @field_validator('project_id')
    @classmethod
    def validate_project_id(cls, v: str) -> str:
        """Validate project ID format for constitutional security requirements"""
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Project ID must contain only alphanumeric, underscore, and dash characters")
        return v
    
    def is_terminal_state(self) -> bool:
        """Check if task is in a terminal state"""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
    
    def is_cancellable(self) -> bool:
        """Check if task can be cancelled"""
        return self.status in [TaskStatus.QUEUED, TaskStatus.PROCESSING]
    
    def is_retryable(self) -> bool:
        """Check if task can be retried"""
        return self.status == TaskStatus.FAILED
    
    def update_progress(self, progress: float, step: str) -> None:
        """Update task progress and current step"""
        self.progress = progress
        self.current_step = step
        if progress >= 1.0:
            self.status = TaskStatus.COMPLETED
            self.completed_at = datetime.utcnow()
    
    def mark_failed(self, error_message: str) -> None:
        """Mark task as failed with error message"""
        self.status = TaskStatus.FAILED
        self.error = error_message
        self.completed_at = datetime.utcnow()
    
    def mark_cancelled(self) -> None:
        """Mark task as cancelled"""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.utcnow()