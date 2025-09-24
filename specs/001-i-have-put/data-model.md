# Data Model: AI Movie Platform - Celery/Redis Task Service

## Core Entities

### Task
**Purpose**: Represents a processing job submitted to the task service  
**Storage**: Redis (task metadata), Celery backend (execution state)  
**Lifecycle**: queued → processing → completed/failed/cancelled

**Attributes**:
- `task_id`: UUID - Unique identifier for the task
- `project_id`: String - Project isolation identifier
- `task_type`: Enum - Type of task (video_generation, image_generation, audio_synthesis)
- `status`: Enum - Current task status (queued, processing, completed, failed, cancelled)
- `priority`: Integer - Task priority (1=high, 2=normal, 3=low)
- `task_data`: JSON - Task-specific parameters and configuration
- `progress`: Float - Completion percentage (0.0 to 1.0)
- `current_step`: String - Current processing step description
- `result`: JSON - Task result data including media URLs and metadata
- `error`: String - Error message if task failed
- `callback_url`: String - Optional webhook URL for completion notifications
- `metadata`: JSON - Additional context data (user_id, agent_id, scene_id)
- `created_at`: Timestamp - Task creation time
- `started_at`: Timestamp - Processing start time
- `completed_at`: Timestamp - Processing completion time
- `estimated_duration`: Integer - Estimated processing time in seconds
- `queue_position`: Integer - Position in queue when queued

**Validation Rules**:
- `task_id` must be unique across all tasks
- `project_id` must match pattern `^[a-zA-Z0-9_-]+$`
- `task_type` must be one of the supported types
- `priority` must be 1, 2, or 3
- `progress` must be between 0.0 and 1.0
- `callback_url` must be valid HTTP/HTTPS URL if provided

**State Transitions**:
```
queued → processing → completed
queued → processing → failed
queued → cancelled
processing → cancelled
failed → queued (retry)
```

### Project
**Purpose**: Isolation boundary for tasks and media assets  
**Storage**: Redis (project metadata)  
**Lifecycle**: Long-lived entity managed by main application

**Attributes**:
- `project_id`: String - Unique project identifier
- `project_name`: String - Human-readable project name
- `task_count`: Integer - Total number of tasks submitted
- `active_tasks`: Integer - Number of currently processing tasks
- `storage_prefix`: String - Cloudflare R2 storage path prefix
- `created_at`: Timestamp - Project creation time
- `last_activity`: Timestamp - Last task submission or completion

**Validation Rules**:
- `project_id` must match pattern `^[a-zA-Z0-9_-]+$`
- `project_id` must be unique across all projects
- `storage_prefix` must be valid path format

### Media Result
**Purpose**: Generated content with metadata and storage information  
**Storage**: Cloudflare R2 (media files), PayloadCMS (metadata), Redis (cached metadata)  
**Lifecycle**: Created during task completion, persisted long-term

**Attributes**:
- `media_id`: UUID - Unique identifier for the media file
- `task_id`: UUID - Reference to the task that generated this media
- `project_id`: String - Project association
- `media_type`: Enum - Type of media (video_segment, character_design, dialogue_audio)
- `media_url`: String - Direct URL to media file in Cloudflare R2
- `payload_media_id`: String - Reference to PayloadCMS media entry
- `file_name`: String - Original file name
- `file_size`: Integer - File size in bytes
- `duration`: Float - Media duration in seconds (for video/audio)
- `resolution`: String - Media resolution (for video/images)
- `format`: String - File format (MP4, JPEG, MP3, etc.)
- `generation_metadata`: JSON - Parameters used for generation
- `created_at`: Timestamp - Media creation time

**Validation Rules**:
- `media_url` must be valid HTTPS URL
- `file_size` must be positive integer
- `duration` must be positive for video/audio media
- `resolution` must match format "WIDTHxHEIGHT" for visual media

### Task Queue
**Purpose**: Ordered collection of pending tasks with priority management  
**Storage**: Redis (queue data structure)  
**Lifecycle**: Dynamic, managed by Celery

**Attributes**:
- `queue_name`: String - Queue identifier (e.g., "gpu_heavy", "gpu_medium", "cpu_intensive")
- `project_id`: String - Project association for project-specific queues
- `pending_count`: Integer - Number of tasks waiting in queue
- `priority_distribution`: JSON - Count of tasks by priority level
- `estimated_wait_time`: Integer - Estimated time until next task processing

### Worker Status
**Purpose**: Information about available processing resources  
**Storage**: Redis (worker heartbeat data)  
**Lifecycle**: Dynamic, updated by worker processes

**Attributes**:
- `worker_id`: String - Unique worker identifier
- `worker_type`: Enum - Worker capability (gpu_heavy, gpu_medium, cpu_intensive)
- `status`: Enum - Worker status (active, idle, busy, offline)
- `current_task_id`: UUID - Currently processing task (if any)
- `gpu_utilization`: Float - GPU usage percentage (0.0 to 1.0)
- `memory_usage`: Integer - Memory usage in bytes
- `tasks_completed`: Integer - Total tasks completed by this worker
- `last_heartbeat`: Timestamp - Last status update time

### Processing Progress
**Purpose**: Real-time status updates for task execution  
**Storage**: Redis (temporary data, expires after task completion)  
**Lifecycle**: Created when task starts, updated during processing, cleaned up after completion

**Attributes**:
- `task_id`: UUID - Reference to the associated task
- `progress_percentage`: Float - Current completion percentage
- `current_step`: String - Description of current processing step
- `step_start_time`: Timestamp - When current step began
- `estimated_remaining`: Integer - Estimated seconds until completion
- `detailed_status`: JSON - Step-specific progress information

## Relationships

### Task → Project
- **Type**: Many-to-One
- **Constraint**: All tasks must belong to a valid project
- **Cascade**: Tasks are retained when project is deleted (soft delete)

### Task → Media Result  
- **Type**: One-to-Many
- **Constraint**: Media results must reference a valid completed task
- **Cascade**: Media results are deleted when task is deleted

### Task → Processing Progress
- **Type**: One-to-One (active tasks only)
- **Constraint**: Progress records exist only for active tasks
- **Cascade**: Progress is deleted when task completes or fails

### Project → Task Queue
- **Type**: One-to-Many (conceptual)
- **Constraint**: Queues can be project-specific or shared
- **Implementation**: Queue routing based on project_id

### Worker Status → Task
- **Type**: One-to-One (active assignments)
- **Constraint**: Workers can process only one task at a time
- **Implementation**: Worker assignment tracking in Redis

## Data Storage Strategy

### Redis Data Organization
```
# Task metadata
tasks:{task_id} → Task JSON
tasks:by_project:{project_id} → Set of task_ids
tasks:by_status:{status} → Set of task_ids

# Project data
projects:{project_id} → Project JSON
projects:active → Set of active project_ids

# Worker status
workers:{worker_id} → Worker Status JSON
workers:active → Set of active worker_ids

# Progress tracking
progress:{task_id} → Processing Progress JSON (TTL: 1 hour after completion)

# Queue management (handled by Celery)
celery:queue:{queue_name} → Celery queue data
```

### Cloudflare R2 Organization
```
# Media files organized by project
{bucket}/projects/{project_id}/video/{task_id}/output.mp4
{bucket}/projects/{project_id}/image/{task_id}/output.jpg  
{bucket}/projects/{project_id}/audio/{task_id}/output.mp3
```

### PayloadCMS Integration
- Media entries reference R2 URLs and include generation metadata
- Project association maintained through custom fields
- Search and filtering capabilities for generated content
- Version tracking for iterative generation workflows

## Performance Considerations

### Indexing Strategy
- Redis sets for fast project-based task lookup
- Time-based expiration for completed task progress data
- Worker status caching with automatic cleanup

### Data Retention
- Task metadata: Retained indefinitely for audit purposes
- Processing progress: Expired 1 hour after task completion  
- Worker status: Expired 5 minutes after last heartbeat
- Media files: Retained indefinitely, managed by PayloadCMS lifecycle

### Scalability
- Horizontal partitioning possible by project_id
- Redis clustering support for high availability
- Media storage scales independently in Cloudflare R2
- Task queue scaling handled by Celery worker processes