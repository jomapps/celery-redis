#\!/bin/bash

# Setup script for celery-redis service
# This script initializes git, starts PM2 services, and verifies configuration

set -e  # Exit on error

echo "========================================="
echo "Celery-Redis Service Setup"
echo "========================================="
echo ""

# Check if we're in the right directory
if [ \! -f "app/main.py" ]; then
    echo "Error: app/main.py not found. Are you in the celery-redis directory?"
    exit 1
fi

# Step 1: Git initialization
echo "Step 1: Checking Git status..."
if [ \! -d ".git" ]; then
    echo "Error: .git directory not found. Repository not initialized."
    exit 1
fi

# Check if there are commits
COMMIT_COUNT=$(git rev-list --count HEAD 2>/dev/null || echo "0")
if [ "$COMMIT_COUNT" = "0" ]; then
    echo "⚠️  No commits found. Repository needs initial commit."
    echo ""
    echo "To initialize the repository, run:"
    echo "  git add ."
    echo "  git commit -m 'Initial commit: AI Movie Task Service'"
    echo "  git push -u origin master"
    echo ""
    read -p "Do you want to commit now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add .
        git commit -m "Initial commit: AI Movie Task Service with PM2 configuration"
        echo "✅ Initial commit created"
        echo ""
        read -p "Push to remote? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git push -u origin master
            echo "✅ Pushed to remote"
        fi
    fi
else
    echo "✅ Git repository has $COMMIT_COUNT commit(s)"
fi

echo ""

# Step 2: Check virtual environment
echo "Step 2: Checking virtual environment..."
if [ \! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

if [ \! -f "venv/bin/python" ]; then
    echo "Error: venv/bin/python not found"
    exit 1
fi

echo "✅ Virtual environment exists"
echo ""

# Step 3: Check dependencies
echo "Step 3: Checking dependencies..."
if [ -f "requirements.txt" ]; then
    echo "Installing/updating dependencies..."
    venv/bin/pip install -q --upgrade pip
    venv/bin/pip install -q -r requirements.txt
    echo "✅ Dependencies installed"
else
    echo "⚠️  requirements.txt not found"
fi

echo ""

# Step 4: Check environment file
echo "Step 4: Checking environment configuration..."
if [ \! -f ".env" ]; then
    echo "⚠️  .env file not found"
    if [ -f ".env.prod.example" ]; then
        echo "Found .env.prod.example"
        read -p "Copy .env.prod.example to .env? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cp .env.prod.example .env
            echo "✅ Created .env from .env.prod.example"
            echo "⚠️  Please edit .env with your actual configuration"
        fi
    fi
else
    echo "✅ .env file exists"
fi

echo ""

# Step 5: Check Redis
echo "Step 5: Checking Redis..."
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo "✅ Redis is running"
    else
        echo "⚠️  Redis is not responding"
        echo "Start Redis with: sudo systemctl start redis"
    fi
else
    echo "⚠️  redis-cli not found. Is Redis installed?"
fi

echo ""

# Step 6: PM2 Configuration
echo "Step 6: Checking PM2 configuration..."
if [ \! -f "ecosystem.config.js" ]; then
    echo "Error: ecosystem.config.js not found"
    exit 1
fi

echo "✅ PM2 configuration exists"
echo ""

# Step 7: Start services
echo "Step 7: Starting PM2 services..."
echo ""
echo "Current PM2 processes:"
pm2 list

echo ""
read -p "Start/restart celery-redis services? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Stop existing processes if any
    pm2 delete celery-redis-api 2>/dev/null || true
    pm2 delete celery-worker 2>/dev/null || true
    
    # Start new processes
    pm2 start ecosystem.config.js
    pm2 save
    
    echo "✅ Services started"
    echo ""
    echo "Waiting 5 seconds for services to initialize..."
    sleep 5
fi

echo ""

# Step 8: Verify services
echo "Step 8: Verifying services..."
echo ""

# Check if port 8001 is listening
if netstat -tlnp 2>/dev/null | grep -q ":8001"; then
    echo "✅ Port 8001 is listening"
else
    echo "⚠️  Port 8001 is NOT listening"
fi

# Check PM2 status
echo ""
echo "PM2 Status:"
pm2 list | grep -E "celery-redis|celery-worker" || echo "No celery-redis processes found"

echo ""

# Step 9: Test API
echo "Step 9: Testing API..."
if command -v curl &> /dev/null; then
    echo "Testing http://localhost:8001/health..."
    if curl -s -f http://localhost:8001/health > /dev/null 2>&1; then
        echo "✅ API health check passed"
        curl -s http://localhost:8001/health | head -5
    else
        echo "⚠️  API health check failed"
        echo "Check logs with: pm2 logs celery-redis-api"
    fi
else
    echo "⚠️  curl not found, skipping API test"
fi

echo ""

# Step 10: Nginx verification
echo "Step 10: Checking Nginx configuration..."
if [ -f "/etc/nginx/sites-available/tasks.ft.tc.conf" ]; then
    echo "✅ Nginx config exists: /etc/nginx/sites-available/tasks.ft.tc.conf"
    
    if [ -L "/etc/nginx/sites-enabled/tasks.ft.tc.conf" ]; then
        echo "✅ Nginx config is enabled"
    else
        echo "⚠️  Nginx config is NOT enabled"
        echo "Enable with: sudo ln -s /etc/nginx/sites-available/tasks.ft.tc.conf /etc/nginx/sites-enabled/"
    fi
    
    # Test nginx config
    if sudo nginx -t 2>&1 | grep -q "successful"; then
        echo "✅ Nginx configuration is valid"
    else
        echo "⚠️  Nginx configuration has errors"
    fi
else
    echo "⚠️  Nginx config not found"
fi

echo ""
echo "========================================="
echo "Setup Complete\!"
echo "========================================="
echo ""
echo "Service Information:"
echo "  - API Port: 8001"
echo "  - Domain: tasks.ft.tc"
echo "  - PM2 Processes: celery-redis-api, celery-worker"
echo ""
echo "Useful Commands:"
echo "  pm2 list                    - List all processes"
echo "  pm2 logs celery-redis-api   - View API logs"
echo "  pm2 logs celery-worker      - View worker logs"
echo "  pm2 restart all             - Restart all processes"
echo "  pm2 monit                   - Monitor processes"
echo ""
echo "Test URLs:"
echo "  http://localhost:8001/health"
echo "  https://tasks.ft.tc/health"
echo ""

