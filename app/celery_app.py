"""
Celery application configuration for AI Movie Task Service
Follows constitutional requirements for distributed task processing
"""
from celery import Celery
from .config import settings, CELERY_CONFIG

# Create Celery application instance
celery_app = Celery("ai_movie_tasks")

# Apply configuration from settings
celery_app.conf.update(CELERY_CONFIG)

# Task routing configuration for different worker types
celery_app.conf.task_routes = {
    'app.tasks.video_tasks.*': {'queue': 'gpu_heavy'},
    'app.tasks.image_tasks.*': {'queue': 'gpu_medium'},
    'app.tasks.audio_tasks.*': {'queue': 'cpu_intensive'},
    'automated_gather_creation': {'queue': 'cpu_intensive'},
}

# Worker configuration for GPU management
celery_app.conf.worker_concurrency = 2  # Adjust based on GPU memory
celery_app.conf.worker_prefetch_multiplier = 1  # Prevent memory issues
celery_app.conf.worker_max_tasks_per_child = 10  # Restart worker after 10 tasks (prevent memory leaks)
celery_app.conf.worker_max_memory_per_child = 2048000  # 2GB memory limit per worker (in KB)

# Task execution settings
celery_app.conf.task_acks_late = True
celery_app.conf.task_reject_on_worker_lost = True
celery_app.conf.task_time_limit = settings.task_timeout
celery_app.conf.task_soft_time_limit = settings.task_timeout - 300  # 5 min buffer

# Result backend settings
celery_app.conf.result_expires = 86400  # 24 hours
celery_app.conf.result_compression = 'gzip'

# Task-specific timeout configuration
celery_app.conf.task_time_limits = {
    'automated_gather_creation': 600,  # 10 minutes hard timeout
}

celery_app.conf.task_soft_time_limits = {
    'automated_gather_creation': 540,  # 9 minutes soft timeout (warning)
}

# Retry configuration for automated_gather_creation
celery_app.conf.task_autoretry_for = (
    ConnectionError,
    TimeoutError,
    Exception,  # Catch-all for temporary failures
)

celery_app.conf.task_retry_kwargs = {
    'max_retries': 3,
    'countdown': 60,  # Wait 60 seconds before first retry
}

celery_app.conf.task_retry_backoff = True
celery_app.conf.task_retry_backoff_max = 600  # Max 10 minutes between retries
celery_app.conf.task_retry_jitter = True  # Add randomness to prevent thundering herd

# Monitoring and events
celery_app.conf.worker_send_task_events = True
celery_app.conf.task_send_sent_event = True

# Import task modules to register them
try:
    from . import tasks  # This will import all task modules
except ImportError:
    # Tasks not yet implemented, that's expected during testing phase
    pass


def get_celery_app() -> Celery:
    """Get configured Celery application instance"""
    return celery_app