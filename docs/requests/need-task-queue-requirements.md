# Task Queue Requirements for Automated Gather Creation

**Service**: Celery-Redis Task Queue (tasks.ft.tc)
**Version**: 1.0.0
**Date**: January 2025
**Status**: Requirements Specification

---

## 📋 Overview

The Celery-Redis task queue needs to support a new long-running task type for automated gather creation. This document specifies **only** what the task queue infrastructure must provide - the actual task implementation logic is separate.

---

## 🆕 New Task Type Registration

### Task: `automated_gather_creation`

**Queue Assignment**: `cpu_intensive`

**Why**: Content generation and LLM operations are CPU-bound, not GPU-intensive

**Task Configuration**:
```python
# celery-redis/app/celery_config.py

task_routes = {
    # ... existing routes ...
    'automated_gather_creation': {'queue': 'cpu_intensive'},
}

task_time_limit = {
    'automated_gather_creation': 600,  # 10 minutes max
}

task_soft_time_limit = {
    'automated_gather_creation': 540,  # 9 minutes warning
}
```

---

## ⚙️ Task Queue Configuration

### 1. Timeout Settings

**Hard Timeout**: 600 seconds (10 minutes)
- Task will be killed if it exceeds this time
- Prevents zombie tasks

**Soft Timeout**: 540 seconds (9 minutes)
- Sends warning signal to task
- Allows graceful cleanup

**Rationale**:
- 50 iterations × ~10 seconds per iteration = ~500 seconds
- 100 second buffer for MongoDB/Brain operations
- Total: 10 minutes maximum

### 2. Retry Configuration

```python
task_autoretry_for = (
    ConnectionError,      # Network issues
    TimeoutError,         # External service timeouts
    TemporaryFailure,     # Recoverable errors
)

task_retry_kwargs = {
    'max_retries': 3,
    'countdown': 60,      # Wait 60s before first retry
}

task_retry_backoff = True
task_retry_backoff_max = 600    # Max 10 minutes between retries
task_retry_jitter = True         # Add randomness to prevent thundering herd
```

**Retry Schedule**:
- Attempt 1: Immediate
- Attempt 2: After 60 seconds
- Attempt 3: After ~120 seconds (with jitter)
- Attempt 4: After ~240 seconds (with jitter)

### 3. Priority Configuration

**Priority**: `1` (High)

**Rationale**: User-initiated tasks should have priority over background jobs

**Queue Priority Order**:
1. Priority 1: User-initiated (automated_gather_creation, evaluate_department)
2. Priority 5: Scheduled tasks
3. Priority 9: Background cleanup

---

## 🔄 Task State Management

### Required States

The task queue must support these states for tracking:

1. **`PENDING`**: Task submitted, waiting in queue
2. **`STARTED`**: Task execution began
3. **`PROGRESS`**: Task is running (with progress updates)
4. **`SUCCESS`**: Task completed successfully
5. **`FAILURE`**: Task failed (after retries)
6. **`RETRY`**: Task is being retried
7. **`REVOKED`**: Task was cancelled by user

### State Transitions

```
PENDING → STARTED → PROGRESS → SUCCESS
                  ↓
                RETRY → STARTED → ...
                  ↓
                FAILURE

PENDING/STARTED/PROGRESS → REVOKED (user cancellation)
```

---

## 📊 Task Result Storage

### Result Backend: Redis

**Configuration**:
```python
result_backend = 'redis://localhost:6379/1'
result_expires = 3600  # Results expire after 1 hour
```

### Result Format

**Success Result**:
```python
{
    'status': 'completed',
    'iterations': 45,
    'departments_processed': 7,
    'items_created': 89,
    'processing_time_ms': 425000,
    'summary': [
        {
            'department': 'story',
            'name': 'Story Department',
            'quality_score': 85,
            'iterations': 8,
            'items_created': 15
        },
        # ... more departments
    ]
}
```

**Failure Result**:
```python
{
    'error': 'task_execution_failed',
    'message': 'Brain API unavailable after 3 retries',
    'details': {
        'failed_at_department': 'character',
        'completed_departments': ['story'],
        'items_created_so_far': 15
    }
}
```

---

## 🔍 Task Monitoring Requirements

### 1. Celery Flower Integration

**Endpoint**: `https://tasks.ft.tc/flower`

**Must Provide**:
- Real-time task status
- Queue lengths
- Worker health
- Task execution history

### 2. Metrics Exposure

**Required Metrics** (Prometheus format):
```
# Task execution
celery_task_duration_seconds{task="automated_gather_creation"}
celery_task_total{task="automated_gather_creation",status="success"}
celery_task_total{task="automated_gather_creation",status="failure"}
celery_task_retry_total{task="automated_gather_creation"}

# Queue metrics
celery_queue_length{queue="cpu_intensive"}
celery_queue_wait_time_seconds{queue="cpu_intensive"}

# Worker metrics
celery_worker_active_tasks
celery_worker_available_slots
```

### 3. Logging Requirements

**Log Format**: JSON structured logs

**Required Fields**:
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "level": "INFO",
  "task_id": "abc-123-def",
  "task_name": "automated_gather_creation",
  "project_id": "507f1f77bcf86cd799439011",
  "message": "Task started",
  "duration_ms": null,
  "retry_count": 0
}
```

**Log Levels**:
- `DEBUG`: Detailed execution flow
- `INFO`: Task lifecycle events (started, progress, completed)
- `WARNING`: Retries, approaching timeout
- `ERROR`: Task failures, unhandled exceptions

---

## 🚫 Task Cancellation (Revocation)

### API Endpoint

**Method**: `DELETE /api/v1/tasks/{task_id}/cancel`

**Response**:
```json
{
  "task_id": "abc-123-def",
  "status": "revoked",
  "message": "Task cancellation requested"
}
```

### Cancellation Behavior

**Signal**: `SIGTERM` (soft kill)

**Task Response**:
- Must check for revocation signal periodically
- Save partial results before exiting
- Clean up resources (close connections)
- Return status: `revoked`

**Timeout**: 30 seconds for graceful shutdown
- If task doesn't exit in 30s, send `SIGKILL`

### Implementation Requirement

Task code must check for revocation:
```python
from celery.exceptions import Interrupt

@celery_app.task(bind=True)
def automated_gather_creation(self, task_data):
    for dept in departments:
        # Check if task was cancelled
        if self.request.id in cancelled_tasks:
            # Save partial results
            save_partial_results(...)
            raise Interrupt('Task cancelled by user')

        # Continue processing...
```

---

## 🔌 WebSocket Integration

### Redis Pub/Sub Channel

**Purpose**: Real-time progress updates to UI

**Channel Pattern**: `automated-gather:{projectId}`

**Configuration**:
```python
# No changes needed to Celery
# Task publishes to Redis directly:
import redis

redis_client = redis.Redis.from_url(os.getenv('REDIS_URL'))

def send_progress(event_data):
    channel = f"automated-gather:{event_data['project_id']}"
    redis_client.publish(channel, json.dumps(event_data))
```

**What Celery Must Provide**:
- Access to Redis connection (already exists)
- No blocking on publish operations
- Connection pooling for Redis

---

## 📦 Worker Configuration

### CPU-Intensive Queue Workers

**Worker Command**:
```bash
celery -A app.celery_app worker \
  --queue cpu_intensive \
  --concurrency 4 \
  --max-tasks-per-child 10 \
  --loglevel INFO \
  --logfile /var/log/celery/cpu_intensive.log
```

**Configuration**:
- **Concurrency**: 4 workers (adjust based on CPU cores)
- **Max Tasks per Child**: 10 (prevent memory leaks)
- **Prefetch Multiplier**: 1 (don't prefetch tasks)
- **Ack Late**: True (acknowledge after completion)

### Resource Limits

**Memory Limit**: 2GB per worker
```python
worker_max_memory_per_child = 2048000  # 2GB in KB
```

**If exceeded**: Worker restarts gracefully

---

## 🧪 Testing Requirements

### Load Testing

**Must handle**:
- 10 concurrent `automated_gather_creation` tasks
- Queue length up to 100 tasks
- No task starvation

### Failure Testing

**Scenarios**:
- Task timeout (exceeds 10 minutes)
- Worker crash mid-task
- Redis connection loss
- Task cancellation

**Expected Behavior**:
- Timeouts trigger retry
- Crashed workers don't lose tasks (ack_late=True)
- Redis reconnection automatic
- Cancellation saves partial results

---

## 🔐 Security Requirements

### Task Authorization

**API Key Required**: `X-API-Key` header

**Validation**:
- Check API key before accepting task
- Return 401 if invalid
- Rate limit by API key

### ProjectId Isolation

**CRITICAL**: Tasks must only access their project's data

**Enforcement**:
- All database queries filtered by `projectId`
- Brain API calls include `projectId`
- MongoDB uses isolated databases: `aladdin-gather-{projectId}`

---

## 📈 Scaling Requirements

### Horizontal Scaling

**Workers**:
- Must support adding workers dynamically
- No shared state between workers
- Use Redis for coordination

**Queue Scaling**:
- Monitor queue length
- Auto-scale workers when queue > 10 tasks
- Scale down when queue < 2 tasks

### Performance Targets

**Queue Latency**:
- Task pickup: <1 second
- Task start: <5 seconds
- Total queue wait: <30 seconds

**Task Throughput**:
- Process 20 tasks per hour minimum
- Complete 95% of tasks within 10 minutes

---

## 🚨 Error Handling & Alerts

### Alert Conditions

**Critical Alerts**:
- Task failure rate > 10%
- Queue length > 50 tasks
- Worker count = 0
- Redis connection lost

**Warning Alerts**:
- Task duration > 8 minutes (approaching timeout)
- Retry rate > 5%
- Queue wait time > 1 minute

### Alert Channels

- **Slack**: `#celery-alerts`
- **PagerDuty**: Critical failures only
- **Email**: Daily digest

---

## 🔄 Upgrade Requirements

### Breaking Changes

**None expected** - This is an additive change:
- New task type
- New queue routing
- Existing tasks unaffected

### Backwards Compatibility

**Required**:
- Existing tasks continue to work
- No changes to current worker configuration
- No changes to result backend

### Migration Plan

**Zero-downtime deployment**:
1. Deploy updated Celery config
2. Restart workers (rolling restart)
3. Verify new task type registered
4. Monitor for 24 hours

---

## ✅ Acceptance Criteria

### Functional Requirements
- [ ] Task type `automated_gather_creation` registered
- [ ] Routes to `cpu_intensive` queue
- [ ] Timeout: 600 seconds enforced
- [ ] Retry: 3 attempts with backoff
- [ ] Priority: 1 (high)
- [ ] Results stored in Redis (1 hour expiry)
- [ ] Cancellation supported (SIGTERM → graceful exit)
- [ ] WebSocket events publishable to Redis

### Monitoring Requirements
- [ ] Celery Flower accessible at `/flower`
- [ ] Prometheus metrics exposed
- [ ] JSON structured logs enabled
- [ ] Alerts configured (critical + warning)

### Performance Requirements
- [ ] Task pickup latency: <1 second
- [ ] Queue wait time: <30 seconds
- [ ] 10 concurrent tasks supported
- [ ] 20 tasks/hour throughput minimum

### Security Requirements
- [ ] API key authentication enforced
- [ ] Rate limiting by API key
- [ ] ProjectId isolation verified
- [ ] No cross-project data leakage

---

## 📋 Configuration Checklist

### Environment Variables

```bash
# Redis (Result Backend)
CELERY_RESULT_BACKEND=redis://localhost:6379/1
CELERY_RESULT_EXPIRES=3600

# Broker (Task Queue)
CELERY_BROKER_URL=redis://localhost:6379/0

# Worker Settings
CELERYD_CONCURRENCY=4
CELERYD_MAX_TASKS_PER_CHILD=10
CELERYD_PREFETCH_MULTIPLIER=1
CELERYD_TASK_ACKS_LATE=True

# Memory Limits
CELERYD_MAX_MEMORY_PER_CHILD=2048000  # 2GB

# Monitoring
CELERY_ENABLE_FLOWER=true
CELERY_FLOWER_PORT=5555
```

### Worker Service Configuration

**Systemd Service** (`/etc/systemd/system/celery-cpu-intensive.service`):
```ini
[Unit]
Description=Celery CPU Intensive Worker
After=network.target

[Service]
Type=forking
User=celery
Group=celery
EnvironmentFile=/etc/celery/celery.env
WorkingDirectory=/opt/celery-redis
ExecStart=/opt/celery-redis/venv/bin/celery -A app.celery_app worker \
  --queue cpu_intensive \
  --concurrency 4 \
  --max-tasks-per-child 10 \
  --loglevel INFO \
  --logfile /var/log/celery/cpu_intensive.log \
  --pidfile /var/run/celery/cpu_intensive.pid
ExecStop=/bin/kill -TERM $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## 📞 Support & Maintenance

**Service Owner**: Infrastructure Team
**On-Call**: `#celery-oncall`
**Documentation**: `/celery-redis/docs/`
**Runbook**: `/celery-redis/docs/runbooks/automated-gather.md`

---

**Status**: Ready for Implementation
**Estimated Effort**: 1 day (configuration changes only)
**Risk Level**: Low (additive change, no breaking modifications)
