"""
Configuration management for AI Movie Task Service
Follows constitutional requirements for environment-based configuration
"""
import os
from typing import List, Optional
from pydantic import BaseModel, field_validator, ConfigDict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseModel):
    """Application settings with environment variable support"""
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_password: Optional[str] = None
    
    # Celery Configuration
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    api_workers: int = 4
    api_keys: str = "test-api-key"  # Comma-separated list
    
    # Auto-Movie App Integration (Port 3010)
    auto_movie_app_url: str = "http://localhost:3010"
    auto_movie_api_url: str = "http://localhost:3010/api"
    
    # PayloadCMS Integration (via Auto-Movie App)
    payload_api_url: str = "http://localhost:3010/api"
    payload_api_key: str = ""
    
    # Webhook configuration
    webhook_base_url: str = "http://localhost:3010/api/webhooks"
    
    # Cloudflare R2 Storage
    r2_endpoint: str = ""
    r2_access_key: str = ""
    r2_secret_key: str = ""
    r2_bucket_name: str = "ai-movie-assets"
    r2_public_url: str = ""
    
    # GPU Configuration
    cuda_visible_devices: str = "0,1,2,3"
    max_gpu_memory_per_task: str = "8GB"
    
    # Task Configuration
    max_retry_attempts: int = 3
    task_timeout: int = 3600  # 1 hour default
    queue_max_size: int = 1000
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    log_level: str = "INFO"
    
    # Development
    environment: str = "development"
    debug: bool = False
    
    @field_validator('api_keys')
    @classmethod
    def validate_api_keys(cls, v):
        """Ensure at least one API key is provided"""
        if not v or not v.strip():
            raise ValueError("At least one API key must be provided")
        return v
    
    def get_api_keys(self) -> List[str]:
        """Get list of valid API keys"""
        return [key.strip() for key in self.api_keys.split(',') if key.strip()]
    
    def get_redis_url(self) -> str:
        """Get complete Redis URL with password if provided"""
        if self.redis_password:
            # Parse URL and add password
            url_parts = self.redis_url.split('://')
            if len(url_parts) == 2:
                return f"{url_parts[0]}://:{self.redis_password}@{url_parts[1]}"
        return self.redis_url
    
    model_config = ConfigDict(
        case_sensitive=False,
        validate_assignment=True
    )


# Global settings instance with environment variable loading
settings = Settings(
    redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    redis_password=os.getenv("REDIS_PASSWORD"),
    celery_broker_url=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    celery_result_backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
    api_host=os.getenv("API_HOST", "0.0.0.0"),
    api_port=int(os.getenv("API_PORT", "8001")),
    api_workers=int(os.getenv("API_WORKERS", "4")),
    api_keys=os.getenv("API_KEY", "test-api-key"),
    auto_movie_app_url=os.getenv("AUTO_MOVIE_APP_URL", "http://localhost:3010"),
    auto_movie_api_url=os.getenv("AUTO_MOVIE_API_URL", "http://localhost:3010/api"),
    payload_api_url=os.getenv("PAYLOAD_API_URL", "http://localhost:3010/api"),
    payload_api_key=os.getenv("PAYLOAD_API_KEY", ""),
    webhook_base_url=os.getenv("WEBHOOK_BASE_URL", "http://localhost:3010/api/webhooks"),
    r2_endpoint=os.getenv("R2_ENDPOINT", ""),
    r2_access_key=os.getenv("R2_ACCESS_KEY", ""),
    r2_secret_key=os.getenv("R2_SECRET_KEY", ""),
    r2_bucket_name=os.getenv("R2_BUCKET_NAME", "ai-movie-assets"),
    r2_public_url=os.getenv("R2_PUBLIC_URL", ""),
    cuda_visible_devices=os.getenv("CUDA_VISIBLE_DEVICES", "0,1,2,3"),
    max_gpu_memory_per_task=os.getenv("MAX_GPU_MEMORY_PER_TASK", "8GB"),
    max_retry_attempts=int(os.getenv("MAX_RETRY_ATTEMPTS", "3")),
    task_timeout=int(os.getenv("TASK_TIMEOUT", "3600")),
    queue_max_size=int(os.getenv("QUEUE_MAX_SIZE", "1000")),
    enable_metrics=os.getenv("ENABLE_METRICS", "true").lower() == "true",
    metrics_port=int(os.getenv("METRICS_PORT", "9090")),
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    environment=os.getenv("ENVIRONMENT", "development"),
    debug=os.getenv("DEBUG", "false").lower() == "true",
)


# Redis connection configuration
REDIS_CONFIG = {
    "host": "localhost",
    "port": 6379,
    "db": 0,
    "password": settings.redis_password,
    "decode_responses": True,
    "socket_timeout": 5,
    "socket_connect_timeout": 5,
    "retry_on_timeout": True,
}


# Celery configuration
CELERY_CONFIG = {
    "broker_url": settings.celery_broker_url,
    "result_backend": settings.celery_result_backend,
    "task_serializer": "json",
    "accept_content": ["json"],
    "result_serializer": "json",
    "timezone": "UTC",
    "enable_utc": True,
    "worker_prefetch_multiplier": 1,
    "task_acks_late": True,
    "task_reject_on_worker_lost": True,
    "task_time_limit": settings.task_timeout,
    "task_soft_time_limit": settings.task_timeout - 60,
    "result_expires": 86400,  # 24 hours
}


# GPU configuration
def get_gpu_devices() -> List[int]:
    """Parse CUDA_VISIBLE_DEVICES into list of device IDs"""
    devices_str = settings.cuda_visible_devices
    if not devices_str:
        return []
    
    try:
        return [int(d.strip()) for d in devices_str.split(',') if d.strip()]
    except ValueError:
        return []


# Monitoring configuration
MONITORING_CONFIG = {
    "enable_metrics": settings.enable_metrics,
    "metrics_port": settings.metrics_port,
    "log_level": settings.log_level,
}