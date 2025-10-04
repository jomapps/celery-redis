# How to Use Celery-Redis Task Service

## Overview
The Celery-Redis Task Service handles all GPU-intensive and time-consuming operations for the AI Movie Platform. This document provides everything you need to integrate with the task service from any application in the system.

## Service Endpoints

### **Base URLs**
- **Development**: `http://localhost:8001`
- **Staging**: `https://tasks.ngrok.pro`
- **Production**: `https://tasks.ft.tc`

### **Authentication**
All requests require the `X-API-Key` header:
```bash
X-API-Key: your_celery_api_key_here
```

## API Reference

### 1. Submit Task

**POST** `/api/v1/tasks/submit`

Submit a new task for background processing.

#### Request
```json
{
  "project_id": "detective_series_001",
  "task_type": "generate_video",
  "task_data": {
    "storyboard_images": ["url1", "url2"],
    "scene_description": "Detective enters the dark alley",
    "camera_angle": "wide_shot",
    "lighting": "noir_dramatic",
    "duration": 7
  },
  "priority": 1,
  "callback_url": "https://auto-movie.ft.tc/api/webhooks/task-complete",
  "metadata": {
    "user_id": "user123",
    "agent_id": "video_generation_agent",
    "session_id": "session456"
  }
}
```

#### Response
```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "queued",
  "project_id": "detective_series_001",
  "estimated_duration": 300,
  "queue_position": 5,
  "created_at": "2025-01-15T10:30:00Z"
}
```

#### Task Types Available
- `generate_video` - Create 7-second video segments
- `generate_image` - Create character designs, concept art
- `generate_character_voice` - Synthesize character dialogue
- `process_audio` - Audio mixing and enhancement
- `render_animation` - Character animation rendering
- `evaluate_department` - AI-powered department evaluation for project readiness (Aladdin integration)
- `automated_gather_creation` - Automated content gathering and organization (long-running, 10min timeout)
- `test_prompt` - Test agent prompts with immediate results

### 2. Get Task Status

**GET** `/api/v1/tasks/{task_id}/status`

Get current status and progress of a task.

#### Response
```json
{
  "task_id": "abc123-def456-ghi789",
  "project_id": "detective_series_001",
  "status": "processing",
  "progress": 0.75,
  "current_step": "rendering_video",
  "result": {
    "media_url": "https://media.ft.tc/project_001/video_abc123.mp4",
    "payload_media_id": "64f1b2c3a8d9e0f1",
    "metadata": {
      "duration": 7.0,
      "resolution": "1920x1080",
      "file_size": 15728640
    }
  },
  "error": null,
  "started_at": "2025-01-15T10:30:15Z",
  "completed_at": "2025-01-15T10:35:30Z",
  "processing_time": 315
}
```

#### Status Values
- `queued` - Task is waiting to be processed
- `processing` - Task is currently being executed
- `completed` - Task finished successfully
- `failed` - Task encountered an error
- `cancelled` - Task was cancelled by user

### 3. Get Project Tasks

**GET** `/api/v1/projects/{project_id}/tasks`

Get all tasks for a specific project with filtering. Tasks are stored in Redis and expire after 24 hours.

#### Query Parameters
- `status` - Filter by task status (queued, processing, completed, failed)
- `task_type` - Filter by task type (evaluate_department, generate_video, etc.)
- `page` - Page number (default: 1)
- `limit` - Items per page (default: 20, max: 100)

#### Example Request
```bash
# Get all tasks for a project
curl -H "X-API-Key: YOUR_KEY" \
  "https://tasks.ft.tc/api/v1/projects/68df4dab400c86a6a8cf40c6/tasks"

# Get only completed tasks
curl -H "X-API-Key: YOUR_KEY" \
  "https://tasks.ft.tc/api/v1/projects/68df4dab400c86a6a8cf40c6/tasks?status=completed"

# Get evaluation tasks only
curl -H "X-API-Key: YOUR_KEY" \
  "https://tasks.ft.tc/api/v1/projects/68df4dab400c86a6a8cf40c6/tasks?task_type=evaluate_department"
```

#### Response
```json
{
  "tasks": [
    {
      "task_id": "abc123-def456-ghi789",
      "project_id": "68df4dab400c86a6a8cf40c6",
      "task_type": "evaluate_department",
      "status": "completed",
      "task_data": {
        "department_slug": "story",
        "department_number": 1,
        "threshold": 80
      },
      "result": {
        "department": "story",
        "rating": 89,
        "evaluation_result": "pass"
      },
      "created_at": "2025-10-04T10:20:00Z",
      "updated_at": "2025-10-04T10:20:06Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 5,
    "total_pages": 1
  }
}
```

#### Important Notes
- Tasks are stored in Redis and **expire after 24 hours**
- Only tasks submitted after 2025-10-04 are tracked (when storage was implemented)
- Tasks are sorted by creation time (newest first)

### 4. Cancel Task

**DELETE** `/api/v1/tasks/{task_id}`

Cancel a queued or running task. The task will be gracefully terminated with SIGTERM.

#### Request
```bash
curl -X DELETE https://tasks.ft.tc/api/v1/tasks/{task_id} \
  -H "X-API-Key: your_celery_api_key_here"
```

#### Response (Queued Task)
```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "cancelled",
  "message": "Task was queued and has been revoked",
  "previous_state": "queued",
  "cancelled_at": "2025-10-04T04:00:00Z"
}
```

#### Response (Running Task)
```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "cancelled",
  "message": "Task was running and has been terminated",
  "previous_state": "processing",
  "cancelled_at": "2025-10-04T04:00:00Z"
}
```

#### Response (Already Completed)
```json
{
  "detail": "Task has already completed successfully and cannot be cancelled"
}
```

#### Cancellation Behavior

| Task State | Action | Result |
|------------|--------|--------|
| **PENDING** (queued) | Revoke without termination | Task removed from queue |
| **STARTED** (running) | Revoke with SIGTERM | Task process terminated gracefully |
| **SUCCESS** (completed) | No action | HTTP 400 error |
| **FAILURE** (failed) | No action | HTTP 400 error |
| **REVOKED** (cancelled) | No action | Returns already cancelled status |

### 5. Retry Task

**POST** `/api/v1/tasks/{task_id}/retry`

Retry a failed task with the same parameters.

#### Response
```json
{
  "new_task_id": "xyz789-uvw456-rst123",
  "original_task_id": "abc123-def456-ghi789",
  "status": "queued",
  "message": "Task retry submitted successfully"
}
```

### 6. Health Check

**GET** `/api/v1/health`

Check service health and system status.

#### Response
```json
{
  "status": "healthy",
  "redis_status": "connected",
  "worker_count": 4,
  "queue_sizes": {
    "gpu_heavy": 3,
    "gpu_medium": 1,
    "cpu_intensive": 0
  },
  "system_load": {
    "cpu_percent": 45.2,
    "memory_percent": 62.8,
    "gpu_utilization": [85.5, 72.1, 0.0, 0.0]
  },
  "uptime": 86400
}
```

### 7. Get Task Metrics

**GET** `/api/v1/tasks/metrics`

Get real-time task queue metrics and statistics. Metrics are stored in Redis and shared across all API and worker processes.

#### Request
```bash
curl https://tasks.ft.tc/api/v1/tasks/metrics \
  -H "X-API-Key: your_celery_api_key_here"
```

#### Response
```json
{
  "metrics": {
    "total_tasks": 1523,
    "completed_tasks": 1398,
    "failed_tasks": 89,
    "retried_tasks": 36,
    "cancelled_tasks": 0,
    "success_rate": 91.8,
    "failure_rate": 5.8,
    "average_durations": {},
    "currently_running": 4
  },
  "timestamp": "2025-10-04T04:00:00Z"
}
```

#### Metrics Explained

| Metric | Description |
|--------|-------------|
| `total_tasks` | Total number of tasks submitted (cumulative, persists across restarts) |
| `completed_tasks` | Successfully completed tasks (cumulative) |
| `failed_tasks` | Tasks that failed after all retries (cumulative) |
| `retried_tasks` | Number of retry attempts made (cumulative) |
| `cancelled_tasks` | Tasks cancelled by users (cumulative) |
| `success_rate` | Percentage of successful tasks |
| `failure_rate` | Percentage of failed tasks |
| `average_durations` | Average execution time per task type (currently not tracked) |
| `currently_running` | Number of tasks currently being processed |

#### Important Notes
- Metrics are stored in Redis and **persist across service restarts**
- Metrics are **cumulative** since the last Redis reset
- Metrics are **shared** across all API and worker processes
- Only tasks submitted after 2025-10-04 are counted (when storage was implemented)

### 8. Get Task Queue Health

**GET** `/api/v1/tasks/health`

Get task queue health status with alerts and anomaly detection.

#### Request
```bash
curl https://tasks.ft.tc/api/v1/tasks/health \
  -H "X-API-Key: your_celery_api_key_here"
```

#### Response (Healthy)
```json
{
  "status": "healthy",
  "metrics": {
    "total_tasks": 1523,
    "completed_tasks": 1398,
    "failed_tasks": 89,
    "success_rate": 91.8,
    "failure_rate": 5.8,
    "currently_running": 4
  },
  "alerts": [],
  "timestamp": "2025-10-04T04:00:00Z"
}
```

#### Response (With Alerts)
```json
{
  "status": "warning",
  "metrics": {
    "total_tasks": 1523,
    "success_rate": 88.5,
    "failure_rate": 11.5
  },
  "alerts": [
    {
      "severity": "warning",
      "message": "Elevated failure rate: 11.50%",
      "metric": "failure_rate",
      "value": 11.5
    },
    {
      "severity": "warning",
      "message": "Task abc-123-def running for 485 seconds",
      "metric": "task_duration",
      "value": 485,
      "task_id": "abc-123-def"
    }
  ],
  "timestamp": "2025-10-04T04:00:00Z"
}
```

#### Health Status Values

| Status | Description | Action Required |
|--------|-------------|-----------------|
| `healthy` | All systems normal | None |
| `warning` | Elevated metrics detected | Monitor closely |
| `critical` | Severe issues detected | Immediate attention required |

#### Alert Thresholds

| Alert | Warning | Critical |
|-------|---------|----------|
| **Failure Rate** | >10% | >20% |
| **Task Duration** | >8 minutes | >9.5 minutes |
| **Memory Usage** | >1.5GB | >1.9GB |

## Task Type Specifications

### Video Generation Task

Generate 7-second video segments from storyboards.

```json
{
  "task_type": "generate_video",
  "task_data": {
    "storyboard_images": ["https://media.ft.tc/storyboard1.jpg"],
    "scene_description": "Detective walks through rain-soaked alley",
    "camera_angle": "wide_shot",
    "lighting": "dramatic_noir",
    "character_positions": [
      {
        "character_id": "detective_jones",
        "position": "center_frame",
        "action": "walking_slowly"
      }
    ],
    "duration": 7,
    "fps": 24,
    "resolution": "1920x1080"
  }
}
```

**Result Structure:**
```json
{
  "media_url": "https://media.ft.tc/detective_001/scene_001.mp4",
  "payload_media_id": "64f1b2c3a8d9e0f1",
  "metadata": {
    "duration": 7.0,
    "resolution": "1920x1080",
    "fps": 24,
    "file_size": 15728640,
    "generation_model": "runway_gen3"
  }
}
```

### Image Generation Task

Create character designs, concept art, and environment images.

```json
{
  "task_type": "generate_image",
  "task_data": {
    "prompt": "1920s detective in film noir style, wearing trench coat",
    "style_guide": "https://media.ft.tc/style_guide.jpg",
    "reference_images": ["https://media.ft.tc/ref1.jpg"],
    "character_id": "detective_jones",
    "pose": "standing_confident",
    "lighting": "dramatic_shadow",
    "resolution": "1024x1024",
    "quality": "high"
  }
}
```

### Character Voice Generation Task

Generate character dialogue with specific voice profiles.

```json
{
  "task_type": "generate_character_voice",
  "task_data": {
    "text": "I've been expecting you, detective.",
    "character_voice_profile": "https://media.ft.tc/voices/detective_voice.json",
    "emotion": "mysterious",
    "pace": "slow",
    "background_noise": "rain_ambience",
    "output_format": "mp3",
    "sample_rate": 44100
  }
}
```

### Prompt Testing Task

Test AI agent prompts with immediate results (used by prompt management system).

```json
{
  "task_type": "test_prompt",
  "task_data": {
    "prompt_id": "character_creator_v2_1",
    "prompt_template": "Create a character based on: {{concept}}",
    "agent_type": "character_creator",
    "test_parameters": {
      "concept": "mysterious librarian with dark secrets",
      "genre": "thriller"
    },
    "test_result_id": "test_result_123"
  }
}
```

## Client Integration Examples

### JavaScript/TypeScript (Auto-Movie App)

```typescript
// src/services/taskService.ts
class TaskService {
  private baseUrl: string
  private apiKey: string

  constructor() {
    this.baseUrl = process.env.NEXT_PUBLIC_TASK_SERVICE_URL || 'http://localhost:8001'
    this.apiKey = process.env.CELERY_TASK_API_KEY || ''
  }

  async submitTask(taskData: TaskSubmission): Promise<TaskResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/tasks/submit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey
      },
      body: JSON.stringify(taskData)
    })

    if (!response.ok) {
      throw new Error(`Task submission failed: ${response.statusText}`)
    }

    return response.json()
  }

  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    const response = await fetch(`${this.baseUrl}/api/v1/tasks/${taskId}/status`, {
      headers: {
        'X-API-Key': this.apiKey
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to get task status: ${response.statusText}`)
    }

    return response.json()
  }

  async pollTaskUntilComplete(
    taskId: string, 
    onProgress?: (status: TaskStatus) => void,
    pollInterval: number = 2000
  ): Promise<TaskStatus> {
    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const status = await this.getTaskStatus(taskId)
          
          if (onProgress) {
            onProgress(status)
          }

          if (status.status === 'completed') {
            resolve(status)
          } else if (status.status === 'failed') {
            reject(new Error(status.error || 'Task failed'))
          } else if (status.status === 'cancelled') {
            reject(new Error('Task was cancelled'))
          } else {
            // Still processing, continue polling
            setTimeout(poll, pollInterval)
          }
        } catch (error) {
          reject(error)
        }
      }

      poll()
    })
  }
}

export const taskService = new TaskService()
```

### Python (MCP Brain Service)

```python
# mcp_brain_service/services/task_client.py
import httpx
import asyncio
import os
from typing import Dict, Any, Optional, Callable

class TaskServiceClient:
    def __init__(self):
        self.base_url = os.getenv('TASK_SERVICE_URL', 'http://localhost:8001')
        self.api_key = os.getenv('CELERY_TASK_API_KEY', '')
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            headers={'X-API-Key': self.api_key}
        )
    
    async def submit_task(
        self, 
        project_id: str,
        task_type: str,
        task_data: Dict[str, Any],
        priority: int = 2,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Submit a new task for processing"""
        
        payload = {
            'project_id': project_id,
            'task_type': task_type,
            'task_data': task_data,
            'priority': priority,
            'metadata': metadata or {}
        }
        
        response = await self.client.post(
            f'{self.base_url}/api/v1/tasks/submit',
            json=payload
        )
        
        response.raise_for_status()
        return response.json()
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get current task status"""
        
        response = await self.client.get(
            f'{self.base_url}/api/v1/tasks/{task_id}/status'
        )
        
        response.raise_for_status()
        return response.json()
    
    async def wait_for_completion(
        self,
        task_id: str,
        timeout: int = 600,  # 10 minutes
        poll_interval: int = 2
    ) -> Dict[str, Any]:
        """Wait for task to complete with timeout"""
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            status = await self.get_task_status(task_id)
            
            if status['status'] == 'completed':
                return status
            elif status['status'] == 'failed':
                raise Exception(f"Task failed: {status.get('error', 'Unknown error')}")
            elif status['status'] == 'cancelled':
                raise Exception("Task was cancelled")
            
            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise Exception(f"Task timeout after {timeout} seconds")
            
            await asyncio.sleep(poll_interval)
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
```

## Usage Patterns

### 1. Fire-and-Forget Tasks

For tasks where you don't need to wait for results:

```typescript
// Submit task and store task_id for later checking
const task = await taskService.submitTask({
  project_id: "my_project",
  task_type: "generate_image",
  task_data: { /* ... */ },
  callback_url: "https://my-app.com/api/webhooks/task-complete"
})

// Store task_id in database for later reference
await database.updateProject(projectId, {
  pending_tasks: [...existingTasks, task.task_id]
})
```

### 2. Real-time Progress Monitoring

For tasks where you need to show progress to users:

```typescript
// Submit task and poll for updates
const task = await taskService.submitTask(taskData)

const finalResult = await taskService.pollTaskUntilComplete(
  task.task_id,
  (status) => {
    // Update UI with progress
    updateProgressBar(status.progress)
    updateStatusText(status.current_step)
  }
)

// Use final result
console.log('Video generated:', finalResult.result.media_url)
```

### 3. Batch Task Processing

For processing multiple related tasks:

```typescript
// Submit multiple tasks
const taskPromises = scenes.map(scene => 
  taskService.submitTask({
    project_id: projectId,
    task_type: "generate_video",
    task_data: scene
  })
)

const tasks = await Promise.all(taskPromises)

// Wait for all to complete
const results = await Promise.all(
  tasks.map(task => taskService.pollTaskUntilComplete(task.task_id))
)

console.log('All scenes generated:', results.length)
```

### 4. Error Handling and Retries

```typescript
async function generateVideoWithRetry(sceneData: any, maxRetries = 3): Promise<any> {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const task = await taskService.submitTask({
        project_id: sceneData.project_id,
        task_type: "generate_video",
        task_data: sceneData
      })

      return await taskService.pollTaskUntilComplete(task.task_id)
      
    } catch (error) {
      console.error(`Attempt ${attempt} failed:`, error.message)
      
      if (attempt === maxRetries) {
        throw new Error(`Video generation failed after ${maxRetries} attempts`)
      }
      
      // Exponential backoff
      await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, attempt)))
    }
  }
}
```

## Webhook Integration

The Task Service supports **automatic webhook callbacks** to notify your application when tasks complete. This eliminates the need for polling and provides real-time notifications.

### Overview

When you submit a task with a `callback_url`, the service will automatically POST to that URL when the task completes (successfully or with failure).

**Features:**
- ✅ Automatic delivery on task completion
- ✅ Retry logic with exponential backoff (3 retries)
- ✅ 30-second timeout per request
- ✅ Support for both success and failure scenarios
- ✅ Custom metadata passthrough
- ✅ Standardized payload format

### Submitting a Task with Callback

```bash
curl -X POST https://tasks.ft.tc/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "project_id": "detective_series_001",
    "task_type": "generate_video",
    "callback_url": "https://your-app.com/api/webhooks/task-complete",
    "task_data": {
      "scene_description": "Detective enters dark alley",
      "duration": 7
    },
    "metadata": {
      "userId": "user-123",
      "testResultId": "result-456",
      "sessionId": "session-789"
    }
  }'
```

### Success Webhook Payload

When a task completes successfully:

```json
{
  "task_id": "abc123-def456-ghi789",
  "project_id": "detective_series_001",
  "status": "completed",
  "result": {
    "media_url": "https://media.ft.tc/detective_001/video_001.mp4",
    "payload_media_id": "64f1b2c3a8d9e0f1",
    "metadata": {
      "duration": 7.0,
      "resolution": "1920x1080",
      "file_size": 15728640
    }
  },
  "processing_time": 315,
  "completed_at": "2025-01-15T10:35:30Z",
  "metadata": {
    "userId": "user-123",
    "testResultId": "result-456",
    "sessionId": "session-789"
  }
}
```

### Failure Webhook Payload

When a task fails:

```json
{
  "task_id": "abc123-def456-ghi789",
  "project_id": "detective_series_001",
  "status": "failed",
  "error": "Task execution failed: Invalid scene description format",
  "traceback": "Traceback (most recent call last):\n  File ...",
  "failed_at": "2025-01-15T10:35:30Z",
  "metadata": {
    "userId": "user-123",
    "testResultId": "result-456",
    "sessionId": "session-789"
  }
}
```

### Webhook Handler Implementation

#### Node.js/Express Example

```typescript
// pages/api/webhooks/task-complete.ts
import { NextApiRequest, NextApiResponse } from 'next'

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  // Only accept POST requests
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  const { task_id, status, result, error, project_id, metadata } = req.body

  try {
    if (status === 'completed') {
      console.log(`✅ Task ${task_id} completed successfully`)

      // Update project with completed media
      await updateProjectMedia(project_id, {
        task_id,
        media_url: result.media_url,
        payload_media_id: result.payload_media_id,
        metadata: result.metadata
      })

      // Notify user via WebSocket or other real-time channel
      if (metadata?.userId) {
        await notifyUser(metadata.userId, {
          type: 'task_completed',
          task_id,
          project_id,
          result
        })
      }

      // Update test result if applicable
      if (metadata?.testResultId) {
        await updateTestResult(metadata.testResultId, {
          status: 'completed',
          media_url: result.media_url
        })
      }

    } else if (status === 'failed') {
      console.error(`❌ Task ${task_id} failed:`, error)

      // Log task failure
      await logTaskFailure(task_id, {
        project_id,
        error,
        metadata
      })

      // Notify user of failure
      if (metadata?.userId) {
        await notifyUser(metadata.userId, {
          type: 'task_failed',
          task_id,
          project_id,
          error
        })
      }

      // Update test result with failure
      if (metadata?.testResultId) {
        await updateTestResult(metadata.testResultId, {
          status: 'failed',
          error
        })
      }
    }

    // Always respond with 200 to acknowledge receipt
    res.status(200).json({ received: true })

  } catch (error) {
    console.error('Webhook processing error:', error)
    res.status(500).json({ error: 'Internal server error' })
  }
}
```

#### Python/FastAPI Example

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

app = FastAPI()

class WebhookPayload(BaseModel):
    task_id: str
    project_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    traceback: Optional[str] = None
    processing_time: Optional[float] = None
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@app.post("/api/webhooks/task-complete")
async def handle_task_webhook(payload: WebhookPayload):
    try:
        if payload.status == "completed":
            print(f"✅ Task {payload.task_id} completed successfully")

            # Update database
            await update_task_status(
                task_id=payload.task_id,
                status="completed",
                result=payload.result,
                processing_time=payload.processing_time
            )

            # Notify user
            if payload.metadata and "userId" in payload.metadata:
                await notify_user(
                    user_id=payload.metadata["userId"],
                    message={
                        "type": "task_completed",
                        "task_id": payload.task_id,
                        "result": payload.result
                    }
                )

        elif payload.status == "failed":
            print(f"❌ Task {payload.task_id} failed: {payload.error}")

            await update_task_status(
                task_id=payload.task_id,
                status="failed",
                error=payload.error
            )

            if payload.metadata and "userId" in payload.metadata:
                await notify_user(
                    user_id=payload.metadata["userId"],
                    message={
                        "type": "task_failed",
                        "task_id": payload.task_id,
                        "error": payload.error
                    }
                )

        return {"received": True}

    except Exception as e:
        print(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

### Webhook Delivery Behavior

#### Retry Logic

The Task Service implements automatic retry with exponential backoff:

1. **Initial attempt**: Immediate delivery after task completion
2. **Retry 1**: After 1 second (if initial fails)
3. **Retry 2**: After 2 seconds (if retry 1 fails)
4. **Retry 3**: After 4 seconds (if retry 2 fails)

**Total attempts**: 4 (1 initial + 3 retries)

#### Success Criteria

A webhook delivery is considered successful if your endpoint returns:
- HTTP 200 (OK)
- HTTP 201 (Created)
- HTTP 202 (Accepted)
- HTTP 204 (No Content)

Any other status code will trigger a retry.

#### Timeout

Each webhook request has a **30-second timeout**. If your endpoint doesn't respond within this time, the request will be retried.

#### Failure Handling

If all retry attempts fail:
- The task result is still stored in the brain service
- An error is logged in the Task Service logs
- You can still query the task status via `/api/v1/tasks/{task_id}/status`

### Best Practices

1. **Respond Quickly**: Acknowledge webhook receipt immediately (return 200), then process asynchronously
   ```typescript
   // Good: Immediate response
   res.status(200).json({ received: true })
   processWebhookAsync(payload) // Process in background

   // Bad: Long processing before response
   await longRunningProcess(payload)
   res.status(200).json({ received: true })
   ```

2. **Idempotency**: Handle duplicate webhook deliveries gracefully
   ```typescript
   // Check if already processed
   const existing = await db.webhooks.findOne({ task_id })
   if (existing) {
     return res.status(200).json({ received: true, duplicate: true })
   }
   ```

3. **Error Handling**: Always return appropriate HTTP status codes
   ```typescript
   try {
     await processWebhook(payload)
     res.status(200).json({ received: true })
   } catch (error) {
     console.error('Error:', error)
     res.status(500).json({ error: 'Processing failed' })
   }
   ```

4. **Logging**: Log all webhook receipts for debugging
   ```typescript
   console.log(`Webhook received: ${task_id} - ${status}`)
   ```

5. **Security**: Validate webhook source (see Security section below)

### Security Considerations

#### IP Whitelisting (Recommended)

```typescript
const ALLOWED_IPS = [
  '10.0.0.1',  // Task Service IP
  '10.0.0.2'   // Backup Task Service IP
]

app.post('/api/webhooks/task-complete', (req, res, next) => {
  const clientIP = req.ip || req.connection.remoteAddress

  if (!ALLOWED_IPS.includes(clientIP)) {
    return res.status(403).json({ error: 'Forbidden' })
  }

  next()
}, handleWebhook)
```

#### HTTPS Only

Always use HTTPS endpoints for webhook URLs:
```json
{
  "callback_url": "https://your-app.com/api/webhooks/task-complete"
}
```

#### Request Validation

Validate the webhook payload structure:
```typescript
if (!task_id || !status || !project_id) {
  return res.status(400).json({ error: 'Invalid payload' })
}
```

### Testing Webhooks

#### Using ngrok for Local Development

```bash
# Start ngrok to expose your local server
ngrok http 3010

# Use the ngrok URL as your callback_url
# Example: https://abc123.ngrok.io/api/webhooks/task-complete
```

#### Mock Webhook Server

```javascript
const express = require('express')
const app = express()

app.post('/api/webhooks/task-complete', express.json(), (req, res) => {
  console.log('Received webhook:', JSON.stringify(req.body, null, 2))
  res.status(200).json({ received: true })
})

app.listen(3010, () => {
  console.log('Mock webhook server running on port 3010')
})
```

### Monitoring Webhooks

#### Checking Logs

```bash
# View webhook delivery logs
docker logs celery-redis-api-1 | grep "webhook"

# View successful deliveries
docker logs celery-redis-api-1 | grep "Webhook sent successfully"

# View failed deliveries
docker logs celery-redis-api-1 | grep "Failed to send webhook"
```

#### Log Examples

**Success:**
```
INFO: Webhook sent successfully callback_url=https://... status_code=200 task_id=abc123
```

**Retry:**
```
WARNING: Webhook request failed callback_url=https://... error=Connection timeout attempt=1
```

**Failure:**
```
ERROR: Failed to send webhook after all retries callback_url=https://... task_id=abc123
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Webhook not received | Callback URL not accessible | Verify URL is publicly accessible |
| Timeout errors | Handler takes too long | Respond immediately, process async |
| Duplicate webhooks | Retry after slow response | Implement idempotency check |
| 403 Forbidden | IP whitelist blocking | Add Task Service IP to whitelist |

### Additional Resources

- [Complete Webhook Documentation](./webhook-callbacks.md)
- [Webhook Example Script](../examples/webhook_example.py)
- [System Integration Guide](./system-integration.md)

## Error Handling

### Common Error Responses

#### Authentication Error (401)
```json
{
  "error": "authentication_failed",
  "message": "Invalid or missing API key"
}
```

#### Task Not Found (404)
```json
{
  "error": "task_not_found", 
  "message": "Task with ID 'abc123' not found"
}
```

#### Validation Error (400)
```json
{
  "error": "validation_error",
  "message": "Invalid task data",
  "details": {
    "project_id": "Project ID is required",
    "task_data.duration": "Duration must be between 1 and 30 seconds"
  }
}
```

#### Service Unavailable (503)
```json
{
  "error": "service_unavailable",
  "message": "All workers are busy, please try again later",
  "retry_after": 120
}
```

## Department Evaluation Task (Aladdin Integration)

The `evaluate_department` task provides AI-powered evaluation of movie production departments for the Aladdin Project Readiness system.

### Overview

This task evaluates department readiness based on gathered content and provides:
- Quality rating (0-100)
- Pass/fail result based on threshold
- Comprehensive evaluation summary
- Specific issues identified
- Actionable improvement suggestions

### Submit Evaluation Task

**POST** `/api/v1/tasks/submit`

```json
{
  "project_id": "68df4dab400c86a6a8cf40c6",
  "task_type": "evaluate_department",
  "task_data": {
    "department_slug": "story",
    "department_number": 1,
    "gather_data": [
      {
        "content": "A young detective arrives in a small coastal town to investigate mysterious disappearances...",
        "summary": "Main story premise",
        "context": "Mystery thriller genre"
      },
      {
        "content": "Three-act structure with clear character arcs...",
        "summary": "Story structure",
        "context": "Narrative framework"
      }
    ],
    "previous_evaluations": [
      {
        "department": "concept",
        "rating": 85,
        "summary": "Strong conceptual foundation"
      }
    ],
    "threshold": 80
  },
  "priority": 1,
  "callback_url": "https://aladdin.ngrok.pro/api/webhooks/evaluation-complete",
  "metadata": {
    "user_id": "user123",
    "department_id": "dept-story-001"
  }
}
```

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `department_slug` | string | Yes | Department name (e.g., "story", "character", "production") |
| `department_number` | integer | Yes | Sequential department number (1-12) |
| `gather_data` | array | Yes | Array of gathered content items with content, summary, context |
| `previous_evaluations` | array | No | Array of previous department evaluations for context |
| `threshold` | integer | Yes | Minimum passing score (0-100), default: 80 |

### Evaluation Response (Webhook)

```json
{
  "task_id": "abc123-def456-ghi789",
  "project_id": "68df4dab400c86a6a8cf40c6",
  "status": "completed",
  "result": {
    "department": "story",
    "rating": 85,
    "evaluation_result": "pass",
    "evaluation_summary": "The story department shows strong narrative structure with well-developed characters and clear three-act progression. The protagonist's journey is compelling and the conflict is well-established.",
    "issues": [
      "Character backstory needs more depth",
      "Third act resolution feels rushed",
      "Supporting character arcs underdeveloped"
    ],
    "suggestions": [
      "Add flashback scenes to establish character motivation",
      "Extend climax sequence by 2-3 minutes",
      "Develop supporting character relationships"
    ],
    "iteration_count": 1,
    "processing_time": 45.2,
    "metadata": {
      "model": "gpt-4",
      "tokens_used": 1500,
      "confidence_score": 0.85
    }
  },
  "completed_at": "2025-01-15T10:35:30Z",
  "metadata": {
    "user_id": "user123",
    "department_id": "dept-story-001"
  }
}
```

### Supported Departments

The evaluation system supports these department types:

1. **Story** - Narrative structure, plot, themes
2. **Character** - Character profiles, arcs, relationships
3. **Production** - Resources, budget, timeline
4. **Visual** - Visual style, cinematography, effects
5. **Audio** - Sound design, music, dialogue
6. **Editing** - Pacing, transitions, continuity
7. **Marketing** - Promotion, distribution, audience
8. **Legal** - Rights, contracts, compliance
9. **Technical** - Equipment, software, infrastructure
10. **Post-Production** - Color grading, VFX, final mix
11. **Distribution** - Release strategy, platforms
12. **Archive** - Asset management, preservation

### Performance

- **Expected Duration**: 30-120 seconds
- **Token Usage**: 1000-5000 tokens per evaluation
- **Queue**: `cpu_intensive`
- **Timeout**: 300 seconds maximum

### Example Usage (TypeScript)

```typescript
// Submit evaluation task
const response = await fetch('https://tasks.ft.tc/api/v1/tasks/submit', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': process.env.CELERY_API_KEY
  },
  body: JSON.stringify({
    project_id: projectId,
    task_type: 'evaluate_department',
    task_data: {
      department_slug: 'story',
      department_number: 1,
      gather_data: gatherDataArray,
      previous_evaluations: previousEvals,
      threshold: 80
    },
    callback_url: `${process.env.APP_URL}/api/webhooks/evaluation-complete`,
    metadata: {
      user_id: userId,
      department_id: departmentId
    }
  })
});

const { task_id } = await response.json();

// Handle webhook callback
export async function POST(req: Request) {
  const payload = await req.json();

  if (payload.status === 'completed') {
    const { rating, evaluation_result, evaluation_summary, issues, suggestions } = payload.result;

    // Update department status
    await updateDepartment({
      id: payload.metadata.department_id,
      rating,
      status: evaluation_result,
      summary: evaluation_summary,
      issues,
      suggestions
    });

    // Notify user
    await notifyUser(payload.metadata.user_id, {
      type: 'evaluation_complete',
      department: payload.result.department,
      rating,
      result: evaluation_result
    });
  }

  return Response.json({ received: true });
}
```

### Error Handling

**Insufficient Data:**
```json
{
  "result": {
    "rating": 0,
    "evaluation_result": "fail",
    "evaluation_summary": "Insufficient data provided for evaluation",
    "issues": ["No gather data provided"],
    "suggestions": ["Gather content for department"]
  }
}
```

**AI Service Failure:**
```json
{
  "result": {
    "rating": 50,
    "evaluation_summary": "Evaluation could not be completed: AI service timeout",
    "issues": ["AI evaluation service unavailable"],
    "suggestions": ["Retry evaluation when service is available"]
  }
}
```

### Additional Resources

- [Complete Evaluation Task Documentation](./evaluate-department-task.md)
- [Implementation Details](./requests/IMPLEMENTATION_COMPLETE.md)

---

## Task Queue Configuration

### Queue Types

The task service uses dedicated queues for different workload types:

| Queue | Purpose | Concurrency | Timeout | Use Cases |
|-------|---------|-------------|---------|-----------|
| `gpu_heavy` | GPU-intensive tasks | 2 | 10 min | Video generation, 3D rendering |
| `gpu_medium` | Moderate GPU tasks | 4 | 5 min | Image generation, style transfer |
| `cpu_intensive` | CPU-heavy tasks | 4 | 10 min | Audio processing, data analysis, automated gather creation |
| `default` | Light tasks | 8 | 2 min | Text processing, API calls |

### Task Routing

Tasks are automatically routed to appropriate queues based on task type:

```python
# Automatic routing configuration
task_routes = {
    'generate_video': {'queue': 'gpu_heavy'},
    'generate_image': {'queue': 'gpu_medium'},
    'process_audio': {'queue': 'cpu_intensive'},
    'automated_gather_creation': {'queue': 'cpu_intensive'},
    'evaluate_department': {'queue': 'cpu_intensive'},
}
```

### Timeout Configuration

Each task type has specific timeout settings:

| Task Type | Soft Timeout | Hard Timeout | Behavior |
|-----------|--------------|--------------|----------|
| `automated_gather_creation` | 9 minutes | 10 minutes | Graceful shutdown at 9min, force kill at 10min |
| `generate_video` | 9 minutes | 10 minutes | Same as above |
| `generate_image` | 4.5 minutes | 5 minutes | Shorter timeout for faster tasks |
| `evaluate_department` | 4.5 minutes | 5 minutes | AI evaluation with timeout protection |

**Soft Timeout**: Task receives `SoftTimeLimitExceeded` exception and can clean up gracefully.
**Hard Timeout**: Task is forcefully terminated with `SIGKILL`.

### Retry Configuration

Failed tasks are automatically retried with exponential backoff:

```
Retry Schedule:
- Attempt 1: Immediate
- Attempt 2: After 60 seconds
- Attempt 3: After 120 seconds (2 minutes)
- Attempt 4: After 240 seconds (4 minutes)
- Final Failure: After 3 failed attempts
```

**Retry Conditions**:
- Connection errors (Redis, external APIs)
- Timeout errors
- Temporary service unavailability
- Resource exhaustion (will retry when resources available)

**No Retry**:
- Invalid input data
- Authentication failures
- Permanent errors (404, 403)

### Resource Limits

Worker resource limits prevent memory leaks and ensure stability:

| Setting | Value | Purpose |
|---------|-------|---------|
| **Worker Memory Limit** | 2GB | Restart worker if memory exceeds limit |
| **Tasks Per Worker** | 10 | Restart worker after processing 10 tasks |
| **Worker Concurrency** | 4 | Number of parallel task processes |
| **Prefetch Multiplier** | 1 | Tasks to prefetch per worker (prevents hoarding) |

### Monitoring & Alerts

The task queue includes built-in monitoring with automatic alerts:

**Monitored Metrics**:
- Task success/failure rates
- Average task durations
- Queue lengths
- Worker memory usage
- Long-running tasks

**Automatic Alerts**:
- ⚠️ **Warning**: Failure rate >10%, task running >8 minutes
- 🚨 **Critical**: Failure rate >20%, worker memory >1.9GB

**Access Monitoring**:
```bash
# Get current metrics
curl -H "X-API-Key: $API_KEY" https://tasks.ft.tc/api/v1/tasks/metrics

# Get health status with alerts
curl -H "X-API-Key: $API_KEY" https://tasks.ft.tc/api/v1/tasks/health
```

### Task Cancellation

Tasks can be cancelled at any time:

**Cancellation Process**:
1. Client sends `DELETE /api/v1/tasks/{task_id}`
2. System checks task state
3. If queued: Task removed from queue
4. If running: SIGTERM sent to worker process
5. Worker has 30 seconds to clean up gracefully
6. After 30 seconds: SIGKILL if still running

**Graceful Shutdown**:
Tasks should handle cancellation gracefully:
```python
from celery.exceptions import SoftTimeLimitExceeded

try:
    # Task logic here
    process_data()
except SoftTimeLimitExceeded:
    # Clean up resources
    cleanup()
    raise
```

### Performance Expectations

| Task Type | Avg Duration | P95 Duration | Success Rate |
|-----------|--------------|--------------|--------------|
| `generate_video` | 4-6 minutes | 8 minutes | >95% |
| `generate_image` | 30-60 seconds | 2 minutes | >98% |
| `process_audio` | 15-30 seconds | 1 minute | >99% |
| `evaluate_department` | 1-2 minutes | 4 minutes | >95% |
| `automated_gather_creation` | 3-5 minutes | 8 minutes | >90% |

### Configuration Documentation

For detailed configuration information, see:
- [Task Queue Configuration Guide](./task-queue-configuration.md)
- [Task Queue Implementation](./TASK_QUEUE_IMPLEMENTATION.md)
- [Quick Reference Guide](./TASK_QUEUE_QUICK_REFERENCE.md)

---

## Best Practices

### 1. Project ID Isolation
Always use meaningful project IDs to ensure proper data isolation:
```typescript
const projectId = `${userId}_${projectName}_${Date.now()}`
```

### 2. Task Priority Management
Use priority levels strategically:
- `1` (High) - User-initiated tasks requiring immediate feedback
- `2` (Normal) - Background processing tasks  
- `3` (Low) - Batch processing, cleanup tasks

### 3. Timeout Handling
Set appropriate timeouts based on task type:
- Video generation: 5-10 minutes
- Image generation: 1-3 minutes  
- Audio processing: 30 seconds - 2 minutes
- Text processing: 10-30 seconds

### 4. Resource Management
Monitor system load and queue sizes:
```typescript
const health = await fetch(`${taskServiceUrl}/api/v1/health`)
const { queue_sizes, system_load } = await health.json()

if (queue_sizes.gpu_heavy > 10) {
  // Warn user about delays or defer non-critical tasks
}
```

### 5. Task Metadata
Include useful metadata for debugging and analytics:
```typescript
const task = await taskService.submitTask({
  // ... task data
  metadata: {
    user_id: currentUser.id,
    session_id: currentSession.id,
    agent_id: "video_generation_agent",
    workflow_step: "scene_generation",
    ui_context: "episode_editor"
  }
})
```

## Rate Limits

- **Task Submissions**: 100 requests per minute per API key
- **Status Checks**: 1000 requests per minute per API key  
- **Concurrent Tasks**: 50 per project (configurable)

## Support

### Health Monitoring
Check service status: `GET /api/v1/health`

### Debug Information
Include these details when reporting issues:
- Task ID
- Project ID  
- Task type and data
- Timestamp
- Error messages
- Expected vs actual behavior

### Performance Expectations
| Task Type | Typical Duration | Max Duration |
|-----------|-----------------|--------------|
| Image Generation | 30-90 seconds | 5 minutes |
| Video Generation | 2-8 minutes | 15 minutes |
| Voice Generation | 10-30 seconds | 2 minutes |
| Prompt Testing | 5-15 seconds | 1 minute |
| Department Evaluation | 30-120 seconds | 5 minutes |

---

## Recent Updates (2025-10-04)

### ✅ Fixed: Tasks Not Being Processed

**Issue**: The task service was accepting submissions but not processing them.

**Root Causes**:
1. **Worker Queue Configuration**: The Celery worker was only listening to the default `celery` queue, but the `evaluate_department` task was being sent to the `cpu_intensive` queue.
2. **No Task Persistence**: Tasks were being processed but not saved to storage, so the API couldn't track them.

**Fixes Applied**:

1. **Worker Queue Configuration** (See `CELERY_WORKER_FIX.md`):
   - Updated `ecosystem.config.js` to configure worker with all queues
   - Worker now listens to: `celery`, `cpu_intensive`, `gpu_heavy`, `gpu_medium`
   - Added unique hostname: `celery-redis-worker@%h` to avoid conflicts

2. **Task Storage Implementation** (See `TASK_STORAGE_FIX.md`):
   - Implemented Redis-based `TaskStorage` class for persistent task tracking
   - Tasks are now saved to Redis when submitted
   - Task status is updated when tasks complete or fail
   - Metrics are shared across API and worker processes via Redis

**Verification**:
```bash
# Check worker is listening to all queues
celery -A app.celery_app inspect active_queues

# Should show:
# -> celery-redis-worker@vmd177401: OK
#   * celery
#   * cpu_intensive
#   * gpu_heavy
#   * gpu_medium

# Submit a test task
curl -X POST https://tasks.ft.tc/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{
    "project_id": "test-project",
    "task_type": "evaluate_department",
    "task_data": {
      "department_slug": "story",
      "department_number": 1,
      "gather_data": [],
      "threshold": 80
    }
  }'

# Wait 10 seconds, then check if task appears
curl -H "X-API-Key: YOUR_KEY" \
  "https://tasks.ft.tc/api/v1/projects/test-project/tasks"

# Check metrics
curl -H "X-API-Key: YOUR_KEY" \
  "https://tasks.ft.tc/api/v1/tasks/metrics"
```

**Important Notes**:
- Tasks submitted **before** 2025-10-04 were processed but not persisted (won't appear in task lists)
- New tasks submitted **after** the fix are fully tracked and queryable
- The service now requires Redis for both Celery queuing AND task storage
- Tasks expire after 24 hours to prevent Redis from growing indefinitely

**Verification Completed**: 2025-10-04 10:31:56 UTC
- ✅ Test task submitted and processed successfully
- ✅ Task appeared in project tasks list
- ✅ Metrics updated correctly (total_tasks: 1, completed_tasks: 1, success_rate: 100%)
- ✅ End-to-end flow confirmed working

---

## Troubleshooting

### Service Returns 404 for `/api/v1/tasks/submit`

**Symptom**: The task submission endpoint returns `404 Not Found` even though the service is running and health checks pass.

**Root Cause**: Missing Python dependencies in the virtual environment causing silent import failures. The FastAPI routers fail to load due to `ImportError`, which is caught by the try-except block in `app/main.py` (lines 101-111).

**Diagnosis**:
```bash
# Check if routers are loaded in OpenAPI schema
curl -s https://tasks.ft.tc/openapi.json | python3 -c "import sys, json; data = json.load(sys.stdin); print('Available paths:'); [print(f'  {path}') for path in sorted(data['paths'].keys())]"

# If only /health and /api/v1/health are shown, routers are not loaded

# Test imports directly
cd /var/www/celery-redis
/var/www/celery-redis/venv/bin/python -c "from app.api import tasks, projects, workers; print('SUCCESS')"
```

**Solution**:
```bash
# 1. Identify missing dependencies
cd /var/www/celery-redis
/var/www/celery-redis/venv/bin/python -c "from app.api import tasks"
# Look for ModuleNotFoundError in output

# 2. Install missing dependencies
/var/www/celery-redis/venv/bin/pip install -r requirements.txt

# Or install specific missing package
/var/www/celery-redis/venv/bin/pip install requests==2.31.0

# 3. Verify imports work
/var/www/celery-redis/venv/bin/python -c "from app.api import tasks; print('Routes:', [r.path for r in tasks.router.routes])"

# 4. Restart the service
pm2 restart celery-redis-api

# 5. Verify endpoint is now available
curl -X POST https://tasks.ft.tc/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"project_id":"test","task_type":"evaluate_department","task_data":{"department_slug":"story","department_number":1,"gather_data":[],"threshold":80}}'
```

**Prevention**:
- Always run `pip install -r requirements.txt` after pulling code changes
- Check PM2 logs for import errors: `pm2 logs celery-redis-api --lines 100`
- Monitor the OpenAPI schema to ensure all expected endpoints are registered
- Consider adding a startup health check that verifies all routers are loaded

### Tasks Stuck in "Queued" Status

**Symptom**: Tasks are submitted successfully but never start processing.

**Diagnosis**:
```bash
# Check if Celery workers are running
pm2 list | grep celery-worker

# Check worker logs
pm2 logs celery-worker --lines 50

# Check Redis connection
redis-cli ping

# Check task queue size
redis-cli llen celery
```

**Solution**:
```bash
# Restart Celery worker
pm2 restart celery-worker

# If Redis is down, restart it
sudo systemctl restart redis-server
```

### 401 Unauthorized Errors

**Symptom**: All API requests return `401 Unauthorized`.

**Diagnosis**:
```bash
# Check if API key is set correctly
echo $CELERY_API_KEY

# Verify API key in .env file
grep API_KEY /var/www/celery-redis/.env
```

**Solution**:
```bash
# Use the correct API key from .env file
API_KEY=$(grep "^API_KEY=" /var/www/celery-redis/.env | cut -d'=' -f2)

# Test with correct key
curl -H "X-API-Key: $API_KEY" https://tasks.ft.tc/api/v1/health
```

### Service Not Responding

**Symptom**: Service is not responding to any requests.

**Diagnosis**:
```bash
# Check if service is running
pm2 list | grep celery-redis-api

# Check service logs
pm2 logs celery-redis-api --lines 100

# Check if port is listening
netstat -tlnp | grep 8001
```

**Solution**:
```bash
# Restart the service
pm2 restart celery-redis-api

# If that doesn't work, check for port conflicts
sudo lsof -i :8001

# Check nginx configuration
sudo nginx -t
sudo systemctl restart nginx
```

### Checking Service Health

**Quick Health Check**:
```bash
# Basic health check
curl https://tasks.ft.tc/health

# Detailed health check (requires API key)
curl -H "X-API-Key: $API_KEY" https://tasks.ft.tc/api/v1/tasks/health

# Check metrics
curl -H "X-API-Key: $API_KEY" https://tasks.ft.tc/api/v1/tasks/metrics
```

### Viewing Logs

**PM2 Logs**:
```bash
# View API logs
pm2 logs celery-redis-api

# View worker logs
pm2 logs celery-worker

# View last 100 lines
pm2 logs celery-redis-api --lines 100

# View errors only
pm2 logs celery-redis-api --err
```

**Log Locations**:
- API logs: `/var/log/celery-redis-api-out-*.log` and `/var/log/celery-redis-api-error-*.log`
- Worker logs: `/var/log/celery-worker-out-*.log` and `/var/log/celery-worker-error-*.log`

---

This service handles all the heavy computational work so your applications can focus on user experience and workflow management!