# Task Storage Fix - Task Tracking Issue

## Problem Summary

After fixing the Celery worker queue configuration, tasks were being processed successfully, but:
- The `/api/v1/projects/{project_id}/tasks` endpoint returned empty results
- The `/api/v1/tasks/metrics` endpoint showed `total_tasks: 0`
- Tasks were being executed but not tracked or persisted

## Root Cause Analysis

### Issue 1: No Task Persistence Layer

The API was creating task objects but **never saving them anywhere**:

```python
# app/api/tasks.py - BEFORE FIX (lines 55-67)
task = Task(
    task_id=task_id,
    project_id=task_request.project_id,
    task_type=task_request.task_type,
    status=TaskStatus.QUEUED,
    # ... other fields
)

# Task object created but NEVER SAVED!
# Only submitted to Celery, no persistence
```

**Result**: Tasks were submitted to Celery and processed, but the API had no record of them.

### Issue 2: Projects Endpoint Not Implemented

The `/api/v1/projects/{project_id}/tasks` endpoint had placeholder code:

```python
# app/api/projects.py - BEFORE FIX (lines 48-49)
# TODO: Retrieve tasks from Redis with project isolation
# TODO: Apply filters and pagination

# Return empty result for now
return ProjectTasksResponse(tasks=[], ...)
```

**Result**: Always returned empty list, even if tasks existed.

### Issue 3: Metrics Only Tracked in Worker Process

The monitoring module used Celery signals which only fire in the worker process:

```python
# app/config/monitoring.py
task_metrics = {
    "total_tasks": 0,  # In-memory in worker process
    "completed_tasks": 0,
    # ...
}

@task_prerun.connect  # Only fires in worker
def task_prerun_handler(...):
    task_metrics["total_tasks"] += 1
```

**Result**: Metrics were tracked in the worker's memory, but the API (separate process) couldn't access them.

## Solution

### Fix 1: Implemented Redis-Based Task Storage

Created `app/storage/task_storage.py` with a `TaskStorage` class that:
- Saves tasks to Redis when submitted
- Updates task status when completed/failed
- Stores tasks by project for easy retrieval
- Tracks metrics in Redis (shared across processes)

Key features:
```python
class TaskStorage:
    def save_task(self, task: Task) -> bool:
        """Save task to Redis with project association"""
        
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Retrieve task by ID"""
        
    def update_task_status(self, task_id: str, status: str, ...):
        """Update task status and result"""
        
    def get_project_tasks(self, project_id: str, ...):
        """Get all tasks for a project with filtering"""
        
    def increment_metric(self, metric_name: str, value: int = 1):
        """Increment shared metrics in Redis"""
```

### Fix 2: Updated Task Submission to Save Tasks

Modified `app/api/tasks.py` to save tasks to storage:

```python
# AFTER FIX
task = Task(...)

# Submit to Celery
task_result = evaluate_department.delay(...)

# Update with Celery task ID
if task_result:
    task.task_id = uuid.UUID(task_result.id)
    task.status = TaskStatus.PROCESSING

# Save to storage (NEW!)
task_storage.save_task(task)

# Increment metrics (NEW!)
task_storage.increment_metric("total_tasks")
```

### Fix 3: Implemented Projects Tasks Endpoint

Updated `app/api/projects.py` to retrieve tasks from storage:

```python
# AFTER FIX
tasks = task_storage.get_project_tasks(
    project_id=validated_project_id,
    status=status,
    task_type=task_type,
    limit=limit,
    offset=offset
)

total = task_storage.get_project_tasks_count(
    project_id=validated_project_id,
    status=status,
    task_type=task_type
)

return ProjectTasksResponse(tasks=tasks, pagination={...})
```

### Fix 4: Updated Metrics Endpoint

Modified `app/api/tasks.py` to use Redis-based metrics:

```python
# AFTER FIX
redis_metrics = task_storage.get_metrics()

metrics = {
    "total_tasks": redis_metrics.get("total_tasks", 0),
    "completed_tasks": redis_metrics.get("completed_tasks", 0),
    # ... shared across API and worker processes
}
```

### Fix 5: Added Task Status Updates on Completion

Updated `app/tasks/base_task.py` to update storage in lifecycle hooks:

```python
def on_success(self, retval, task_id, args, kwargs):
    # Update task status in storage (NEW!)
    task_storage.update_task_status(
        task_id=task_id,
        status="completed",
        result=retval
    )
    
    # Increment completion metrics (NEW!)
    task_storage.increment_metric("completed_tasks")
    
    # ... existing webhook and brain service code

def on_failure(self, exc, task_id, args, kwargs, einfo):
    # Update task status in storage (NEW!)
    task_storage.update_task_status(
        task_id=task_id,
        status="failed",
        error=str(exc)
    )
    
    # Increment failure metrics (NEW!)
    task_storage.increment_metric("failed_tasks")
    
    # ... existing webhook and brain service code
```

## Verification

After the fix:

1. **Task Submission**: Tasks are saved to Redis when submitted
   ```bash
   curl -X POST https://tasks.ft.tc/api/v1/tasks/submit \
     -H "X-API-Key: YOUR_KEY" \
     -d '{"project_id": "test", "task_type": "evaluate_department", ...}'
   ```

2. **Project Tasks**: Endpoint returns actual tasks
   ```bash
   curl -H "X-API-Key: YOUR_KEY" \
     "https://tasks.ft.tc/api/v1/projects/PROJECT_ID/tasks"
   # Returns: {"tasks": [...], "pagination": {...}}
   ```

3. **Metrics**: Shared across API and worker
   ```bash
   curl -H "X-API-Key: YOUR_KEY" \
     "https://tasks.ft.tc/api/v1/tasks/metrics"
   # Returns: {"metrics": {"total_tasks": N, "completed_tasks": M, ...}}
   ```

## Data Structure in Redis

### Task Data
```
Key: task:{task_id}
Type: Hash
Fields:
  - task_id: UUID
  - project_id: string
  - task_type: string
  - status: queued|processing|completed|failed
  - task_data: JSON
  - result: JSON
  - error: string
  - created_at: ISO timestamp
  - updated_at: ISO timestamp
Expiration: 24 hours
```

### Project Tasks Index
```
Key: project_tasks:{project_id}
Type: Set
Members: [task_id1, task_id2, ...]
Expiration: 24 hours
```

### Metrics
```
Key: task_metrics
Type: Hash
Fields:
  - total_tasks: integer
  - completed_tasks: integer
  - failed_tasks: integer
  - retried_tasks: integer
  - cancelled_tasks: integer
No expiration (persistent counters)
```

## Important Notes

1. **Redis is required**: The service now depends on Redis for both Celery queuing AND task storage
2. **Task expiration**: Tasks expire after 24 hours to prevent Redis from growing indefinitely
3. **Metrics are cumulative**: Metrics persist across restarts (stored in Redis)
4. **Cross-process sharing**: API and worker processes share the same task state via Redis

## Testing

To test the complete flow:

```bash
# 1. Submit a task
TASK_RESPONSE=$(curl -s -X POST https://tasks.ft.tc/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{
    "project_id": "test-project-123",
    "task_type": "evaluate_department",
    "task_data": {
      "department_slug": "story",
      "department_number": 1,
      "gather_data": [],
      "threshold": 80
    }
  }')

echo "Task submitted: $TASK_RESPONSE"

# 2. Wait a few seconds for processing
sleep 10

# 3. Check project tasks
curl -s -H "X-API-Key: YOUR_KEY" \
  "https://tasks.ft.tc/api/v1/projects/test-project-123/tasks" | jq

# 4. Check metrics
curl -s -H "X-API-Key: YOUR_KEY" \
  "https://tasks.ft.tc/api/v1/tasks/metrics" | jq
```

## Related Files

- `app/storage/task_storage.py` - Task storage implementation
- `app/storage/__init__.py` - Storage module exports
- `app/api/tasks.py` - Task submission and metrics endpoints
- `app/api/projects.py` - Project tasks endpoint
- `app/tasks/base_task.py` - Task lifecycle hooks

## Date Fixed

2025-10-04

## Previous Fix

This fix builds on the previous worker queue configuration fix (see `CELERY_WORKER_FIX.md`). Both fixes were necessary:
1. First fix: Worker listening to correct queues (tasks can be processed)
2. This fix: Tasks are tracked and persisted (tasks can be queried)

