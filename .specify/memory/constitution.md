<!--
SYNC IMPACT REPORT
Version change: [TEMPLATE] → 1.0.0
Modified principles: Initial constitution creation from template
Added sections: All core principles, integration standards, development workflow
Removed sections: Template placeholders
Templates requiring updates:
  ✅ Updated constitution.md
  ⚠ Pending: Follow up validation of plan-template.md constitution checks
Follow-up TODOs: None - all placeholders resolved
-->

# AI Movie Platform Task Service Constitution

## Core Principles

### I. Service-First Architecture
The AI Movie Platform Task Service MUST be designed as a standalone, self-contained service with clear API boundaries. Each service component (task processing, media handling, monitoring) MUST be independently deployable and testable. No organizational-only services without clear functional purpose are permitted. All external integrations MUST use well-defined contracts and fail gracefully when dependencies are unavailable.

### II. Test-First Development (NON-NEGOTIABLE)
TDD is mandatory: Tests MUST be written first, reviewed and approved, MUST fail, then implementation follows. The Red-Green-Refactor cycle is strictly enforced. Contract tests MUST exist for all API endpoints before implementation. Integration tests MUST cover all user scenarios from the quickstart guide. No code merges are permitted without passing tests and adequate coverage.

### III. Integration Standards
All external integrations MUST follow established patterns: PayloadCMS integration MUST use local API (`getPayload({ config })`) over REST when available. Cloudflare R2 storage MUST use S3-compatible patterns with proper error handling. GPU task processing MUST include resource monitoring and cleanup. All integrations MUST include circuit breaker patterns and graceful degradation modes.

### IV. Performance and Reliability
The system MUST handle GPU-intensive workloads with proper resource management. Task processing MUST complete within defined time limits (300min for video generation). Concurrent task processing MUST be supported without resource conflicts. All failures MUST trigger appropriate retry mechanisms with exponential backoff. System monitoring MUST track GPU utilization, memory usage, and task completion rates.

### V. Security and Isolation
Project-based isolation MUST be enforced at all levels - task queues, data storage, and media access. API authentication MUST use secure key validation for all endpoints. File uploads and media storage MUST validate content types and enforce size limits. Cross-project data access MUST be prevented through access controls and path validation. All external webhooks MUST be validated before processing.

## Technology Standards

### Language and Framework Requirements
- **Python Version**: 3.11+ with type hints mandatory for all functions
- **API Framework**: FastAPI with automatic OpenAPI documentation generation
- **Task Processing**: Celery with Redis broker for distributed processing
- **Storage**: Redis for task metadata, Cloudflare R2 for media files
- **Testing**: pytest with contract and integration test coverage
- **Deployment**: Docker containers with GPU support for workers

### PayloadCMS Integration Standards
- **Version Compatibility**: PayloadCMS 3.56+ patterns only
- **API Access**: Use `getPayload({ config })` in server components, avoid REST API when local API available
- **Type Safety**: Always run `pnpm generate:types` after schema changes, never edit generated types
- **Storage Configuration**: Use Cloudflare R2 with S3-compatible adapter and proper URL generation
- **Collection Configuration**: Custom collections in designated directories with proper access controls

## Development Workflow

### Code Quality Gates
All code changes MUST pass through these mandatory gates:
1. **Constitution Compliance**: Verify adherence to all principles before implementation
2. **Test Coverage**: Contract tests for APIs, integration tests for workflows, unit tests for utilities
3. **Performance Validation**: Load testing for concurrent task processing, memory usage monitoring
4. **Security Review**: Authentication, authorization, and input validation checks
5. **Documentation**: API documentation, deployment guides, and operational runbooks

### Task Management Standards
- **Infrastructure First**: Redis, Celery, and FastAPI configuration before feature implementation
- **TDD Workflow**: Contract tests, then integration tests, then implementation
- **Parallel Execution**: Mark independent tasks with [P] for concurrent development
- **Dependency Management**: Clear dependency mapping and sequential execution for dependent tasks

### Error Handling and Monitoring
- **Structured Logging**: JSON logs with correlation IDs for request tracing
- **Metrics Collection**: Prometheus-compatible metrics for system monitoring
- **Error Classification**: Distinguish between retryable and permanent failures
- **Alert Thresholds**: Define clear SLA boundaries and escalation procedures

## Governance

The constitution supersedes all other development practices and coding standards. Amendments require documentation of rationale, approval through pull request review, and migration plan for affected code. All code reviews MUST verify constitutional compliance before approval.

Constitutional violations MUST be justified in complexity tracking with specific rationale for why simpler alternatives are insufficient. Any complexity that cannot be justified MUST be refactored to comply with constitutional principles.

For runtime development guidance beyond constitutional requirements, refer to project-specific documentation in `docs/` directory and agent-specific files (CLAUDE.md, AGENTS.md).

**Version**: 1.0.0 | **Ratified**: 2025-09-24 | **Last Amended**: 2025-09-24