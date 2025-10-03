module.exports = {
  apps: [
    {
      name: 'celery-redis-api',
      cwd: '/var/www/celery-redis',
      script: 'venv/bin/python',
      args: '-m app.main',
      interpreter: 'none',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production'
      },
      error_file: '/var/log/celery-redis-api-error.log',
      out_file: '/var/log/celery-redis-api-out.log',
      log_file: '/var/log/celery-redis-api-combined.log',
      time: true
    },
    {
      name: 'celery-worker',
      cwd: '/var/www/celery-redis',
      script: 'venv/bin/celery',
      args: '-A app.celery_app worker --loglevel=info --concurrency=4',
      interpreter: 'none',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '2G',
      env: {
        NODE_ENV: 'production'
      },
      error_file: '/var/log/celery-worker-error.log',
      out_file: '/var/log/celery-worker-out.log',
      log_file: '/var/log/celery-worker-combined.log',
      time: true
    }
  ]
};
