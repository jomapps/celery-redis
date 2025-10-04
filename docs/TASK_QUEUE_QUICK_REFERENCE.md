# Task Queue Quick Reference

**Quick reference for task queue operations and troubleshooting**

---

## 🚀 Quick Start

### Check Service Status
```bash
pm2 list
pm2 logs celery-worker --lines 50
pm2 logs celery-redis-api --lines 50
```

### Restart Services
```bash
pm2 restart celery-worker
pm2 restart celery-redis-api
pm2 restart all
```

### Health Check
```bash
curl http://localhost:8001/api/v1/health
```

---

## 📊 Monitoring Commands

### Get Task Metrics
```bash
curl -H "X-API-Key: ae6e18cb408bc7128f23585casdlaelwlekoqdsldsa" \
  http://localhost:8001/api/v1/tasks/metrics | python3 -m json.tool
```

### Get Health Status
```bash
curl -H "X-API-Key: ae6e18cb408bc7128f23585casdlaelwlekoqdsldsa" \
  http://localhost:8001/api/v1/tasks/health | python3 -m json.tool
```

### Check Worker Status
```bash
celery -A app.celery_app inspect active
celery -A app.celery_app inspect stats
celery -A app.celery_app inspect registered
```

### Check Queue Length
```bash
redis-cli llen celery
redis-cli llen cpu_intensive
```

---

## 🔧 Task Operations

### Submit Task
```bash
curl -X POST http://localhost:8001/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ae6e18cb408bc7128f23585casdlaelwlekoqdsldsa" \
  -d '{
    "project_id": "507f1f77bcf86cd799439011",
    "task_type": "automated_gather_creation",
    "task_data": {}
  }'
```

### Cancel Task
```bash
curl -X DELETE http://localhost:8001/api/v1/tasks/{task_id} \
  -H "X-API-Key: ae6e18cb408bc7128f23585casdlaelwlekoqdsldsa"
```

### Get Task Status
```bash
curl http://localhost:8001/api/v1/tasks/{task_id}/status \
  -H "X-API-Key: ae6e18cb408bc7128f23585casdlaelwlekoqdsldsa"
```

---

## 🐛 Troubleshooting

### Worker Not Picking Up Tasks
```bash
# Check worker is running
pm2 list | grep celery-worker

# Check worker logs
pm2 logs celery-worker --lines 100

# Check Redis connection
redis-cli ping

# Restart worker
pm2 restart celery-worker
```

### High Memory Usage
```bash
# Check worker memory
pm2 list

# Check detailed stats
pm2 show celery-worker

# Restart worker (will clear memory)
pm2 restart celery-worker
```

### Tasks Timing Out
```bash
# Check current timeout settings
grep -A 5 "task_time_limits" app/celery_app.py

# Check long-running tasks
curl -H "X-API-Key: ae6e18cb408bc7128f23585casdlaelwlekoqdsldsa" \
  http://localhost:8001/api/v1/tasks/health | grep -A 10 "alerts"
```

### High Failure Rate
```bash
# Check metrics
curl -H "X-API-Key: ae6e18cb408bc7128f23585casdlaelwlekoqdsldsa" \
  http://localhost:8001/api/v1/tasks/metrics

# Check worker logs for errors
pm2 logs celery-worker --err --lines 100

# Check Redis connection
redis-cli ping
```

### Queue Backlog
```bash
# Check queue length
redis-cli llen celery
redis-cli llen cpu_intensive

# Purge queue (CAUTION!)
celery -A app.celery_app purge

# Scale workers (if needed)
# Edit PM2 config to increase instances
```

---

## 📝 Configuration Files

### Celery Configuration
- **File**: `app/celery_app.py`
- **Key Settings**: Task routes, timeouts, retries, worker limits

### Worker Configuration
- **File**: `worker_config.py`
- **Key Settings**: Concurrency, memory limits, queue names

### Monitoring Configuration
- **File**: `app/config/monitoring.py`
- **Key Settings**: Metrics collection, health checks, alerts

### API Configuration
- **File**: `app/api/tasks.py`
- **Key Settings**: Endpoints, authentication, validation

---

## 🔑 Configuration Values

| Setting | Value | Location |
|---------|-------|----------|
| **Queue Name** | `cpu_intensive` | `app/celery_app.py` |
| **Hard Timeout** | 600 seconds | `app/celery_app.py` |
| **Soft Timeout** | 540 seconds | `app/celery_app.py` |
| **Max Retries** | 3 | `app/celery_app.py` |
| **Worker Concurrency** | 4 | `worker_config.py` |
| **Memory Limit** | 2GB | `app/celery_app.py` |
| **Tasks Per Child** | 10 | `app/celery_app.py` |
| **Result Expiry** | 1 hour | `app/celery_app.py` |

---

## 🧪 Testing

### Run All Tests
```bash
python3 -m pytest tests/test_task_queue_config.py -v
```

### Run Specific Test
```bash
python3 -m pytest tests/test_task_queue_config.py::TestTaskCancellation::test_cancel_queued_task -v
```

### Run with Coverage
```bash
python3 -m pytest tests/test_task_queue_config.py --cov=app --cov-report=html
```

---

## 📊 Metrics Reference

### Success Metrics
- **Success Rate**: >90% (healthy)
- **Failure Rate**: <10% (healthy)
- **Average Duration**: <5 minutes (optimal)
- **Queue Length**: <10 tasks (healthy)

### Alert Thresholds
- **Critical**: Failure rate >20%
- **Warning**: Failure rate >10%
- **Warning**: Task duration >8 minutes
- **Warning**: Memory usage >1.9GB

---

## 🔗 Useful Links

### Documentation
- [Full Implementation Guide](./TASK_QUEUE_IMPLEMENTATION.md)
- [Configuration Guide](./task-queue-configuration.md)
- [Celery Docs](https://docs.celeryproject.org/)

### Monitoring
- Metrics: `GET /api/v1/tasks/metrics`
- Health: `GET /api/v1/tasks/health`
- PM2 Dashboard: `pm2 monit`

### Logs
- Worker Output: `/var/log/celery-worker-out-3.log`
- Worker Errors: `/var/log/celery-worker-error-3.log`
- PM2 Logs: `pm2 logs`

---

## 🆘 Emergency Procedures

### Service Down
```bash
# Check status
pm2 list

# Restart all services
pm2 restart all

# If still down, check logs
pm2 logs --err --lines 100

# Check Redis
redis-cli ping

# Last resort: full restart
pm2 delete all
pm2 start ecosystem.config.js
```

### Memory Leak
```bash
# Immediate: Restart worker
pm2 restart celery-worker

# Long-term: Reduce tasks per child
# Edit app/celery_app.py
# Change: worker_max_tasks_per_child = 5
pm2 restart celery-worker
```

### Queue Stuck
```bash
# Check queue
redis-cli llen celery

# Inspect active tasks
celery -A app.celery_app inspect active

# Revoke all active tasks (CAUTION!)
celery -A app.celery_app inspect active | grep task_id | xargs -I {} celery -A app.celery_app control revoke {}

# Purge queue (CAUTION!)
celery -A app.celery_app purge
```

---

## 📞 Support

### Check Logs First
```bash
pm2 logs celery-worker --lines 100
pm2 logs celery-redis-api --lines 100
```

### Gather Diagnostics
```bash
# System info
pm2 list
pm2 show celery-worker
redis-cli info

# Task metrics
curl -H "X-API-Key: ae6e18cb408bc7128f23585casdlaelwlekoqdsldsa" \
  http://localhost:8001/api/v1/tasks/health

# Worker status
celery -A app.celery_app inspect stats
```

### Common Issues
1. **Worker not starting**: Check Redis connection
2. **Tasks not executing**: Check queue routing
3. **High memory**: Reduce tasks_per_child
4. **Timeouts**: Increase timeout or optimize task
5. **High failure rate**: Check logs for errors

---

**Last Updated**: 2025-10-04  
**Version**: 1.0.0

