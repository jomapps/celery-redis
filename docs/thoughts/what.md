# AI Movie Platform - Celery/Redis Task Service

## Overview
Standalone GPU-intensive task processing service for AI movie production platform. Handles video generation, image creation, audio synthesis, and other computationally expensive operations with project-based isolation and result integration with PayloadCMS.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Main App                                 │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Task Client                                ││
│  │  POST /api/external/tasks/submit                       ││
│  │  GET  /api/external/tasks/{task_id}/status             ││
│  │  GET  /api/external/tasks/project/{project_id}         ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP REST Calls
┌─────────────────────────▼───────────────────────────────────┐
│                 Celery/Redis Task Service                   │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                 Task API Server                         ││
│  │  FastAPI + uvicorn (Port 8001)                         ││
│  │  • Task submission endpoints                            ││
│  │  • Status monitoring endpoints                          ││
│  │  • Project isolation middleware                         ││
│  │  • Authentication & validation                          ││
│  └─────────────────────────────────────────────────────────┘│
│                              │                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Message Broker                             ││
│  │  Redis (Port 6379)                                     ││
│  │  • Task queue management                                ││
│  │  • Result backend storage                               ││
│  │  • Project-based queue routing                          ││
│  │  • Task priority management                             ││
│  └─────────────────────────────────────────────────────────┘│
│                              │                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │               Celery Workers                            ││
│  │  GPU Workers (CUDA enabled)                            ││
│  │  • Video generation workers                             ││
│  │  • Image generation workers                             ││
│  │  • Audio processing workers                             ││
│  │  • Animation rendering workers                          ││
│  └─────────────────────────────────────────────────────────┘│
│                              │                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Integration Layer                          ││
│  │  • PayloadCMS client for media upload                  ││
│  │  • Cloudflare R2 direct upload                         ││
│  │  • Webhook callbacks                                    ││
│  │  • Error reporting                                      ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
celery-task-service/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── celery_app.py          # Celery configuration
│   ├── config.py              # Environment configuration
│   ├── models/
│   │   ├── __init__.py
│   │   ├── task_models.py     # Pydantic models
│   │   └── response_models.py
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── video_tasks.py     # Video generation tasks
│   │   ├── image_tasks.py     # Image generation tasks
│   │   ├── audio_tasks.py     # Audio processing tasks
│   │   └── base_task.py       # Base task class
│   ├── services/
│   │   ├── __init__.py
│   │   ├── payload_client.py  # PayloadCMS integration
│   │   ├── storage_client.py  # R2 storage client
│   │   └── gpu_manager.py     # GPU resource management
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py           # API key authentication
│   │   └── project_isolation.py
│   └── utils/
│       ├── __init__.py
│       ├── logging.py
│       └── monitoring.py
├── docker/
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   └── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## API Specification

### Authentication
All requests require `X-API-Key` header with valid API key.

### Task Submission

#### POST `/api/v1/tasks/submit`

Submit a new task for processing.

**Request Body:**
```json
{
  "project_id": "detective_series_001",
  "task_type": "generate_video" | "generate_image" | "process_audio" | "render_animation",
  "task_data": {
    // Task-specific parameters
  },
  "priority": 1, // 1=high, 2=normal, 3=low
  "callback_url": "https://main-app.com/api/webhooks/task-complete",
  "metadata": {
    "user_id": "user123",
    "agent_id": "video_generation_agent",
    "scene_id": "scene_005"
  }
}
```

**Response:**
```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "queued",
  "project_id": "detective_series_001",
  "estimated_duration": 300, // seconds
  "queue_position": 5,
  "created_at": "2025-09-24T10:30:00Z"
}
```

### Task Status

#### GET `/api/v1/tasks/{task_id}/status`

Get current task status and progress.

**Response:**
```json
{
  "task_id": "abc123-def456-ghi789",
  "project_id": "detective_series_001", 
  "status": "processing" | "queued" | "completed" | "failed" | "cancelled",
  "progress": 0.75, // 0.0 to 1.0
  "current_step": "rendering_video",
  "result": {
    "media_url": "https://r2.cloudflare.com/bucket/project_001/video_abc123.mp4",
    "payload_media_id": "64f1b2c3a8d9e0f1",
    "metadata": {
      "duration": 7.0,
      "resolution": "1920x1080",
      "file_size": 15728640
    }
  },
  "error": null,
  "started_at": "2025-09-24T10:30:15Z",
  "completed_at": "2025-09-24T10:35:30Z"
}
```

### Project Tasks

#### GET `/api/v1/projects/{project_id}/tasks`

Get all tasks for a specific project with filtering and pagination.

**Query Parameters:**
- `status`: Filter by task status
- `task_type`: Filter by task type
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20, max: 100)

**Response:**
```json
{
  "tasks": [
    {
      "task_id": "abc123-def456-ghi789",
      "task_type": "generate_video",
      "status": "completed",
      "created_at": "2025-09-24T10:30:00Z",
      "completed_at": "2025-09-24T10:35:30Z",
      "result_url": "https://r2.cloudflare.com/bucket/project_001/video_abc123.mp4"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 45,
    "total_pages": 3
  }
}
```

### Task Management

#### DELETE `/api/v1/tasks/{task_id}/cancel`

Cancel a queued or processing task.

#### POST `/api/v1/tasks/{task_id}/retry`

Retry a failed task with same parameters.

## Task Definitions

### Video Generation Task

```python
# tasks/video_tasks.py
from celery import Task
from .base_task import ProjectIsolatedTask

@celery_app.task(bind=True, base=ProjectIsolatedTask)
def generate_video_segment(self, project_id: str, task_data: dict):
    """
    Generate 7-second video segment from storyboard data
    
    Args:
        project_id: Project isolation identifier
        task_data: {
            "storyboard_images": ["url1", "url2", ...],
            "scene_description": "Detective enters the dark alley",
            "camera_angle": "wide_shot",
            "lighting": "noir_dramatic",
            "character_positions": [...],
            "audio_cues": [...]
        }
    """
    try:
        # Update progress
        self.update_state(state='PROGRESS', meta={'progress': 0.1, 'step': 'loading_models'})
        
        # Load video generation model
        video_model = load_video_model()
        
        self.update_state(state='PROGRESS', meta={'progress': 0.3, 'step': 'processing_storyboard'})
        
        # Process storyboard images
        processed_frames = process_storyboard_sequence(task_data['storyboard_images'])
        
        self.update_state(state='PROGRESS', meta={'progress': 0.6, 'step': 'generating_video'})
        
        # Generate video
        video_result = video_model.generate(
            frames=processed_frames,
            description=task_data['scene_description'],
            duration=7.0,
            fps=24
        )
        
        self.update_state(state='PROGRESS', meta={'progress': 0.9, 'step': 'uploading_result'})
        
        # Upload to R2 and PayloadCMS
        upload_result = upload_media_to_payload(
            project_id=project_id,
            media_data=video_result,
            media_type='video_segment',
            metadata={
                'scene_description': task_data['scene_description'],
                'duration': 7.0,
                'generation_model': 'runway_gen3'
            }
        )
        
        return {
            'media_url': upload_result['url'],
            'payload_media_id': upload_result['id'],
            'metadata': {
                'duration': 7.0,
                'resolution': '1920x1080',
                'file_size': len(video_result),
                'fps': 24
            }
        }
        
    except Exception as exc:
        self.retry(exc=exc, countdown=60, max_retries=3)
```

### Image Generation Task

```python
# tasks/image_tasks.py
@celery_app.task(bind=True, base=ProjectIsolatedTask)
def generate_character_image(self, project_id: str, task_data: dict):
    """
    Generate character design image
    
    Args:
        project_id: Project isolation identifier
        task_data: {
            "character_description": "Detective in 1920s noir style",
            "style_guide": "https://...",
            "reference_images": ["url1", "url2"],
            "pose": "standing_confident",
            "lighting": "dramatic_shadow"
        }
    """
    try:
        self.update_state(state='PROGRESS', meta={'progress': 0.2, 'step': 'loading_models'})
        
        # Load image generation model
        image_model = load_image_model()
        
        self.update_state(state='PROGRESS', meta={'progress': 0.5, 'step': 'generating_image'})
        
        # Generate image
        image_result = image_model.generate(
            prompt=build_character_prompt(task_data),
            style_reference=task_data.get('style_guide'),
            quality='high',
            aspect_ratio='1:1'
        )
        
        self.update_state(state='PROGRESS', meta={'progress': 0.9, 'step': 'uploading_result'})
        
        # Upload to PayloadCMS
        upload_result = upload_media_to_payload(
            project_id=project_id,
            media_data=image_result,
            media_type='character_design',
            metadata=task_data
        )
        
        return {
            'media_url': upload_result['url'],
            'payload_media_id': upload_result['id'],
            'metadata': {
                'resolution': '1024x1024',
                'file_size': len(image_result),
                'format': 'JPEG'
            }
        }
        
    except Exception as exc:
        self.retry(exc=exc, countdown=30, max_retries=3)
```

### Audio Processing Task

```python
# tasks/audio_tasks.py
@celery_app.task(bind=True, base=ProjectIsolatedTask)
def generate_character_voice(self, project_id: str, task_data: dict):
    """
    Generate character voice audio from text
    
    Args:
        project_id: Project isolation identifier
        task_data: {
            "text": "I've been expecting you, detective.",
            "character_voice_profile": "https://...",
            "emotion": "mysterious",
            "pace": "normal",
            "background_noise": "rain_ambience"
        }
    """
    try:
        self.update_state(state='PROGRESS', meta={'progress': 0.3, 'step': 'loading_voice_model'})
        
        # Load TTS model with character voice
        voice_model = load_voice_model(task_data['character_voice_profile'])
        
        self.update_state(state='PROGRESS', meta={'progress': 0.6, 'step': 'synthesizing_speech'})
        
        # Generate speech
        audio_result = voice_model.synthesize(
            text=task_data['text'],
            emotion=task_data['emotion'],
            pace=task_data['pace']
        )
        
        # Add background audio if specified
        if task_data.get('background_noise'):
            audio_result = add_background_audio(audio_result, task_data['background_noise'])
        
        self.update_state(state='PROGRESS', meta={'progress': 0.9, 'step': 'uploading_result'})
        
        # Upload to PayloadCMS
        upload_result = upload_media_to_payload(
            project_id=project_id,
            media_data=audio_result,
            media_type='dialogue_audio',
            metadata={
                'text': task_data['text'],
                'character_voice': task_data['character_voice_profile'],
                'duration': get_audio_duration(audio_result)
            }
        )
        
        return {
            'media_url': upload_result['url'],
            'payload_media_id': upload_result['id'],
            'metadata': {
                'duration': get_audio_duration(audio_result),
                'format': 'MP3',
                'sample_rate': 44100
            }
        }
        
    except Exception as exc:
        self.retry(exc=exc, countdown=45, max_retries=3)
```

## Base Task Class

```python
# tasks/base_task.py
from celery import Task
from typing import Any, Dict
import logging
from ..utils.monitoring import track_gpu_usage, track_task_metrics

class ProjectIsolatedTask(Task):
    """Base task class with project isolation and monitoring"""
    
    def __call__(self, project_id: str, *args, **kwargs):
        # Ensure project_id is always first parameter
        if not project_id:
            raise ValueError("project_id is required for all tasks")
            
        # Set up project-specific logging context
        logger = logging.getLogger(f"task.{project_id}")
        logger.info(f"Starting task {self.name} for project {project_id}")
        
        # Track resource usage
        with track_gpu_usage(project_id, self.name):
            with track_task_metrics(project_id, self.name):
                return super().__call__(project_id, *args, **kwargs)
    
    def on_success(self, retval: Any, task_id: str, args: tuple, kwargs: Dict):
        """Called on task success"""
        project_id = args[0] if args else kwargs.get('project_id')
        logging.info(f"Task {task_id} completed successfully for project {project_id}")
        
        # Send success webhook if callback_url provided
        callback_url = kwargs.get('callback_url')
        if callback_url:
            send_webhook(callback_url, {
                'task_id': task_id,
                'status': 'completed',
                'result': retval
            })
    
    def on_failure(self, exc: Exception, task_id: str, args: tuple, kwargs: Dict, einfo):
        """Called on task failure"""
        project_id = args[0] if args else kwargs.get('project_id')
        logging.error(f"Task {task_id} failed for project {project_id}: {str(exc)}")
        
        # Send failure webhook
        callback_url = kwargs.get('callback_url')
        if callback_url:
            send_webhook(callback_url, {
                'task_id': task_id,
                'status': 'failed',
                'error': str(exc)
            })
```

## Configuration

### Environment Variables

```bash
# .env
# Redis Configuration - Single URL for all Redis needs
# The application will automatically derive Celery broker (db=0) and result backend (db=1) from this URL
REDIS_URL=redis://default:password@your-redis-host:6379/0

# GPU Configuration
CUDA_VISIBLE_DEVICES=0,1,2,3
MAX_GPU_MEMORY_PER_TASK=8GB

# PayloadCMS Integration
PAYLOAD_API_URL=https://main-app.com/api
PAYLOAD_API_KEY=your_payload_api_key

# Cloudflare R2
R2_ENDPOINT=https://your-account.r2.cloudflarestorage.com
R2_ACCESS_KEY=your_access_key
R2_SECRET_KEY=your_secret_key
R2_BUCKET_NAME=ai-movie-assets

# API Configuration
API_HOST=0.0.0.0
API_PORT=8001
API_WORKERS=4
API_KEY=your_api_key_for_main_app

# Task Configuration
MAX_RETRY_ATTEMPTS=3
TASK_TIMEOUT=3600  # 1 hour
QUEUE_MAX_SIZE=1000

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
LOG_LEVEL=INFO
```

### Celery Configuration

```python
# app/celery_app.py
from celery import Celery
from .config import settings

celery_app = Celery("ai_movie_tasks")

celery_app.conf.update(
    broker_url=settings.get_celery_broker_url(),
    result_backend=settings.get_celery_result_backend(),
    
    # Task routing by project
    task_routes={
        'tasks.video_tasks.*': {'queue': 'gpu_heavy'},
        'tasks.image_tasks.*': {'queue': 'gpu_medium'},  
        'tasks.audio_tasks.*': {'queue': 'cpu_intensive'},
    },
    
    # Worker configuration
    worker_concurrency=4,  # Adjust based on GPU count
    worker_prefetch_multiplier=1,  # Prevent memory issues
    
    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=3600,  # 1 hour timeout
    task_soft_time_limit=3300,  # 55 minutes soft timeout
    
    # Results
    result_expires=86400,  # 24 hours
    result_compression='gzip',
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Import all task modules
from .tasks import video_tasks, image_tasks, audio_tasks
```

## Docker Configuration

### API Server Dockerfile

```dockerfile
# docker/Dockerfile.api
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Expose API port
EXPOSE 8001

# Start FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Worker Dockerfile

```dockerfile
# docker/Dockerfile.worker
FROM nvidia/cuda:11.8-devel-ubuntu20.04

# Install Python 3.11
RUN apt-get update && apt-get install -y \
    software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y \
    python3.11 \
    python3.11-pip \
    python3.11-venv \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN python3.11 -m pip install --no-cache-dir -r requirements.txt

# Install GPU-specific packages
RUN python3.11 -m pip install torch torchvision --extra-index-url https://download.pytorch.org/whl/cu118

# Copy application code
COPY app/ ./app/

# Start Celery worker
CMD ["python3.11", "-m", "celery", "worker", "-A", "app.celery_app:celery_app", "--loglevel=info", "--concurrency=2"]
```

### Docker Compose

```yaml
# docker/docker-compose.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}

  task-api:
    build:
      context: ..
      dockerfile: docker/Dockerfile.api
    ports:
      - "8001:8001"
    env_file:
      - ../.env
    depends_on:
      - redis
    volumes:
      - ../app:/app/app

  gpu-worker:
    build:
      context: ..
      dockerfile: docker/Dockerfile.worker
    env_file:
      - ../.env
    depends_on:
      - redis
    volumes:
      - ../app:/app/app
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  monitoring:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

volumes:
  redis_data:
```

## Integration with PayloadCMS

### Media Upload Service

```python
# services/payload_client.py
import httpx
from typing import Dict, Any, Optional
from ..config import settings

class PayloadMediaClient:
    def __init__(self):
        self.base_url = settings.PAYLOAD_API_URL
        self.api_key = settings.PAYLOAD_API_KEY
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
    
    async def upload_media(
        self, 
        project_id: str,
        media_data: bytes,
        filename: str,
        media_type: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Upload generated media to PayloadCMS"""
        
        files = {
            'file': (filename, media_data, get_mime_type(filename))
        }
        
        data = {
            'project_id': project_id,
            'media_type': media_type,
            'agent_generated': True,
            'generation_metadata': json.dumps(metadata)
        }
        
        response = await self.client.post(
            f"{self.base_url}/media",
            files=files,
            data=data
        )
        
        if response.status_code != 201:
            raise Exception(f"Failed to upload media: {response.text}")
        
        return response.json()
    
    async def update_media_embeddings(
        self,
        media_id: str, 
        embedding: List[float],
        description: str
    ):
        """Add embedding data to existing media"""
        
        response = await self.client.patch(
            f"{self.base_url}/media/{media_id}",
            json={
                'embedding': embedding,
                'description': description
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to update media embeddings: {response.text}")
        
        return response.json()
```

## Monitoring and Logging

### Task Metrics

```python
# utils/monitoring.py
from prometheus_client import Counter, Histogram, Gauge
import psutil
import GPUtil
from contextlib import contextmanager

# Metrics
TASK_COUNTER = Counter('tasks_total', 'Total tasks processed', ['project_id', 'task_type', 'status'])
TASK_DURATION = Histogram('task_duration_seconds', 'Task execution time', ['project_id', 'task_type'])
GPU_UTILIZATION = Gauge('gpu_utilization_percent', 'GPU utilization', ['gpu_id'])
MEMORY_USAGE = Gauge('memory_usage_bytes', 'Memory usage', ['project_id'])

@contextmanager
def track_task_metrics(project_id: str, task_type: str):
    """Track task execution metrics"""
    start_time = time.time()
    
    try:
        yield
        TASK_COUNTER.labels(project_id=project_id, task_type=task_type, status='success').inc()
    except Exception:
        TASK_COUNTER.labels(project_id=project_id, task_type=task_type, status='failure').inc()
        raise
    finally:
        duration = time.time() - start_time
        TASK_DURATION.labels(project_id=project_id, task_type=task_type).observe(duration)

@contextmanager  
def track_gpu_usage(project_id: str, task_name: str):
    """Track GPU usage during task execution"""
    try:
        yield
    finally:
        # Update GPU metrics
        gpus = GPUtil.getGPUs()
        for i, gpu in enumerate(gpus):
            GPU_UTILIZATION.labels(gpu_id=str(i)).set(gpu.load * 100)
        
        # Update memory usage
        memory_info = psutil.virtual_memory()
        MEMORY_USAGE.labels(project_id=project_id).set(memory_info.used)
```

## Error Handling and Recovery

### Task Retry Logic

```python
# Custom retry logic with exponential backoff
from celery.exceptions import Retry

class TaskRetryHandler:
    @staticmethod
    def should_retry(exc: Exception, attempt: int) -> bool:
        """Determine if task should be retried based on exception type"""
        
        # Network errors - retry
        if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)):
            return attempt < 3
            
        # GPU OOM errors - retry with backoff
        if "out of memory" in str(exc).lower():
            return attempt < 2
            
        # API rate limits - retry with longer backoff  
        if "rate limit" in str(exc).lower():
            return attempt < 5
            
        # File system errors - don't retry
        if isinstance(exc, (IOError, OSError)):
            return False
            
        # Unknown errors - retry once
        return attempt < 1
    
    @staticmethod
    def get_retry_delay(attempt: int, exc_type: str) -> int:
        """Calculate retry delay based on attempt and error type"""
        
        base_delays = {
            'network': 30,      # Network errors
            'gpu_memory': 120,  # GPU memory errors  
            'rate_limit': 300,  # Rate limit errors
            'default': 60       # Default errors
        }
        
        base_delay = base_delays.get(exc_type, base_delays['default'])
        return base_delay * (2 ** attempt)  # Exponential backoff
```

## Security Considerations

### API Key Authentication

```python
# middleware/auth.py
from fastapi import HTTPException, Depends, Header
from typing import Optional

async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key for all requests"""
    
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required in X-API-Key header"
        )
    
    # Verify against configured API keys
    valid_keys = settings.API_KEYS.split(',')
    if x_api_key not in valid_keys:
        raise HTTPException(
            status_code=401, 
            detail="Invalid API key"
        )
    
    return x_api_key

# Usage in endpoints
@app.post("/api/v1/tasks/submit")
async def submit_task(
    task_request: TaskSubmissionRequest,
    api_key: str = Depends(verify_api_key)
):
    # Task submission logic
    pass
```

### Project Isolation Middleware

```python
# middleware/project_isolation.py
from fastapi import HTTPException
import re

class ProjectIsolationMiddleware:
    """Ensure tasks can only access data from their project"""
    
    @staticmethod
    def validate_project_access(project_id: str, user_context: Dict):
        """Validate user has access to project"""
        
        # Validate project ID format
        if not re.match(r'^[a-zA-Z0-9_-]+$', project_id):
            raise HTTPException(400, "Invalid project ID format")
        
        # Check project access (implement based on your auth system)
        # This could check PayloadCMS for project permissions
        
        return True
    
    @staticmethod
    def sanitize_file_paths(project_id: str, file_path: str) -> str:
        """Ensure file paths are scoped to project"""
        
        # Remove any path traversal attempts
        clean_path = file_path.replace('..', '').replace('//', '/')
        
        # Ensure path starts with project prefix
        return f"projects/{project_id}/{clean_path.lstrip('/')}"
```

## Deployment Instructions

### 1. Environment Setup
```bash
# Clone and setup
git clone <repository>
cd celery-task-service

# Copy environment file
cp .env.example .env

# Edit environment variables
vim .env
```

### 2. Local Development
```bash
# Start Redis
docker run -d -p 6379:6379 redis:alpine

# Install dependencies
pip install -r requirements.txt

# Start API server
uvicorn app.main:app --reload --port 8001

# Start worker (in separate terminal)
celery -A app.celery_app:celery_app worker --loglevel=info
```

### 3. Docker Production Deployment
```bash
# Build and start all services
docker-compose -f docker/docker-compose.yml up -d

# Scale workers based on GPU count
docker-compose -f docker/docker-compose.yml up -d --scale gpu-worker=4

# Monitor logs
docker-compose -f docker/docker-compose.yml logs -f
```

### 4. Health Checks
```bash
# Check API health
curl http://localhost:8001/health

# Check worker status  
celery -A app.celery_app:celery_app inspect active

# Monitor queue
celery -A app.celery_app:celery_app inspect reserved
```

This standalone Celery/Redis task service provides robust, scalable processing for GPU-intensive AI movie generation tasks with proper project isolation, error handling, and integration capabilities.