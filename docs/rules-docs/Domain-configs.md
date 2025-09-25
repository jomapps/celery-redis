# AI Movie Platform - Domain & Port Configuration

## Core Application Services

### 1. **Auto-Movie App** (Main Dashboard & PayloadCMS)
- **Local**: `localhost:3010`
- **Dev**: `auto-movie.ngrok.pro` 
- **Prod**: `auto-movie.ft.tc`
- **Purpose**: Main user interface, PayloadCMS admin, prompt management, chat interface

### 2. **Celery Task Service** (GPU Processing)
- **Local**: `localhost:8001`
- **Dev**: `tasks.ngrok.pro`
- **Prod**: `tasks.ft.tc`
- **Purpose**: Video/image generation, audio processing, heavy AI tasks

### 3. **MCP Brain Service** (Knowledge Graph)
- **Local**: `localhost:8002`
- **Dev**: `brain.ngrok.pro`
- **Prod**: `brain.ft.tc`
- **Purpose**: Jina v4 embeddings + Neo4j knowledge graph

## Database & Infrastructure Services

### 4. **Neo4j Database Interface**
- **Local**: `localhost:7474` (HTTP), `localhost:7687` (Bolt)
- **Dev**: `neo4j.ngrok.pro`
- **Prod**: `neo4j.ft.tc` (admin interface only, internal bolt connection)
- **Purpose**: Graph database web interface for debugging

### 5. **Redis Insight** (Optional - Redis Management)
- **Local**: `localhost:8101`
- **Dev**: `redis.ngrok.pro`
- **Prod**: `redis.ft.tc`
- **Purpose**: Redis cache and queue monitoring

### 6. **MongoDB Express** (Optional - Database Admin)
- **Local**: `localhost:8102`
- **Dev**: `mongo.ngrok.pro`
- **Prod**: `mongo.ft.tc`
- **Purpose**: MongoDB administration interface

## Agent & Orchestration Services

### 7. **LangGraph Agent Orchestrator** (Future Phase 4)
- **Local**: `localhost:8003`
- **Dev**: `agents.ngrok.pro`
- **Prod**: `agents.ft.tc`
- **Purpose**: Agent workflow coordination

### 8. **Domain-Specific MCP Servers** (Future Phases)

#### Story MCP Server
- **Local**: `localhost:8010`
- **Dev**: `story.ngrok.pro`
- **Prod**: `story.ft.tc`

#### Character MCP Server  
- **Local**: `localhost:8011`
- **Dev**: `characters.ngrok.pro`
- **Prod**: `characters.ft.tc`

#### Visual MCP Server
- **Local**: `localhost:8012`
- **Dev**: `visuals.ngrok.pro`
- **Prod**: `visuals.ft.tc`

#### Audio MCP Server
- **Local**: `localhost:8013`
- **Dev**: `audio.ngrok.pro`
- **Prod**: `audio.ft.tc`

#### Asset MCP Server
- **Local**: `localhost:8014`
- **Dev**: `assets.ngrok.pro`
- **Prod**: `assets.ft.tc`

## Monitoring & Analytics Services

### 9. **Prometheus Metrics**
- **Local**: `localhost:9090`
- **Dev**: `metrics.ngrok.pro`
- **Prod**: `metrics.ft.tc`
- **Purpose**: Performance monitoring and metrics collection

### 10. **Grafana Dashboard**
- **Local**: `localhost:3001`
- **Dev**: `dash-board.ngrok.pro`
- **Prod**: `dash-board.ft.tc`
- **Purpose**: Visual monitoring dashboards

### 11. **System Health API**
- **Local**: `localhost:8100`
- **Dev**: `health.ngrok.pro`
- **Prod**: `health.ft.tc`
- **Purpose**: Service health checks and status monitoring

## Media & CDN Services

### 12. **Media CDN** (Cloudflare R2 Custom Domain)
- **Dev**: `media-dev.ft.tc`
- **Prod**: `media.ft.tc`
- **Purpose**: Optimized media delivery for generated assets

### 13. **File Upload Proxy** (Optional)
- **Local**: `localhost:8200`
- **Dev**: `uploads.ngrok.pro`
- **Prod**: `uploads.ft.tc`
- **Purpose**: Direct file upload handling, bypassing main app

## Development & Testing Services

### 14. **API Documentation** (OpenAPI/Swagger)
- **Local**: `localhost:8300`
- **Dev**: `app-docs.ngrok.pro`
- **Prod**: `app-docs.ft.tc`
- **Purpose**: Interactive API documentation

### 15. **Test Environment**
- **Local**: `localhost:3011`
- **Dev**: `app-test.ngrok.pro`
- **Prod**: `app-test.ft.tc` (staging environment)
- **Purpose**: Isolated testing environment

## Port Allocation Summary

### **Core Services (Always Running)**
```bash
3010 - Auto-Movie App (Main)
8001 - Celery Task Service  
8002 - MCP Brain Service
7474 - Neo4j HTTP Interface
7687 - Neo4j Bolt Protocol
6379 - Redis Server
27017 - MongoDB Server
```

### **Extended Services (Phase 4+)**
```bash
8003 - LangGraph Orchestrator
8010-8014 - Domain MCP Servers
9090 - Prometheus Metrics
3001 - Grafana Dashboard
8100 - Health Check API
8101 - Redis Insight
8102 - MongoDB Express
```

### **Development Services**
```bash
8200 - Upload Proxy
8300 - API Documentation  
3011 - Test Environment
```

## Ngrok Configuration Commands

### Core Services Setup
```bash
# Auto-Movie App
ngrok http 3010 --domain=auto-movie.ngrok.pro

# Task Service
ngrok http 8001 --domain=tasks.ngrok.pro

# Brain Service  
ngrok http 8002 --domain=brain.ngrok.pro

# Neo4j Interface
ngrok http 7474 --domain=neo4j.ngrok.pro
```

### Extended Services
```bash
# Agent Orchestrator
ngrok http 8003 --domain=agents.ngrok.pro

# Domain MCP Servers
ngrok http 8010 --domain=story.ngrok.pro
ngrok http 8011 --domain=characters.ngrok.pro
ngrok http 8012 --domain=visuals.ngrok.pro
ngrok http 8013 --domain=audio.ngrok.pro
ngrok http 8014 --domain=assets.ngrok.pro

# Monitoring
ngrok http 9090 --domain=metrics.ngrok.pro
ngrok http 3001 --domain=dashboard.ngrok.pro
```

## Docker Compose Port Mapping

```yaml
# docker-compose.yml
version: '3.8'

services:
  auto-movie:
    ports:
      - "3010:3000"
    
  celery-api:
    ports:
      - "8001:8001"
      
  mcp-brain:
    ports:
      - "8002:8002"
      
  neo4j:
    ports:
      - "7474:7474"
      - "7687:7687"
      
  redis:
    ports:
      - "6379:6379"
      
  mongodb:
    ports:
      - "27017:27017"
```

## Environment Configuration

### **Auto-Movie App (.env)**
```bash
PORT=3000
PAYLOAD_PUBLIC_SERVER_URL=http://localhost:3010

# Development
NEXT_PUBLIC_TASK_SERVICE_URL=http://localhost:8001
NEXT_PUBLIC_BRAIN_SERVICE_URL=http://localhost:8002

# Production URLs  
NEXT_PUBLIC_TASK_SERVICE_URL=https://tasks.ft.tc
NEXT_PUBLIC_BRAIN_SERVICE_URL=https://brain.ft.tc
```

### **Service Discovery Configuration**
```typescript
// src/config/services.ts
const serviceUrls = {
  development: {
    autoMovie: 'http://localhost:3010',
    taskService: 'http://localhost:8001', 
    brainService: 'http://localhost:8002',
    neo4j: 'http://localhost:7474',
  },
  staging: {
    autoMovie: 'https://auto-movie.ngrok.pro',
    taskService: 'https://tasks.ngrok.pro',
    brainService: 'https://brain.ngrok.pro', 
    neo4j: 'https://neo4j.ngrok.pro',
  },
  production: {
    autoMovie: 'https://auto-movie.ft.tc',
    taskService: 'https://tasks.ft.tc',
    brainService: 'https://brain.ft.tc',
    neo4j: 'https://neo4j.ft.tc',
  }
}
```

This gives you a complete, scalable domain architecture that grows with your platform development phases!