# AI Movie Platform - System Integration & Architecture

## Overview
The AI Movie Platform - Celery/Redis Task Service is a critical component of a larger distributed system for AI-powered movie production. This document defines the complete system architecture, port allocations, and integration patterns.

## Complete System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                Auto-Movie App (Port 3010)               │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────┐│
│  │  Dashboard UI   │ │ Prompt Manager  │ │ Test Studio │││
│  │  • Projects     │ │ • CRUD Prompts  │ │ • Live Test │││ 
│  │  • Progress     │ │ • Versioning    │ │ • Results   │││
│  │  • Analytics    │ │ • Approval      │ │ • Compare   │││
│  └─────────────────┘ └─────────────────┘ └─────────────┘││
│                              │                          ││
│  ┌─────────────────────────────────────────────────────┐││
│  │              PayloadCMS Collections                 │││
│  │  • Projects    • Prompts     • Test Results         │││
│  │  • Sessions    • Versions    • Agent Configs        │││
│  │  • Media       • Users       • Workflows            │││
│  └─────────────────────────────────────────────────────┘││
└─────────────────────────┬───────────────────────────────┘
                          │ HTTP REST API Calls
┌─────────────────────────▼───────────────────────────────┐
│              Background Services Layer                  │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────┐│
│  │ Celery Tasks    │ │ MCP Brain       │ │ Agent Orch  ││
│  │ THIS SERVICE    │ │ Port: 8002      │ │ Port: 8003  ││
│  │ Port: 8001      │ │ • Jina v4       │ │ • LangGraph ││
│  │ • GPU Tasks     │ │ • Neo4j Graph   │ │ • 50+ Agents││
│  │ • Test Requests │ │ • Embeddings    │ │ • BAML      ││
│  │ • Media Gen     │ │ • Knowledge     │ │ • Workflows ││
│  │ • Audio Process │ │                 │ │             ││
│  └─────────────────┘ └─────────────────┘ └─────────────┘│
│                              │                          │
│  ┌─────────────────────────────────────────────────────┐│
│  │           Infrastructure & Data Layer               ││
│  │  Redis:6379    Neo4j:7474,7687    MongoDB:27017    ││
│  │  Prometheus:9090   Grafana:3001   Health:8100      ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

## Port Allocation & Service Registry

### Core Services (Always Running)
| Service | Local Port | Dev Domain | Prod Domain | Purpose |
|---------|------------|------------|-------------|---------|
| **Auto-Movie App** | 3010 | auto-movie.ngrok.pro | auto-movie.ft.tc | Main UI, PayloadCMS, prompt mgmt |
| **Celery Task Service** | 8001 | tasks.ngrok.pro | tasks.ft.tc | GPU processing, video/image/audio |
| **MCP Brain Service** | 8002 | brain.ngrok.pro | brain.ft.tc | Knowledge graph, embeddings |
| **Redis Server** | 6379 | - | - | Task queue, cache, sessions |
| **Neo4j Database** | 7474/7687 | neo4j.ngrok.pro | neo4j.ft.tc | Graph database |
| **MongoDB** | 27017 | - | - | PayloadCMS data storage |

### Extended Services (Phase 4+)
| Service | Local Port | Dev Domain | Prod Domain | Purpose |
|---------|------------|------------|-------------|---------|
| **LangGraph Orchestrator** | 8003 | agents.ngrok.pro | agents.ft.tc | Agent workflow coordination |
| **Story MCP Server** | 8010 | story.ngrok.pro | story.ft.tc | Story-specific AI operations |
| **Character MCP Server** | 8011 | characters.ngrok.pro | characters.ft.tc | Character creation/management |
| **Visual MCP Server** | 8012 | visuals.ngrok.pro | visuals.ft.tc | Visual asset generation |
| **Audio MCP Server** | 8013 | audio.ngrok.pro | audio.ft.tc | Audio processing/synthesis |
| **Asset MCP Server** | 8014 | assets.ngrok.pro | assets.ft.tc | Digital asset management |

### Monitoring & Management Services
| Service | Local Port | Dev Domain | Prod Domain | Purpose |
|---------|------------|------------|-------------|---------|
| **Prometheus Metrics** | 9090 | metrics.ngrok.pro | metrics.ft.tc | Performance monitoring |
| **Grafana Dashboard** | 3001 | dashboard.ngrok.pro | dashboard.ft.tc | Visual monitoring dashboards |
| **System Health API** | 8100 | health.ngrok.pro | health.ft.tc | Service health checks |
| **Redis Insight** | 8101 | redis.ngrok.pro | redis.ft.tc | Redis monitoring |
| **MongoDB Express** | 8102 | mongo.ngrok.pro | mongo.ft.tc | MongoDB administration |

### Development Services  
| Service | Local Port | Dev Domain | Prod Domain | Purpose |
|---------|------------|------------|-------------|---------|
| **API Documentation** | 8300 | app-docs.ngrok.pro | app-docs.ft.tc | OpenAPI/Swagger docs |
| **Test Environment** | 3011 | app-test.ngrok.pro | app-test.ft.tc | Staging environment |
| **Upload Proxy** | 8200 | uploads.ngrok.pro | uploads.ft.tc | Direct file upload handling |

## Service Communication Patterns

### 1. Auto-Movie App → Task Service (Primary Integration)

**Direction**: Auto-Movie App calls Task Service  
**Protocol**: HTTP REST API  
**Authentication**: API Key via X-API-Key header  
**Ports**: 3010 → 8001

**Integration Endpoints**:
```python
# Task submission from Auto-Movie App prompt testing
POST http://localhost:8001/api/v1/tasks/submit
{
  "project_id": "test_project",  # Special project for prompt tests
  "task_type": "test_prompt",
  "task_data": {
    "prompt_id": "prompt_uuid",
    "prompt_template": "{{BAML_template}}",
    "agent_type": "character_creator",
    "test_parameters": {...},
    "test_result_id": "test_result_uuid"
  },
  "callback_url": "http://localhost:3010/api/webhooks/task-complete",
  "metadata": {
    "userId": "user_id",
    "testResultId": "test_result_id"
  }
}
```

### 2. Task Service → Auto-Movie App (Webhook Callbacks)

**Direction**: Task Service notifies Auto-Movie App  
**Protocol**: HTTP POST webhooks  
**Authentication**: API Key  
**Ports**: 8001 → 3010

**Webhook Payload**:
```python
# Task completion notification
POST http://localhost:3010/api/webhooks/task-complete
{
  "task_id": "task_uuid",
  "status": "completed|failed",
  "project_id": "test_project",
  "result": {
    "media_url": "https://media.ft.tc/projects/test_project/...",
    "payload_media_id": "media_uuid",
    "metadata": {
      "processing_time": 45.2,
      "tokens_used": 1250,
      "output_data": {...}
    }
  },
  "error": null,
  "metadata": {
    "testResultId": "test_result_id",
    "userId": "user_id"
  }
}
```

### 3. Task Service → MCP Brain Service (Future Integration)

**Direction**: Task Service queries Brain Service for context  
**Protocol**: HTTP REST API  
**Ports**: 8001 → 8002

**Integration Pattern**:
```python
# Knowledge retrieval for enhanced task processing
GET http://localhost:8002/api/v1/knowledge/query
{
  "project_id": "detective_series_001",
  "context_type": "character_context",
  "query": "Detective protagonist personality traits"
}
```

## Environment Configuration by Environment

### Development Environment (.env)
```bash
# Core service ports
AUTO_MOVIE_APP_URL=http://localhost:3010
CELERY_TASK_SERVICE_URL=http://localhost:8001
MCP_BRAIN_SERVICE_URL=http://localhost:8002

# PayloadCMS integration
PAYLOAD_API_URL=http://localhost:3010/api
WEBHOOK_BASE_URL=http://localhost:3010/api/webhooks

# Infrastructure
REDIS_URL=redis://localhost:6379/0
NEO4J_URI=bolt://localhost:7687
MONGODB_URI=mongodb://localhost:27017/auto-movie
```

### Staging Environment (ngrok tunnels)
```bash
# Core service URLs
AUTO_MOVIE_APP_URL=https://auto-movie.ngrok.pro
CELERY_TASK_SERVICE_URL=https://tasks.ngrok.pro
MCP_BRAIN_SERVICE_URL=https://brain.ngrok.pro

# PayloadCMS integration
PAYLOAD_API_URL=https://auto-movie.ngrok.pro/api
WEBHOOK_BASE_URL=https://auto-movie.ngrok.pro/api/webhooks

# Monitoring
PROMETHEUS_URL=https://metrics.ngrok.pro
GRAFANA_URL=https://dashboard.ngrok.pro
```

### Production Environment (.env.production)
```bash
# Core service URLs
AUTO_MOVIE_APP_URL=https://auto-movie.ft.tc
CELERY_TASK_SERVICE_URL=https://tasks.ft.tc
MCP_BRAIN_SERVICE_URL=https://brain.ft.tc

# PayloadCMS integration
PAYLOAD_API_URL=https://auto-movie.ft.tc/api
WEBHOOK_BASE_URL=https://auto-movie.ft.tc/api/webhooks

# Media CDN
R2_PUBLIC_URL=https://media.ft.tc

# Monitoring
PROMETHEUS_URL=https://metrics.ft.tc
GRAFANA_URL=https://dashboard.ft.tc
```

## Service Discovery Configuration

```python
# app/config/service_discovery.py
from enum import Enum
from typing import Dict

class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

SERVICE_REGISTRY = {
    Environment.DEVELOPMENT: {
        "auto_movie": "http://localhost:3010",
        "task_service": "http://localhost:8001",
        "brain_service": "http://localhost:8002",
        "neo4j": "http://localhost:7474",
        "redis": "redis://localhost:6379/0",
        "mongodb": "mongodb://localhost:27017",
        "prometheus": "http://localhost:9090",
        "grafana": "http://localhost:3001"
    },
    Environment.STAGING: {
        "auto_movie": "https://auto-movie.ngrok.pro",
        "task_service": "https://tasks.ngrok.pro",
        "brain_service": "https://brain.ngrok.pro",
        "neo4j": "https://neo4j.ngrok.pro",
        "prometheus": "https://metrics.ngrok.pro",
        "grafana": "https://dashboard.ngrok.pro"
    },
    Environment.PRODUCTION: {
        "auto_movie": "https://auto-movie.ft.tc",
        "task_service": "https://tasks.ft.tc",
        "brain_service": "https://brain.ft.tc",
        "neo4j": "https://neo4j.ft.tc",
        "media_cdn": "https://media.ft.tc",
        "prometheus": "https://metrics.ft.tc",
        "grafana": "https://dashboard.ft.tc"
    }
}

def get_service_url(service_name: str, environment: Environment = Environment.DEVELOPMENT) -> str:
    """Get service URL for the current environment"""
    return SERVICE_REGISTRY[environment].get(service_name, "")
```

## Docker Compose Integration

```yaml
# docker-compose.yml - Complete system orchestration
version: '3.8'

services:
  # Core Application Services
  auto-movie:
    build: ../auto-movie-app
    ports:
      - "3010:3000"
    environment:
      - NEXT_PUBLIC_TASK_SERVICE_URL=http://celery-api:8001
      - NEXT_PUBLIC_BRAIN_SERVICE_URL=http://mcp-brain:8002
      
  celery-api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    ports:
      - "8001:8001"
    environment:
      - AUTO_MOVIE_APP_URL=http://auto-movie:3000
      - PAYLOAD_API_URL=http://auto-movie:3000/api
    depends_on:
      - redis
      - auto-movie
      
  mcp-brain:
    build: ../mcp-brain-service
    ports:
      - "8002:8002"
    depends_on:
      - neo4j
      - mongodb
      
  # Infrastructure Services
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    
  neo4j:
    image: neo4j:5
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/password
      
  mongodb:
    image: mongo:7
    ports:
      - "27017:27017"
      
  # Monitoring Services
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
      
  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
```

## Integration Workflows

### 1. Prompt Testing Workflow (Auto-Movie App → Task Service)

1. User creates/edits prompt in Auto-Movie App prompt manager
2. User clicks "Test" in Test Studio
3. Auto-Movie App submits test task to Task Service:
   ```
   POST http://localhost:8001/api/v1/tasks/submit
   Content-Type: application/json
   X-API-Key: shared-api-key
   ```
4. Task Service queues prompt test task with special `test_project` isolation
5. Celery worker processes prompt using appropriate AI agent
6. Generated results uploaded to Cloudflare R2
7. Task Service sends webhook to Auto-Movie App with results
8. Auto-Movie App updates test result in PayloadCMS
9. User sees results in Test Studio real-time interface

### 2. Production Media Generation (Auto-Movie App → Task Service)

1. Auto-Movie App production workflow triggers media generation
2. Task submitted with actual project ID (not test_project)
3. Task Service processes with full GPU resources
4. Results integrated into PayloadCMS media collection
5. Media available for further production pipeline steps

### 3. Knowledge Integration (Task Service → MCP Brain)

1. Task Service requests relevant context from MCP Brain
2. Enhanced task processing with project-specific knowledge
3. Results stored back to knowledge graph for future enhancement

## Security & Isolation

### Project-Based Isolation
- **test_project**: Special project ID for Auto-Movie App prompt testing
- **Production projects**: Real movie projects with full isolation
- **Cross-project validation**: Constitutional requirement enforced at all levels

### API Authentication
- **Shared API keys** between Auto-Movie App and Task Service
- **Service-to-service authentication** via secure headers
- **Webhook validation** to prevent unauthorized callbacks

### Network Security
- **Internal service communication** within Docker network
- **External exposure** only through defined ports
- **Environment-specific domains** for development, staging, production

## Constitutional Compliance

This system architecture aligns with our constitutional requirements:

- ✅ **Service-First Architecture**: Clear service boundaries with well-defined APIs
- ✅ **Integration Standards**: PayloadCMS integration via Auto-Movie App patterns
- ✅ **Performance and Reliability**: Distributed processing with monitoring
- ✅ **Security and Isolation**: Project-based isolation across service boundaries
- ✅ **Test-First Development**: Comprehensive testing infrastructure

## Deployment Commands

### Development Setup
```bash
# Start core infrastructure
docker-compose up -d redis mongodb neo4j

# Start Auto-Movie App  
cd ../auto-movie-app && npm run dev

# Start Task Service
cd celery-task-service && uvicorn app.main:app --port 8001 --reload

# Start MCP Brain (when available)
cd ../mcp-brain-service && python -m uvicorn main:app --port 8002
```

### Staging Setup (ngrok tunnels)
```bash
# Core services
ngrok http 3010 --domain=auto-movie.ngrok.pro &
ngrok http 8001 --domain=tasks.ngrok.pro &  
ngrok http 8002 --domain=brain.ngrok.pro &
ngrok http 7474 --domain=neo4j.ngrok.pro &
```

### Production Deployment
```bash
# Deploy to production domains
docker-compose -f docker-compose.prod.yml up -d
```

This comprehensive integration ensures the Task Service operates seamlessly within the larger AI Movie Platform ecosystem while maintaining constitutional compliance and proper service isolation.