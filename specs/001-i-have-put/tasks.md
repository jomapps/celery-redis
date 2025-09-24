# Tasks: AI Movie Platform - Celery/Redis Task Service

**Input**: Design documents from `/specs/001-i-have-put/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → Tech stack: Python 3.11, FastAPI, Celery, Redis, uvicorn, httpx, pydantic
   → Structure: Single project with src/ and tests/ directories
2. Load design documents:
   → data-model.md: 6 entities (Task, Project, MediaResult, TaskQueue, WorkerStatus, ProcessingProgress)
   → contracts/openapi.yaml: 8 API endpoints
   → quickstart.md: 5 test scenarios (video, image, audio, project management, monitoring)
3. Generate tasks by category:
   → Setup: Project init, dependencies, infrastructure
   → Tests: Contract tests, integration tests  
   → Core: Models, services, workers
   → Integration: External services, middleware
   → Polish: Documentation, performance, deployment
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Tests before implementation (TDD)
   → Infrastructure before everything else
5. Total tasks: 43 sequential tasks with parallel execution opportunities
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root
- All paths relative to repository root

## Phase 3.1: Infrastructure Setup
- [ ] T001 Create project structure with src/, tests/, app/, docker/ directories
- [ ] T002 Initialize Python project with requirements.txt containing FastAPI, Celery, Redis, uvicorn, httpx, pydantic, pytest
- [ ] T003 [P] Configure linting with black, flake8, and mypy in pyproject.toml
- [ ] T004 [P] Create .env.example with all required environment variables per plan

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests (8 endpoints from OpenAPI spec)
- [ ] T005 [P] Contract test GET /api/v1/health in tests/contract/test_health_get.py
- [ ] T006 [P] Contract test POST /api/v1/tasks/submit in tests/contract/test_tasks_submit_post.py
- [ ] T007 [P] Contract test GET /api/v1/tasks/{task_id}/status in tests/contract/test_tasks_status_get.py
- [ ] T008 [P] Contract test DELETE /api/v1/tasks/{task_id}/cancel in tests/contract/test_tasks_cancel_delete.py
- [ ] T009 [P] Contract test POST /api/v1/tasks/{task_id}/retry in tests/contract/test_tasks_retry_post.py
- [ ] T010 [P] Contract test GET /api/v1/projects/{project_id}/tasks in tests/contract/test_projects_tasks_get.py
- [ ] T011 [P] Contract test GET /api/v1/workers/status in tests/contract/test_workers_status_get.py

### Integration Tests (5 scenarios from quickstart)
- [ ] T012 [P] Integration test video generation workflow in tests/integration/test_video_generation.py
- [ ] T013 [P] Integration test image generation workflow in tests/integration/test_image_generation.py
- [ ] T014 [P] Integration test audio synthesis workflow in tests/integration/test_audio_synthesis.py
- [ ] T015 [P] Integration test project task management in tests/integration/test_project_management.py
- [ ] T016 [P] Integration test system monitoring in tests/integration/test_system_monitoring.py

## Phase 3.3: Core Infrastructure (ONLY after tests are failing)
- [ ] T017 Redis connection configuration in app/config.py
- [ ] T018 Celery app initialization in app/celery_app.py
- [ ] T019 FastAPI app creation with middleware in app/main.py
- [ ] T020 API key authentication middleware in app/middleware/auth.py

## Phase 3.4: Data Models (6 entities from data-model.md)
- [ ] T021 [P] Task model with validation in app/models/task.py
- [ ] T022 [P] Project model with validation in app/models/project.py
- [ ] T023 [P] MediaResult model with validation in app/models/media_result.py
- [ ] T024 [P] TaskQueue model in app/models/task_queue.py
- [ ] T025 [P] WorkerStatus model in app/models/worker_status.py
- [ ] T026 [P] ProcessingProgress model in app/models/processing_progress.py

## Phase 3.5: Service Layer
- [ ] T027 Redis service for data persistence in app/services/redis_service.py
- [ ] T028 Task management service in app/services/task_service.py
- [ ] T029 Project management service in app/services/project_service.py
- [ ] T030 Worker monitoring service in app/services/worker_service.py

## Phase 3.6: API Implementation (8 endpoints to pass contract tests)
- [ ] T031 Health check endpoint implementation in app/api/health.py
- [ ] T032 Task submission endpoint implementation in app/api/tasks.py
- [ ] T033 Task status endpoint implementation in app/api/tasks.py
- [ ] T034 Task cancellation endpoint implementation in app/api/tasks.py
- [ ] T035 Task retry endpoint implementation in app/api/tasks.py
- [ ] T036 Project tasks listing endpoint implementation in app/api/projects.py
- [ ] T037 Worker status endpoint implementation in app/api/workers.py

## Phase 3.7: Worker Implementation (3 task types)
- [ ] T038 Base task class with project isolation in app/tasks/base_task.py
- [ ] T039 Video generation worker in app/tasks/video_tasks.py
- [ ] T040 Image generation worker in app/tasks/image_tasks.py
- [ ] T041 Audio synthesis worker in app/tasks/audio_tasks.py

## Phase 3.8: External Integrations
- [ ] T042 PayloadCMS client implementation in app/services/payload_client.py
- [ ] T043 Cloudflare R2 storage client in app/services/storage_client.py

## Phase 3.9: Deployment and Polish
- [ ] T044 [P] Docker configuration for API server in docker/Dockerfile.api
- [ ] T045 [P] Docker configuration for workers in docker/Dockerfile.worker
- [ ] T046 [P] Docker Compose configuration in docker/docker-compose.yml
- [ ] T047 [P] GPU monitoring utilities in app/utils/monitoring.py
- [ ] T048 [P] Logging configuration in app/utils/logging.py
- [ ] T049 Unit tests for utility functions in tests/unit/
- [ ] T050 Performance validation (<300min task timeout)
- [ ] T051 Quickstart validation by running all scenarios

## Dependencies
### Critical Path
- T001-T004 (setup) before everything else
- T005-T016 (tests) before T017-T051 (implementation)
- T017-T020 (infrastructure) before T021-T030 (models/services)
- T021-T030 (core) before T031-T037 (API endpoints)
- T038 (base task) before T039-T041 (worker implementations)
- T042-T043 (integrations) before worker implementations complete
- T031-T043 (all implementation) before T044-T051 (deployment/polish)

### Parallel Execution Opportunities
- T003-T004 can run together (different config files)
- T005-T016 can run together (different test files)
- T021-T026 can run together (different model files)
- T039-T041 can run together after T038 completes (different worker files)
- T044-T048 can run together (different deployment files)

## Parallel Execution Examples

### Setup Phase
```bash
# Launch T003-T004 together:
Task: "Configure linting with black, flake8, and mypy in pyproject.toml"
Task: "Create .env.example with all required environment variables per plan"
```

### Contract Tests Phase
```bash
# Launch T005-T011 together:
Task: "Contract test GET /api/v1/health in tests/contract/test_health_get.py"
Task: "Contract test POST /api/v1/tasks/submit in tests/contract/test_tasks_submit_post.py"
Task: "Contract test GET /api/v1/tasks/{task_id}/status in tests/contract/test_tasks_status_get.py"
Task: "Contract test DELETE /api/v1/tasks/{task_id}/cancel in tests/contract/test_tasks_cancel_delete.py"
Task: "Contract test POST /api/v1/tasks/{task_id}/retry in tests/contract/test_tasks_retry_post.py"
Task: "Contract test GET /api/v1/projects/{project_id}/tasks in tests/contract/test_projects_tasks_get.py"
Task: "Contract test GET /api/v1/workers/status in tests/contract/test_workers_status_get.py"
```

### Integration Tests Phase
```bash
# Launch T012-T016 together:
Task: "Integration test video generation workflow in tests/integration/test_video_generation.py"
Task: "Integration test image generation workflow in tests/integration/test_image_generation.py"
Task: "Integration test audio synthesis workflow in tests/integration/test_audio_synthesis.py"
Task: "Integration test project task management in tests/integration/test_project_management.py"
Task: "Integration test system monitoring in tests/integration/test_system_monitoring.py"
```

### Data Models Phase
```bash
# Launch T021-T026 together (after T017-T020 complete):
Task: "Task model with validation in app/models/task.py"
Task: "Project model with validation in app/models/project.py"
Task: "MediaResult model with validation in app/models/media_result.py"
Task: "TaskQueue model in app/models/task_queue.py"
Task: "WorkerStatus model in app/models/worker_status.py"
Task: "ProcessingProgress model in app/models/processing_progress.py"
```

### Worker Implementation Phase
```bash
# Launch T039-T041 together (after T038 completes):
Task: "Video generation worker in app/tasks/video_tasks.py"
Task: "Image generation worker in app/tasks/image_tasks.py"
Task: "Audio synthesis worker in app/tasks/audio_tasks.py"
```

### Deployment Phase
```bash
# Launch T044-T048 together:
Task: "Docker configuration for API server in docker/Dockerfile.api"
Task: "Docker configuration for workers in docker/Dockerfile.worker"
Task: "Docker Compose configuration in docker/docker-compose.yml"
Task: "GPU monitoring utilities in app/utils/monitoring.py"
Task: "Logging configuration in app/utils/logging.py"
```

## Validation Checklist
*GATE: Verified before task execution*

- [x] All 8 API endpoints have corresponding contract tests (T005-T011)
- [x] All 6 entities have model tasks (T021-T026)
- [x] All 5 quickstart scenarios have integration tests (T012-T016)
- [x] All tests come before implementation (T005-T016 before T017+)
- [x] Parallel tasks are truly independent (different files)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] TDD workflow enforced (tests must fail before implementation)
- [x] Critical dependencies clearly mapped
- [x] Infrastructure setup before all other work

## Notes
- All [P] tasks target different files with no dependencies
- Contract tests MUST fail before starting implementation
- Worker implementations require GPU access for testing
- Integration tests require Redis and external service mocks
- Performance validation requires actual GPU hardware
- Deployment tasks can run in parallel once implementation is complete
- Each phase gates the next - no implementation without failing tests

## Task Generation Summary
- **Setup**: 4 tasks (T001-T004)
- **Contract Tests**: 7 tasks (T005-T011) 
- **Integration Tests**: 5 tasks (T012-T016)
- **Infrastructure**: 4 tasks (T017-T020)
- **Data Models**: 6 tasks (T021-T026)
- **Services**: 4 tasks (T027-T030)
- **API Endpoints**: 7 tasks (T031-T037)
- **Workers**: 4 tasks (T038-T041)
- **External Integrations**: 2 tasks (T042-T043)
- **Deployment & Polish**: 8 tasks (T044-T051)

**Total**: 51 tasks with 25 parallel execution opportunities