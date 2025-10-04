# Celery-Redis Service - Quick Reference Guide

## Service Status

Check if services are running:
```bash
pm2 list
```

Expected output:
- `celery-redis-api` - FastAPI server (port 8001)
- `celery-worker` - Celery worker processing tasks

## Common Commands

### Check Worker Status
```bash
# View worker logs
pm2 logs celery-worker

# View last 50 lines
pm2 logs celery-worker --lines 50 --nostream

# Check registered tasks
venv/bin/celery -A app.celery_app inspect registered

# Check active queues
venv/bin/celery -A app.celery_app inspect active_queues

# Check active tasks
venv/bin/celery -A app.celery_app inspect active
```

### Restart Services
```bash
# Restart API only
pm2 restart celery-redis-api

# Restart worker only
pm2 restart celery-worker

# Restart all
pm2 restart all
```

### Check Queue Status
```bash
# Check queue lengths
venv/bin/python -c "
import redis
r = redis.Redis.from_url('redis://localhost:6379/0')
print('Queue lengths:')
print('celery:', r.llen('celery'))
print('cpu_intensive:', r.llen('cpu_intensive'))
print('gpu_heavy:', r.llen('gpu_heavy'))
print('gpu_medium:', r.llen('gpu_medium'))
"
```

### Health Check
```bash
# Check API health
curl https://tasks.ft.tc/api/v1/health

# Check task service health (requires API key)
curl -H "X-API-Key: YOUR_API_KEY" https://tasks.ft.tc/api/v1/tasks/health
```

## Task Queues

The service uses 4 different queues:

| Queue | Purpose | Example Tasks |
|-------|---------|---------------|
| `celery` | Default queue | General tasks |
| `cpu_intensive` | CPU-heavy tasks | `evaluate_department`, `automated_gather_creation` |
| `gpu_heavy` | GPU-intensive video | Video generation/editing |
| `gpu_medium` | GPU-moderate image | Image generation/editing |

## Troubleshooting

### Tasks Not Being Processed

1. **Check if worker is running:**
   ```bash
   pm2 list | grep celery-worker
   ```

2. **Check worker logs for errors:**
   ```bash
   pm2 logs celery-worker --lines 100
   ```

3. **Verify tasks are registered:**
   ```bash
   venv/bin/celery -A app.celery_app inspect registered
   ```
   Should show `app.tasks.evaluation_tasks.evaluate_department`

4. **Verify worker is listening to correct queues:**
   ```bash
   pm2 logs celery-worker --lines 50 --nostream | grep -A 10 "queues"
   ```
   Should show: `celery`, `cpu_intensive`, `gpu_heavy`, `gpu_medium`

5. **Check queue lengths:**
   ```bash
   venv/bin/python -c "import redis; r = redis.Redis.from_url('redis://localhost:6379/0'); print('cpu_intensive queue:', r.llen('cpu_intensive'))"
   ```

### Worker Not Starting

1. **Check Redis connection:**
   ```bash
   venv/bin/python -c "import redis; r = redis.Redis.from_url('redis://localhost:6379/0'); r.ping(); print('Redis OK')"
   ```

2. **Check for import errors:**
   ```bash
   venv/bin/python -c "from app.celery_app import celery_app; print('Celery app loaded')"
   ```

3. **Check PM2 error logs:**
   ```bash
   cat /var/log/celery-worker-error.log | tail -50
   ```

### Tasks Failing

1. **Check task execution logs:**
   ```bash
   pm2 logs celery-worker | grep -i error
   ```

2. **Check specific task result:**
   ```bash
   venv/bin/celery -A app.celery_app result TASK_ID
   ```

3. **Check failed tasks:**
   ```bash
   venv/bin/celery -A app.celery_app inspect failed
   ```

## Configuration Files

- `ecosystem.config.js` - PM2 process configuration
- `app/config/settings.py` - Application settings
- `app/celery_app.py` - Celery configuration
- `.env` - Environment variables (not in git)

## Environment Variables

Key environment variables (set in `.env` or PM2 config):

```bash
# Redis
REDIS_URL=redis://localhost:6379/0

# API
API_HOST=0.0.0.0
API_PORT=8001
API_KEY=your-api-key-here

# Worker
WORKER_CONCURRENCY=4
WORKER_QUEUES=celery,cpu_intensive,gpu_heavy,gpu_medium

# Brain Service
BRAIN_SERVICE_BASE_URL=https://brain.ft.tc

# PayloadCMS
PAYLOAD_API_URL=http://localhost:3010/api
PAYLOAD_API_KEY=your-payload-key
```

## Monitoring

### Real-time Monitoring
```bash
# Watch worker logs in real-time
pm2 logs celery-worker

# Watch API logs in real-time
pm2 logs celery-redis-api

# Monitor all services
pm2 monit
```

### Task Statistics
```bash
# Get worker stats
venv/bin/celery -A app.celery_app inspect stats

# Get active tasks
venv/bin/celery -A app.celery_app inspect active

# Get scheduled tasks
venv/bin/celery -A app.celery_app inspect scheduled
```

## Deployment

### Update Code
```bash
cd /var/www/celery-redis
git pull
pm2 restart celery-redis-api
pm2 restart celery-worker
```

### Update Dependencies
```bash
cd /var/www/celery-redis
source venv/bin/activate
pip install -r requirements.txt
pm2 restart all
```

### Update PM2 Configuration
```bash
# After editing ecosystem.config.js
pm2 delete celery-worker
pm2 start ecosystem.config.js --only celery-worker
pm2 save
```

## Important Notes

1. **Always specify queues** when starting workers
2. **Use unique hostnames** to avoid conflicts with other workers
3. **Save PM2 config** after changes: `pm2 save`
4. **Check logs** after any changes to verify everything is working
5. **Monitor queue lengths** to ensure tasks are being processed

## Support

For issues or questions:
1. Check this guide first
2. Review `CELERY_WORKER_FIX.md` for recent fixes
3. Check logs: `pm2 logs celery-worker`
4. Contact the development team

## Last Updated

2025-10-04

