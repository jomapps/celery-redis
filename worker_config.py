"""
Celery worker configuration for automated_gather_creation task
Optimized for CPU-intensive workloads with proper resource limits
"""

# Worker configuration for cpu_intensive queue
WORKER_CONFIG = {
    # Queue configuration
    'queues': ['cpu_intensive'],
    
    # Concurrency settings
    'concurrency': 4,  # Number of worker processes
    'prefetch_multiplier': 1,  # Tasks to prefetch per worker
    
    # Resource limits
    'max_tasks_per_child': 10,  # Restart worker after N tasks (prevent memory leaks)
    'max_memory_per_child': 2048000,  # 2GB memory limit per worker (in KB)
    
    # Timeout settings
    'task_time_limit': 600,  # 10 minutes hard timeout
    'task_soft_time_limit': 540,  # 9 minutes soft timeout
    
    # Logging
    'loglevel': 'INFO',
    'logfile': '/var/log/celery/worker-cpu-intensive.log',
    
    # Performance optimization
    'worker_disable_rate_limits': False,
    'worker_send_task_events': True,
    'task_send_sent_event': True,
    
    # Pool settings
    'pool': 'prefork',  # Use prefork pool for CPU-intensive tasks
    'pool_restarts': True,  # Enable pool restarts
}

# Command to start worker
# celery -A app.celery_app worker \
#     --queues=cpu_intensive \
#     --concurrency=4 \
#     --prefetch-multiplier=1 \
#     --max-tasks-per-child=10 \
#     --max-memory-per-child=2048000 \
#     --time-limit=600 \
#     --soft-time-limit=540 \
#     --loglevel=INFO \
#     --logfile=/var/log/celery/worker-cpu-intensive.log \
#     --pool=prefork

