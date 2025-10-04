# Task Queue Configuration for automated_gather_creation

## Overview

This document describes the Celery task queue infrastructure configuration for the `automated_gather_creation` task type. The configuration ensures reliable task execution with proper timeouts, retries, resource limits, and monitoring.

## Configuration Summary

| Setting | Value | Purpose |
|---------|-------|---------|
| **Queue** | `cpu_intensive` | Dedicated queue for CPU-heavy tasks |
| **Hard Timeout** | 600 seconds (10 min) | Maximum execution time |
| **Soft Timeout** | 540 seconds (9 min) | Warning before hard timeout |
| **Max Retries** | 3 | Number of retry attempts |
| **Retry Backoff** | Exponential | 60s, 120s, 240s intervals |
| **Worker Concurrency** | 4 | Number of worker processes |
| **Memory Limit** | 2GB per worker | Prevent memory leaks |
| **Tasks Per Child** | 10 | Restart worker after N tasks |

## Celery Configuration

### Task Routing

Tasks are routed to the `cpu_intensive` queue:

```python
# app/celery_app.py
celery_app.conf.task_routes = {
    'automated_gather_creation': {'queue': 'cpu_intensive'},
}
```

### Timeout Configuration

```python
# Hard timeout (task will be killed)
celery_app.conf.task_time_limits = {
    'automated_gather_creation': 600,  # 10 minutes
}

# Soft timeout (warning signal sent)
celery_app.conf.task_soft_time_limits = {
    'automated_gather_creation': 540,  # 9 minutes
}
```

**Behavior:**
- At 9 minutes: `SoftTimeLimitExceeded` exception raised (task can handle gracefully)
- At 10 minutes: Task forcefully terminated with `SIGKILL`

### Retry Configuration

```python
# Automatic retry on failures
celery_app.conf.task_autoretry_for = (
    ConnectionError,
    TimeoutError,
    Exception,
)

celery_app.conf.task_retry_kwargs = {
    'max_retries': 3,
    'countdown': 60,  # Wait 60 seconds before first retry
}

celery_app.conf.task_retry_backoff = True
celery_app.conf.task_retry_backoff_max = 600  # Max 10 minutes between retries
celery_app.conf.task_retry_jitter = True  # Add randomness
```

**Retry Schedule:**
1. **First retry**: After 60 seconds
2. **Second retry**: After ~120 seconds (exponential backoff)
3. **Third retry**: After ~240 seconds (exponential backoff)
4. **Final failure**: After 3 failed attempts

### Worker Configuration

```python
# Worker resource limits
celery_app.conf.worker_max_tasks_per_child = 10  # Restart after 10 tasks
celery_app.conf.worker_max_memory_per_child = 2048000  # 2GB limit (in KB)
celery_app.conf.worker_concurrency = 2  # Adjust based on CPU cores
celery_app.conf.worker_prefetch_multiplier = 1  # Prevent task hoarding
```

## Worker Startup

### Command Line

```bash
celery -A app.celery_app worker \
    --queues=cpu_intensive \
    --concurrency=4 \
    --prefetch-multiplier=1 \
    --max-tasks-per-child=10 \
    --max-memory-per-child=2048000 \
    --time-limit=600 \
    --soft-time-limit=540 \
    --loglevel=INFO \
    --logfile=/var/log/celery/worker-cpu-intensive.log \
    --pool=prefork
```

### Using Configuration File

```bash
# Load from worker_config.py
celery -A app.celery_app worker --config=worker_config
```

### Systemd Service

Create `/etc/systemd/system/celery-cpu-intensive.service`:

```ini
[Unit]
Description=Celery Worker (CPU Intensive Queue)
After=network.target redis.target

[Service]
Type=forking
User=celery
Group=celery
WorkingDirectory=/var/www/celery-redis
Environment="PATH=/var/www/celery-redis/venv/bin"
ExecStart=/var/www/celery-redis/venv/bin/celery -A app.celery_app worker \
    --queues=cpu_intensive \
    --concurrency=4 \
    --prefetch-multiplier=1 \
    --max-tasks-per-child=10 \
    --max-memory-per-child=2048000 \
    --time-limit=600 \
    --soft-time-limit=540 \
    --loglevel=INFO \
    --logfile=/var/log/celery/worker-cpu-intensive.log \
    --pidfile=/var/run/celery/worker-cpu-intensive.pid \
    --detach

ExecStop=/bin/kill -TERM $MAINPID
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable celery-cpu-intensive
sudo systemctl start celery-cpu-intensive
sudo systemctl status celery-cpu-intensive
```

## Task Cancellation API

### Cancel a Task

**DELETE** `/api/v1/tasks/{task_id}`

```bash
curl -X DELETE https://tasks.ft.tc/api/v1/tasks/{task_id} \
  -H "X-API-Key: your-api-key"
```

**Response (Success):**
```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "cancelled",
  "message": "Task was running and has been terminated",
  "previous_state": "processing",
  "cancelled_at": "2025-01-15T10:35:30Z"
}
```

**Response (Already Completed):**
```json
{
  "detail": "Task has already completed successfully and cannot be cancelled"
}
```

### Cancellation Behavior

| Task State | Action | Result |
|------------|--------|--------|
| **PENDING** (queued) | Revoke without termination | Task removed from queue |
| **STARTED** (running) | Revoke with SIGTERM | Task process terminated |
| **SUCCESS** (completed) | No action | HTTP 400 error |
| **FAILURE** (failed) | No action | HTTP 400 error |
| **REVOKED** (cancelled) | No action | Returns already cancelled |

## Monitoring

### Metrics Endpoint

**GET** `/api/v1/tasks/metrics`

```bash
curl https://tasks.ft.tc/api/v1/tasks/metrics \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "metrics": {
    "total_tasks": 150,
    "completed_tasks": 135,
    "failed_tasks": 10,
    "retried_tasks": 5,
    "cancelled_tasks": 0,
    "success_rate": 90.0,
    "failure_rate": 6.67,
    "average_durations": {
      "automated_gather_creation": 245.5
    },
    "currently_running": 3
  },
  "timestamp": "2025-01-15T10:35:30Z"
}
```

### Health Check Endpoint

**GET** `/api/v1/tasks/health`

```bash
curl https://tasks.ft.tc/api/v1/tasks/health \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "status": "healthy",
  "metrics": {
    "total_tasks": 150,
    "success_rate": 90.0,
    "failure_rate": 6.67
  },
  "alerts": [],
  "timestamp": "2025-01-15T10:35:30Z"
}
```

**With Alerts:**
```json
{
  "status": "warning",
  "metrics": {...},
  "alerts": [
    {
      "severity": "warning",
      "message": "Task abc123 running for 520 seconds",
      "metric": "task_duration",
      "value": 520,
      "task_id": "abc123"
    }
  ],
  "timestamp": "2025-01-15T10:35:30Z"
}
```

### Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| **Failure Rate** | > 10% | > 20% |
| **Task Duration** | > 8 minutes | > 9.5 minutes |
| **Memory Usage** | > 1.5GB | > 1.9GB |

## Logging

### Log Locations

```bash
# Worker logs
/var/log/celery/worker-cpu-intensive.log

# API logs
/var/log/celery-redis/api.log

# System logs
journalctl -u celery-cpu-intensive -f
```

### Log Patterns

**Task Started:**
```
INFO: Task started task_id=abc123 task_name=automated_gather_creation
```

**Task Completed:**
```
INFO: Task completed task_id=abc123 duration=245.5 state=SUCCESS
```

**Task Failed:**
```
ERROR: Task failed task_id=abc123 exception=TimeoutError
```

**Task Retry:**
```
WARNING: Task retry scheduled task_id=abc123 reason=Connection timeout attempt=1
```

**Task Cancelled:**
```
WARNING: Task revoked task_id=abc123 terminated=True
```

## Performance Tuning

### Concurrency

Adjust based on CPU cores:
```bash
# For 8-core CPU
--concurrency=6  # Leave 2 cores for system

# For 16-core CPU
--concurrency=12  # Leave 4 cores for system
```

### Memory Limits

Adjust based on available RAM:
```bash
# For 16GB RAM server
--max-memory-per-child=3072000  # 3GB per worker

# For 32GB RAM server
--max-memory-per-child=4096000  # 4GB per worker
```

### Prefetch Multiplier

```bash
# Low latency (recommended for long tasks)
--prefetch-multiplier=1

# Higher throughput (for short tasks)
--prefetch-multiplier=4
```

## Troubleshooting

### Task Timeout Issues

**Problem**: Tasks timing out before completion

**Solutions:**
1. Increase timeout limits in `celery_app.py`
2. Optimize task logic to run faster
3. Split task into smaller subtasks

### Memory Leaks

**Problem**: Worker memory usage grows over time

**Solutions:**
1. Reduce `max_tasks_per_child` (restart workers more frequently)
2. Lower `max_memory_per_child` limit
3. Profile task code for memory leaks

### High Failure Rate

**Problem**: Many tasks failing

**Solutions:**
1. Check logs for error patterns
2. Verify external service availability
3. Increase retry attempts
4. Add better error handling in task code

### Queue Backlog

**Problem**: Tasks piling up in queue

**Solutions:**
1. Increase worker concurrency
2. Add more worker instances
3. Optimize task execution time
4. Implement task prioritization

## Testing

Run the test suite:

```bash
python3 -m pytest tests/test_task_queue_config.py -v
```

Expected: 18 tests passing

## Additional Resources

- [Celery Documentation](https://docs.celeryproject.org/)
- [Redis Configuration](https://redis.io/docs/manual/config/)
- [Monitoring Guide](./monitoring-guide.md)
- [Task Implementation](./automated-gather-creation.md)

