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

Get all tasks for a specific project with filtering.

#### Query Parameters
- `status` - Filter by task status
- `task_type` - Filter by task type
- `page` - Page number (default: 1)
- `limit` - Items per page (default: 20, max: 100)
- `since` - ISO datetime for tasks created after this time

#### Response
```json
{
  "tasks": [
    {
      "task_id": "abc123-def456-ghi789",
      "task_type": "generate_video",
      "status": "completed",
      "created_at": "2025-01-15T10:30:00Z",
      "completed_at": "2025-01-15T10:35:30Z",
      "result_url": "https://media.ft.tc/project_001/video_abc123.mp4"
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

### 4. Cancel Task

**DELETE** `/api/v1/tasks/{task_id}/cancel`

Cancel a queued or processing task.

#### Response
```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "cancelled",
  "message": "Task cancelled successfully"
}
```

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

If you provide a `callback_url` when submitting tasks, the service will POST results to your endpoint:

### Webhook Payload

```json
{
  "task_id": "abc123-def456-ghi789",
  "project_id": "detective_series_001",
  "status": "completed",
  "result": {
    "media_url": "https://media.ft.tc/detective_001/video_001.mp4",
    "payload_media_id": "64f1b2c3a8d9e0f1"
  },
  "processing_time": 315,
  "completed_at": "2025-01-15T10:35:30Z"
}
```

### Webhook Handler Example

```typescript
// pages/api/webhooks/task-complete.ts
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  const { task_id, status, result, project_id } = req.body

  try {
    if (status === 'completed') {
      // Update project with completed media
      await updateProjectMedia(project_id, {
        task_id,
        media_url: result.media_url,
        payload_media_id: result.payload_media_id
      })
      
      // Notify user via WebSocket
      notifyUser(project_id, {
        type: 'task_completed',
        task_id,
        result
      })
      
    } else if (status === 'failed') {
      // Handle task failure
      await logTaskFailure(task_id, result.error)
      
      notifyUser(project_id, {
        type: 'task_failed',
        task_id,
        error: result.error
      })
    }

    res.status(200).json({ received: true })
  } catch (error) {
    console.error('Webhook processing error:', error)
    res.status(500).json({ error: 'Internal server error' })
  }
}
```

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

This service handles all the heavy computational work so your applications can focus on user experience and workflow management!