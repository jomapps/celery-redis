@echo off
echo Starting AI Movie Task Service in development mode...

REM Check if Redis is running
echo Checking Redis connection...
docker ps | findstr redis-dev > nul
if errorlevel 1 (
    echo Starting Redis container...
    docker run -d --name redis-dev -p 6379:6379 redis:latest
    timeout /t 3 > nul
)

echo Redis is running!

REM Set environment variables
set API_KEY=test-api-key
set REDIS_URL=redis://localhost:6379/0
set ENVIRONMENT=development
set DEBUG=true

echo Starting API server...
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

pause