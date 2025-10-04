# Celery Worker Fix - Task Processing Issue

## Problem Summary

The task service was accepting task submissions but not processing them. The health endpoint showed:
- `total_tasks: 0` - No tasks processed
- `currently_running: 0` - No tasks running

## Root Cause Analysis

### Issue 1: Worker Not Listening to Correct Queues

The `evaluate_department` task is configured to use the `cpu_intensive` queue:

```python
# app/tasks/evaluation_tasks.py, line 314
@celery_app.task(bind=True, base=EvaluateDepartmentTask, queue='cpu_intensive')
def evaluate_department(...):
```

However, the Celery worker was only listening to the default `celery` queue because the PM2 configuration didn't specify which queues to consume from:

```javascript
// ecosystem.config.js - BEFORE FIX
args: '-A app.celery_app worker --loglevel=info --concurrency=4'
```

**Result**: Tasks were being queued to `cpu_intensive` but no worker was consuming from that queue.

### Issue 2: Duplicate Worker Nodenames

Two different Celery workers were running with the same nodename `celery@vmd177401`:
1. `/var/www/celery-redis` worker (this service)
2. `/var/www/last-frame` worker (different service)

Both workers were using the same Redis instance, causing conflicts and confusion.

## Solution

### Fix 1: Configure Worker to Listen to All Required Queues

Updated `ecosystem.config.js` to explicitly specify all queues:

```javascript
// ecosystem.config.js - AFTER FIX
args: '-A app.celery_app worker --loglevel=info --concurrency=4 --queues=celery,cpu_intensive,gpu_heavy,gpu_medium --hostname=celery-redis-worker@%h'
```

Changes:
- Added `--queues=celery,cpu_intensive,gpu_heavy,gpu_medium` to consume from all task queues
- Added `--hostname=celery-redis-worker@%h` to give this worker a unique name

### Fix 2: Restart Worker with New Configuration

```bash
# Delete old worker process
pm2 delete celery-worker

# Start worker with new configuration
pm2 start ecosystem.config.js --only celery-worker

# Save PM2 configuration for persistence
pm2 save
```

## Verification

After the fix, the worker logs show:

```
[queues]
  .> celery           exchange=celery(direct) key=celery
  .> cpu_intensive    exchange=cpu_intensive(direct) key=cpu_intensive
  .> gpu_heavy        exchange=gpu_heavy(direct) key=gpu_heavy
  .> gpu_medium       exchange=gpu_medium(direct) key=gpu_medium

[tasks]
  . app.tasks.audio_tasks.process_audio_editing
  . app.tasks.audio_tasks.process_audio_generation
  . app.tasks.audio_tasks.process_audio_synthesis
  . app.tasks.evaluation_tasks.evaluate_department  ← REGISTERED
  . app.tasks.image_tasks.process_image_batch
  . app.tasks.image_tasks.process_image_editing
  . app.tasks.image_tasks.process_image_generation
  . app.tasks.video_tasks.process_video_editing
  . app.tasks.video_tasks.process_video_generation
  . automated_gather_creation
```

And tasks are being processed:

```
[2025-10-04 10:13:20,444: INFO/MainProcess] Task app.tasks.evaluation_tasks.evaluate_department[b9e9676e-bdda-498d-ac8d-c1312bd1f033] received
[2025-10-04 10:13:20,455: WARNING/ForkPoolWorker-3] Starting department evaluation department=story
[2025-10-04 10:13:26,826: WARNING/ForkPoolWorker-1] Department evaluation completed rating=89 result=pass
```

## Task Queue Configuration Reference

The service uses multiple queues for different types of tasks:

| Queue | Purpose | Tasks |
|-------|---------|-------|
| `celery` | Default queue | General tasks |
| `cpu_intensive` | CPU-heavy tasks | `evaluate_department`, `automated_gather_creation` |
| `gpu_heavy` | GPU-intensive video tasks | Video generation/editing |
| `gpu_medium` | GPU-moderate image tasks | Image generation/editing |

## Important Notes

1. **Always specify queues** when starting Celery workers to ensure tasks are consumed
2. **Use unique hostnames** for workers to avoid conflicts when multiple services share Redis
3. **Check worker logs** to verify tasks are registered and queues are configured correctly
4. **PM2 configuration changes** require deleting and recreating the process, not just restarting

## Testing

To test that tasks are being processed:

```bash
# Check worker status
pm2 logs celery-worker --lines 50

# Verify registered tasks
venv/bin/celery -A app.celery_app inspect registered

# Check active queues
venv/bin/celery -A app.celery_app inspect active_queues

# Submit a test task
curl -X POST https://tasks.ft.tc/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
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
```

## Related Files

- `ecosystem.config.js` - PM2 process configuration
- `app/tasks/evaluation_tasks.py` - Task definition with queue configuration
- `app/celery_app.py` - Celery app configuration and task routing
- `app/config/settings.py` - Celery and Redis configuration

## Date Fixed

2025-10-04

