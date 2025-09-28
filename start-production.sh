#!/bin/bash
# Production startup script for Celery-Redis Service

set -e

echo "🚀 Starting AI Movie Platform - Celery-Redis Service"

# Check if Redis is available
echo "📡 Checking Redis connection..."
python -c "
import redis
import sys
try:
    r = redis.Redis.from_url('${REDIS_URL:-redis://localhost:6379/0}')
    r.ping()
    print('✅ Redis connection successful')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
    sys.exit(1)
"

# Check if all dependencies are available
echo "📦 Checking dependencies..."
python -c "
import celery, fastapi, uvicorn, redis
print('✅ All core dependencies available')
"

# Start services based on the SERVICE_TYPE environment variable
SERVICE_TYPE=${SERVICE_TYPE:-api}

if [ "$SERVICE_TYPE" = "api" ]; then
    echo "🌐 Starting FastAPI server..."
    exec uvicorn app.main:app \
        --host ${API_HOST:-0.0.0.0} \
        --port ${API_PORT:-8001} \
        --workers ${API_WORKERS:-4} \
        --access-log \
        --log-level ${LOG_LEVEL:-info}

elif [ "$SERVICE_TYPE" = "worker" ]; then
    echo "⚙️ Starting Celery worker..."
    exec celery -A app.celery_app worker \
        --loglevel=${LOG_LEVEL:-info} \
        --concurrency=${WORKER_CONCURRENCY:-4} \
        --queues=${WORKER_QUEUES:-celery,gpu_heavy,gpu_medium,cpu_intensive} \
        --hostname=worker@%h \
        --time-limit=${TASK_TIMEOUT:-3600} \
        --soft-time-limit=3300

elif [ "$SERVICE_TYPE" = "monitor" ]; then
    echo "📊 Starting Celery monitoring..."
    exec celery -A app.celery_app flower \
        --port=${FLOWER_PORT:-5555} \
        --basic_auth=${FLOWER_AUTH:-admin:admin}

else
    echo "❌ Unknown SERVICE_TYPE: $SERVICE_TYPE"
    echo "Valid options: api, worker, monitor"
    exit 1
fi
