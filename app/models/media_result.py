"""
Media Result model for AI Movie Task Service
Follows constitutional requirements for media handling and storage
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, field_validator, ConfigDict


class MediaType(str, Enum):
    """Enumeration of media types"""
    VIDEO_SEGMENT = "video_segment"
    CHARACTER_DESIGN = "character_design"
    DIALOGUE_AUDIO = "dialogue_audio"
    ANIMATION = "animation"


class MediaFormat(str, Enum):
    """Enumeration of media formats"""
    MP4 = "MP4"
    JPEG = "JPEG"
    PNG = "PNG"
    MP3 = "MP3"
    WAV = "WAV"


class MediaResult(BaseModel):
    """Media result data model"""
    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True
    )
    
    media_id: UUID
    task_id: UUID
    project_id: str
    media_type: MediaType
    media_url: str
    payload_media_id: str
    file_name: str
    file_size: int
    duration: Optional[float] = None  # For video/audio
    resolution: Optional[str] = None  # For video/images
    format: MediaFormat
    generation_metadata: Dict[str, Any]
    created_at: datetime
    
    @field_validator('media_url')
    @classmethod
    def validate_media_url(cls, v: str) -> str:
        """Validate media URL format"""
        if not v.startswith('https://'):
            raise ValueError("Media URL must use HTTPS")
        return v
    
    @field_validator('file_size')
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        """Validate file size is positive"""
        if v <= 0:
            raise ValueError("File size must be positive")
        return v
    
    @field_validator('duration')
    @classmethod
    def validate_duration(cls, v: Optional[float]) -> Optional[float]:
        """Validate duration is positive for media with duration"""
        if v is not None and v <= 0:
            raise ValueError("Duration must be positive")
        return v
    
    @field_validator('resolution')
    @classmethod
    def validate_resolution(cls, v: Optional[str]) -> Optional[str]:
        """Validate resolution format (WIDTHxHEIGHT)"""
        if v is not None:
            import re
            if not re.match(r'^\d+x\d+$', v):
                raise ValueError("Resolution must be in format WIDTHxHEIGHT (e.g., 1920x1080)")
        return v
    
    def get_display_name(self) -> str:
        """Get human-readable display name for media"""
        type_names = {
            MediaType.VIDEO_SEGMENT: "Video Segment",
            MediaType.CHARACTER_DESIGN: "Character Design",
            MediaType.DIALOGUE_AUDIO: "Dialogue Audio",
            MediaType.ANIMATION: "Animation"
        }
        return type_names.get(self.media_type, str(self.media_type))
    
    def is_video(self) -> bool:
        """Check if media is video type"""
        return self.media_type in [MediaType.VIDEO_SEGMENT, MediaType.ANIMATION]
    
    def is_audio(self) -> bool:
        """Check if media is audio type"""
        return self.media_type == MediaType.DIALOGUE_AUDIO
    
    def is_image(self) -> bool:
        """Check if media is image type"""
        return self.media_type == MediaType.CHARACTER_DESIGN


class MediaMetadata(BaseModel):
    """Metadata for media generation parameters"""
    duration: Optional[float] = None
    resolution: Optional[str] = None
    file_size: int
    format: MediaFormat
    generation_model: Optional[str] = None
    generation_parameters: Optional[Dict[str, Any]] = None