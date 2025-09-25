# Quickstart Guide: AI Movie Platform - Task Service

## Overview
This guide demonstrates the complete workflow of the AI Movie Platform Task Service, from submitting a task to retrieving the generated media results.

## Prerequisites
- **Auto-Movie App** running on `http://localhost:3010` (with PayloadCMS)
- **Task Service API** running on `http://localhost:8001`
- **Redis server** running on port 6379 for task queue management
- **Celery workers** running for task processing
- **Valid API key** for authentication between services
- **MongoDB** running on port 27017 for PayloadCMS data
- **Neo4j** running on ports 7474/7687 (optional for enhanced context)

## Test Scenarios

### Scenario 1: Video Generation Task
**Goal**: Submit a video generation task and monitor its progress to completion.

#### Step 1: Submit Video Generation Task
```bash
curl -X POST http://localhost:8001/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "project_id": "detective_series_001",
    "task_type": "generate_video",
    "task_data": {
      "storyboard_images": [
        "https://example.com/frame1.jpg",
        "https://example.com/frame2.jpg"
      ],
      "scene_description": "Detective enters the dark alley",
      "camera_angle": "wide_shot",
      "lighting": "noir_dramatic",
      "character_positions": ["detective_center"],
      "audio_cues": ["footsteps", "rain_ambience"]
    },
    "priority": 1,
    "callback_url": "https://main-app.com/api/webhooks/task-complete",
    "metadata": {
      "user_id": "user123",
      "agent_id": "video_generation_agent",
      "scene_id": "scene_005"
    }
  }'
```

**Expected Response**:
```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "queued",
  "project_id": "detective_series_001",
  "estimated_duration": 300,
  "queue_position": 2,
  "created_at": "2025-09-24T10:30:00Z"
}
```

#### Step 2: Monitor Task Progress
```bash
# Check task status (repeat every 30 seconds)
curl -X GET http://localhost:8001/api/v1/tasks/abc123-def456-ghi789/status \
  -H "X-API-Key: your-api-key-here"
```

**Progress Responses**:

*Queued Status*:
```json
{
  "task_id": "abc123-def456-ghi789",
  "project_id": "detective_series_001",
  "status": "queued",
  "progress": 0.0,
  "current_step": "waiting_in_queue",
  "result": null,
  "error": null,
  "started_at": null,
  "completed_at": null
}
```

*Processing Status*:
```json
{
  "task_id": "abc123-def456-ghi789",
  "project_id": "detective_series_001",
  "status": "processing",
  "progress": 0.75,
  "current_step": "rendering_video",
  "result": null,
  "error": null,
  "started_at": "2025-09-24T10:30:15Z",
  "completed_at": null
}
```

*Completed Status*:
```json
{
  "task_id": "abc123-def456-ghi789",
  "project_id": "detective_series_001",
  "status": "completed",
  "progress": 1.0,
  "current_step": "upload_complete",
  "result": {
    "media_url": "https://r2.cloudflare.com/bucket/detective_series_001/video_abc123.mp4",
    "payload_media_id": "64f1b2c3a8d9e0f1",
    "metadata": {
      "duration": 7.0,
      "resolution": "1920x1080",
      "file_size": 15728640,
      "fps": 24
    }
  },
  "error": null,
  "started_at": "2025-09-24T10:30:15Z",
  "completed_at": "2025-09-24T10:35:30Z"
}
```

#### Step 3: Verify Media Upload
```bash
# Access the generated video directly
curl -I https://r2.cloudflare.com/bucket/detective_series_001/video_abc123.mp4

# Verify integration with PayloadCMS
curl -X GET https://main-app.com/api/media/64f1b2c3a8d9e0f1 \
  -H "Authorization: Bearer payload-api-token"
```

### Scenario 2: Image Generation Task
**Goal**: Generate a character design image with specific styling requirements.

#### Submit Image Task
```bash
curl -X POST http://localhost:8001/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "project_id": "detective_series_001",
    "task_type": "generate_image",
    "task_data": {
      "character_description": "Detective in 1920s noir style",
      "style_guide": "https://example.com/noir_style_guide.jpg",
      "reference_images": [
        "https://example.com/ref1.jpg",
        "https://example.com/ref2.jpg"
      ],
      "pose": "standing_confident",
      "lighting": "dramatic_shadow"
    },
    "priority": 2,
    "metadata": {
      "user_id": "user123",
      "agent_id": "character_design_agent",
      "character_id": "detective_main"
    }
  }'
```

**Expected Result**:
- Task queued successfully
- Processing completes in 2-3 minutes
- Generated 1024x1024 JPEG character image
- Media uploaded to PayloadCMS with generation metadata

### Scenario 3: Audio Synthesis Task
**Goal**: Generate character dialogue with specific voice characteristics.

#### Submit Audio Task
```bash
curl -X POST http://localhost:8001/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "project_id": "detective_series_001",
    "task_type": "process_audio",
    "task_data": {
      "text": "I have been expecting you, detective.",
      "character_voice_profile": "https://example.com/detective_voice.wav",
      "emotion": "mysterious",
      "pace": "normal",
      "background_noise": "rain_ambience"
    },
    "priority": 2,
    "metadata": {
      "user_id": "user123",
      "agent_id": "voice_synthesis_agent",
      "dialogue_id": "scene_005_line_001"
    }
  }'
```

**Expected Result**:
- High-quality MP3 audio file generated
- Voice matches character profile and emotional tone
- Background ambience properly mixed
- Audio metadata includes duration and sample rate

### Scenario 4: Project Task Management
**Goal**: View and manage all tasks for a specific project.

#### List Project Tasks
```bash
# Get all tasks for project with pagination
curl -X GET "http://localhost:8001/api/v1/projects/detective_series_001/tasks?page=1&limit=10" \
  -H "X-API-Key: your-api-key-here"

# Filter by status
curl -X GET "http://localhost:8001/api/v1/projects/detective_series_001/tasks?status=completed&limit=20" \
  -H "X-API-Key: your-api-key-here"

# Filter by task type
curl -X GET "http://localhost:8001/api/v1/projects/detective_series_001/tasks?task_type=generate_video" \
  -H "X-API-Key: your-api-key-here"
```

#### Cancel Running Task
```bash
curl -X DELETE http://localhost:8001/api/v1/tasks/abc123-def456-ghi789/cancel \
  -H "X-API-Key: your-api-key-here"
```

#### Retry Failed Task
```bash
curl -X POST http://localhost:8001/api/v1/tasks/failed-task-id/retry \
  -H "X-API-Key: your-api-key-here"
```

### Scenario 5: System Monitoring
**Goal**: Monitor worker status and system health.

#### Check System Health
```bash
curl -X GET http://localhost:8001/api/v1/health
```

#### Monitor Worker Status
```bash
curl -X GET http://localhost:8001/api/v1/workers/status \
  -H "X-API-Key: your-api-key-here"
```

**Expected Response**:
```json
{
  "workers": [
    {
      "worker_id": "worker-gpu-001",
      "worker_type": "gpu_heavy",
      "status": "busy",
      "current_task_id": "abc123-def456-ghi789",
      "gpu_utilization": 0.85,
      "memory_usage": 12884901888,
      "tasks_completed": 47,
      "last_heartbeat": "2025-09-24T10:35:00Z"
    }
  ],
  "total_workers": 4,
  "active_workers": 3,
  "gpu_utilization": 0.72
}
```

## Integration Testing Checklist

### Task Lifecycle Validation
- [ ] Task submission returns valid task_id and queued status
- [ ] Task progresses through statuses: queued → processing → completed
- [ ] Progress percentage increases monotonically from 0.0 to 1.0
- [ ] Current step descriptions update appropriately
- [ ] Completion time is recorded when task finishes

### Media Generation Validation
- [ ] Generated media files are accessible via returned URLs
- [ ] Media metadata matches expected format and quality
- [ ] Files are properly uploaded to Cloudflare R2
- [ ] PayloadCMS entries are created with correct metadata
- [ ] File sizes are within expected ranges

### Project Isolation Validation
- [ ] Tasks from different projects cannot access each other's data
- [ ] Project-specific storage paths are correctly enforced
- [ ] Task listing by project returns only relevant tasks
- [ ] Cross-project data leakage does not occur

### Error Handling Validation
- [ ] Invalid API keys return 401 Unauthorized
- [ ] Malformed requests return 400 Bad Request with clear error messages
- [ ] Task cancellation works for queued and processing tasks
- [ ] Failed tasks can be retried successfully
- [ ] GPU memory errors trigger automatic retry with backoff

### Performance Validation
- [ ] Task processing completes within expected time limits
- [ ] Multiple concurrent tasks can be processed simultaneously
- [ ] System handles queue backlog gracefully
- [ ] Worker utilization is properly balanced
- [ ] Memory usage remains within acceptable bounds

## Troubleshooting

### Common Issues

**Task Stuck in Queued Status**:
- Check if Celery workers are running: `celery -A app.celery_app inspect active`
- Verify Redis connection: `redis-cli ping`
- Check worker logs for error messages

**Task Fails with GPU Memory Error**:
- Monitor GPU usage: `nvidia-smi`
- Reduce concurrent task limits
- Implement GPU memory cleanup in worker code

**Media Upload Failures**:
- Verify Cloudflare R2 credentials and permissions
- Check PayloadCMS API connectivity
- Monitor network timeouts and retry logic

**API Authentication Issues**:
- Verify API key is included in X-API-Key header
- Check API key is valid and not expired
- Ensure API key has required permissions

This quickstart guide validates all major functionality and integration points of the Task Service API, ensuring reliable operation in production environments.