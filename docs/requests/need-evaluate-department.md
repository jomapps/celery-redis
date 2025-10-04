# Implementation Guide: `evaluate_department` Task for Celery-Redis

## Overview

This document provides complete specifications for implementing the `evaluate_department` task type in the Celery-Redis task service at `https://tasks.ft.tc`.

**Purpose**: Evaluate movie production departments (Story, Character, Production, etc.) based on gathered content and provide AI-powered quality ratings, issues, and suggestions.

**Integration**: This task integrates with the Aladdin application's Project Readiness system and uses the existing webhook infrastructure.

---

## 1. Task Type Definition

### Add to Task Type Enum

**File**: `celery-redis/app/models/task.py`

```python
class TaskType(str, Enum):
    GENERATE_VIDEO = "generate_video"
    GENERATE_IMAGE = "generate_image"
    PROCESS_AUDIO = "process_audio"
    RENDER_ANIMATION = "render_animation"
    TEST_PROMPT = "test_prompt"
    EVALUATE_DEPARTMENT = "evaluate_department"  # ← ADD THIS
```

---

## 2. Input Data Structure

### Task Submission Request

```json
{
  "project_id": "68df4dab400c86a6a8cf40c6",
  "task_type": "evaluate_department",
  "task_data": {
    "department_slug": "story",
    "department_number": 1,
    "gather_data": [
      {
        "content": "Story content here...",
        "summary": "Brief summary",
        "context": "Context information",
        "imageUrl": "https://...",
        "documentUrl": "https://..."
      }
    ],
    "previous_evaluations": [
      {
        "department": "story",
        "rating": 85,
        "summary": "Strong narrative foundation"
      }
    ],
    "threshold": 80
  },
  "priority": 1,
  "callback_url": "https://aladdin.ngrok.pro/api/webhooks/evaluation-complete",
  "metadata": {
    "user_id": "user123",
    "department_id": "dept-story-001"
  }
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_id` | string | Yes | Unique project identifier |
| `task_type` | string | Yes | Must be `"evaluate_department"` |
| `task_data.department_slug` | string | Yes | Department name (e.g., "story", "character", "production") |
| `task_data.department_number` | integer | Yes | Sequential department number (1-12) |
| `task_data.gather_data` | array | Yes | Array of gathered content items (see below) |
| `task_data.previous_evaluations` | array | No | Array of previous department evaluations |
| `task_data.threshold` | integer | Yes | Minimum passing score (0-100) |
| `priority` | integer | No | Task priority (1=high, 2=normal, 3=low) |
| `callback_url` | string | Yes | Webhook URL for completion notification |
| `metadata` | object | No | Custom metadata to pass through |

### Gather Data Item Structure

```typescript
{
  "content": string,      // Main content text (required)
  "summary": string,      // Brief summary (optional)
  "context": string,      // Additional context (optional)
  "imageUrl": string,     // URL to related image (optional)
  "documentUrl": string   // URL to related document (optional)
}
```

### Previous Evaluation Structure

```typescript
{
  "department": string,   // Department slug
  "rating": number,       // Score 0-100
  "summary": string       // Evaluation summary
}
```

---

## 3. Expected Output Structure

### Success Result

```json
{
  "department": "story",
  "rating": 85,
  "evaluation_result": "pass",
  "evaluation_summary": "The story department has strong narrative structure with well-developed characters and clear three-act progression. The protagonist's journey is compelling and the conflict is well-established.",
  "issues": [
    "Character backstory needs more depth",
    "Third act resolution feels rushed",
    "Supporting character arcs underdeveloped"
  ],
  "suggestions": [
    "Add flashback scenes to establish character motivation",
    "Extend climax sequence by 2-3 minutes",
    "Develop supporting character relationships"
  ],
  "iteration_count": 3,
  "processing_time": 45.2,
  "metadata": {
    "model": "gpt-4",
    "tokens_used": 2500,
    "confidence_score": 0.92
  }
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `department` | string | Yes | Department slug (echo from input) |
| `rating` | integer | Yes | Quality score 0-100 |
| `evaluation_result` | string | Yes | "pass" if rating >= threshold, else "fail" |
| `evaluation_summary` | string | Yes | 2-3 sentence high-level assessment |
| `issues` | array[string] | Yes | 3-5 specific problems identified |
| `suggestions` | array[string] | Yes | 3-5 actionable improvement recommendations |
| `iteration_count` | integer | Yes | Number of AI refinement iterations |
| `processing_time` | number | Yes | Processing time in seconds |
| `metadata.model` | string | Yes | AI model used (e.g., "gpt-4") |
| `metadata.tokens_used` | integer | Yes | Total tokens consumed |
| `metadata.confidence_score` | number | No | Confidence metric 0.0-1.0 |

---

## 4. Task Implementation

### Create New Task File

**File**: `celery-redis/app/tasks/evaluation_tasks.py`

```python
from celery import Task
from typing import Dict, Any, List
import structlog
from datetime import datetime
import json

from .base_task import BaseTaskWithBrain
from ..clients.brain_client import BrainServiceClient

logger = structlog.get_logger(__name__)


class EvaluateDepartmentTask(BaseTaskWithBrain):
    """
    Evaluate a department's readiness based on gathered data
    Uses AI to analyze content quality and provide ratings
    """
    
    name = "evaluate_department"
    
    def execute_task(
        self,
        project_id: str,
        department_slug: str,
        department_number: int,
        gather_data: List[Dict[str, Any]],
        previous_evaluations: List[Dict[str, Any]],
        threshold: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Main evaluation logic
        
        Args:
            project_id: Project identifier
            department_slug: Department name (e.g., "story", "character")
            department_number: Sequential department number
            gather_data: Array of gathered content items
            previous_evaluations: Array of previous department evaluations
            threshold: Minimum passing score (0-100)
            
        Returns:
            Evaluation result with rating, summary, issues, and suggestions
        """
        start_time = datetime.utcnow()
        
        logger.info(
            "Starting department evaluation",
            project_id=project_id,
            department=department_slug,
            gather_count=len(gather_data),
            threshold=threshold
        )
        
        # 1. Query brain service for relevant context
        brain_context = self.run_async_in_sync(
            self._get_department_context(project_id, department_slug)
        )
        
        # 2. Prepare evaluation prompt
        evaluation_prompt = self._build_evaluation_prompt(
            department_slug=department_slug,
            department_number=department_number,
            gather_data=gather_data,
            previous_evaluations=previous_evaluations,
            threshold=threshold,
            brain_context=brain_context
        )
        
        # 3. Call AI service for evaluation
        evaluation_result = self._call_ai_evaluator(
            prompt=evaluation_prompt,
            department=department_slug,
            threshold=threshold
        )
        
        # 4. Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # 5. Build result
        result = {
            "department": department_slug,
            "rating": evaluation_result["rating"],
            "evaluation_result": "pass" if evaluation_result["rating"] >= threshold else "fail",
            "evaluation_summary": evaluation_result["summary"],
            "issues": evaluation_result["issues"],
            "suggestions": evaluation_result["suggestions"],
            "iteration_count": evaluation_result.get("iteration_count", 1),
            "processing_time": processing_time,
            "metadata": {
                "model": evaluation_result.get("model", "gpt-4"),
                "tokens_used": evaluation_result.get("tokens_used", 0),
                "confidence_score": evaluation_result.get("confidence", 0.0)
            }
        }
        
        logger.info(
            "Department evaluation completed",
            project_id=project_id,
            department=department_slug,
            rating=result["rating"],
            result=result["evaluation_result"],
            processing_time=processing_time
        )
        
        return result
```


    async def _get_department_context(
        self,
        project_id: str,
        department_slug: str
    ) -> Dict[str, Any]:
        """Query brain service for relevant department context"""
        try:
            brain_client = await self.get_brain_client()
            async with brain_client.connection():
                # Query for similar evaluations and best practices
                context = await brain_client.query_department_context(
                    project_id=project_id,
                    department=department_slug
                )
                return context or {}
        except Exception as e:
            logger.warning(
                "Failed to get brain context",
                error=str(e),
                department=department_slug
            )
            return {}

    def _build_evaluation_prompt(
        self,
        department_slug: str,
        department_number: int,
        gather_data: List[Dict[str, Any]],
        previous_evaluations: List[Dict[str, Any]],
        threshold: int,
        brain_context: Dict[str, Any]
    ) -> str:
        """Build comprehensive evaluation prompt for AI"""

        # Aggregate all gathered content
        content_summary = "\n\n".join([
            f"Item {i+1}:\n{item.get('content', '')}\nSummary: {item.get('summary', 'N/A')}\nContext: {item.get('context', 'N/A')}"
            for i, item in enumerate(gather_data)
        ])

        # Format previous evaluations
        prev_eval_summary = "\n".join([
            f"- {eval['department']}: {eval['rating']}/100 - {eval['summary']}"
            for eval in previous_evaluations
        ]) if previous_evaluations else "No previous evaluations"

        prompt = f"""
You are an expert film production evaluator. Evaluate the {department_slug} department for a movie production project.

**Department**: {department_slug} (Department #{department_number})
**Threshold**: {threshold}/100 (minimum passing score)

**Gathered Content** ({len(gather_data)} items):
{content_summary}

**Previous Department Evaluations**:
{prev_eval_summary}

**Evaluation Criteria**:
1. Completeness: Is there enough information to proceed?
2. Quality: Does the content meet professional standards?
3. Coherence: Does it align with previous departments?
4. Feasibility: Can this be executed in production?

**Your Task**:
Provide a comprehensive evaluation with:
1. **Rating** (0-100): Overall quality score
2. **Summary** (2-3 sentences): High-level assessment
3. **Issues** (array): Specific problems identified (3-5 items)
4. **Suggestions** (array): Actionable improvements (3-5 items)

Return your evaluation as JSON:
{{
    "rating": <number>,
    "summary": "<string>",
    "issues": ["<issue1>", "<issue2>", ...],
    "suggestions": ["<suggestion1>", "<suggestion2>", ...],
    "iteration_count": <number>,
    "confidence": <0.0-1.0>
}}
"""
        return prompt

    def _call_ai_evaluator(
        self,
        prompt: str,
        department: str,
        threshold: int
    ) -> Dict[str, Any]:
        """
        Call your AI service (OpenAI, Anthropic, etc.) to evaluate

        TODO: Implement your actual AI integration here
        This is a placeholder implementation
        """
        # Example implementation with OpenAI (replace with your actual AI call):
        try:
            import openai

            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert film production evaluator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            # Add metadata
            result["model"] = "gpt-4"
            result["tokens_used"] = response.usage.total_tokens

            return result

        except Exception as e:
            logger.error("AI evaluation failed", error=str(e), department=department)
            # Return fallback result
            return {
                "rating": 50,
                "summary": f"Evaluation failed: {str(e)}",
                "issues": ["AI evaluation service unavailable"],
                "suggestions": ["Retry evaluation when service is available"],
                "iteration_count": 0,
                "confidence": 0.0,
                "model": "fallback",
                "tokens_used": 0
            }


# Create Celery task instance
evaluate_department = EvaluateDepartmentTask()
```

---

## 5. Register Task in Celery App

**File**: `celery-redis/app/celery_app.py`

Add the import and registration:

```python
from app.tasks.evaluation_tasks import evaluate_department

# Register tasks
celery_app.register_task(evaluate_department)
```

---

## 6. Add Route Handler

**File**: `celery-redis/app/api/tasks.py`

In the `submit_task` function, add the evaluation handler:

```python
@router.post("/tasks/submit", response_model=TaskSubmissionResponse, status_code=201)
async def submit_task(
    task_request: TaskSubmissionRequest,
    api_key: str = Depends(verify_api_key)
) -> TaskSubmissionResponse:
    # ... existing code ...

    # Add this elif block:
    elif task_request.task_type == TaskType.EVALUATE_DEPARTMENT:
        task_result = evaluate_department.delay(
            project_id=task_request.project_id,
            department_slug=task_request.task_data.get('department_slug'),
            department_number=task_request.task_data.get('department_number'),
            gather_data=task_request.task_data.get('gather_data', []),
            previous_evaluations=task_request.task_data.get('previous_evaluations', []),
            threshold=task_request.task_data.get('threshold', 80),
            callback_url=task_request.callback_url,
            metadata=task_request.metadata
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported task type: {task_request.task_type}"
        )

    # ... rest of existing code ...
```

---

## 7. Webhook Integration

### Webhook is Already Implemented

The webhook functionality is already implemented in `celery-redis/app/tasks/base_task.py`:

```python
def on_success(self, retval, task_id, args, kwargs):
    """Called when task succeeds - sends webhook automatically"""
    callback_url = kwargs.get('callback_url')
    if callback_url:
        webhook_payload = build_success_webhook_payload(
            task_id=task_id,
            project_id=project_id,
            result=retval,
            processing_time=processing_time,
            metadata=metadata
        )
        send_webhook_sync(callback_url, webhook_payload)
```

### Success Webhook Payload

```json
{
  "task_id": "abc123-def456-ghi789",
  "project_id": "68df4dab400c86a6a8cf40c6",
  "status": "completed",
  "result": {
    "department": "story",
    "rating": 85,
    "evaluation_result": "pass",
    "evaluation_summary": "Strong narrative structure...",
    "issues": ["Issue 1", "Issue 2", "Issue 3"],
    "suggestions": ["Suggestion 1", "Suggestion 2", "Suggestion 3"],
    "iteration_count": 3,
    "processing_time": 45.2,
    "metadata": {
      "model": "gpt-4",
      "tokens_used": 2500,
      "confidence_score": 0.92
    }
  },
  "processing_time": 45.2,
  "completed_at": "2025-01-15T10:35:30Z",
  "metadata": {
    "user_id": "user123",
    "department_id": "dept-story-001"
  }
}
```

### Failure Webhook Payload

```json
{
  "task_id": "abc123-def456-ghi789",
  "project_id": "68df4dab400c86a6a8cf40c6",
  "status": "failed",
  "error": "AI evaluation service timeout after 300 seconds",
  "traceback": "Traceback (most recent call last):\n  File ...",
  "failed_at": "2025-01-15T10:35:30Z",
  "metadata": {
    "user_id": "user123",
    "department_id": "dept-story-001"
  }
}
```

**Webhook Destination**: `https://aladdin.ngrok.pro/api/webhooks/evaluation-complete`

---

## 8. Environment Variables

Add these to your `.env` or environment configuration:

```bash
# AI Service (choose one based on your implementation)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Brain Service (optional but recommended)
BRAIN_SERVICE_URL=https://brain.ft.tc
BRAIN_API_KEY=your-brain-api-key

# Redis
REDIS_URL=redis://default:password@host:6379/0

# Task Service
API_KEY=ae6e18cb408bc7128f23585casdlaelwlekoqdsldsa
ENVIRONMENT=production
DEBUG=false
```

---

## 9. Testing the Implementation

### Test 1: Submit Evaluation Task

```bash
curl -X POST https://tasks.ft.tc/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ae6e18cb408bc7128f23585casdlaelwlekoqdsldsa" \
  -d '{
    "project_id": "68df4dab400c86a6a8cf40c6",
    "task_type": "evaluate_department",
    "task_data": {
      "department_slug": "story",
      "department_number": 1,
      "gather_data": [
        {
          "content": "A young wizard discovers their magical powers on their 11th birthday and must save the world from an ancient evil.",
          "summary": "Main story premise",
          "context": "Fantasy adventure film"
        },
        {
          "content": "Three-act structure: Setup (discovery), Confrontation (training and challenges), Resolution (final battle)",
          "summary": "Story structure",
          "context": "Narrative framework"
        }
      ],
      "previous_evaluations": [],
      "threshold": 80
    },
    "priority": 1,
    "callback_url": "https://aladdin.ngrok.pro/api/webhooks/evaluation-complete",
    "metadata": {
      "user_id": "test-user-123",
      "department_id": "dept-story-001"
    }
  }'
```

**Expected Response**:
```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "queued",
  "project_id": "68df4dab400c86a6a8cf40c6",
  "estimated_duration": 300,
  "queue_position": 1,
  "created_at": "2025-01-15T10:30:00Z"
}
```

### Test 2: Check Task Status

```bash
curl -X GET https://tasks.ft.tc/api/v1/tasks/abc123-def456-ghi789/status \
  -H "X-API-Key: ae6e18cb408bc7128f23585casdlaelwlekoqdsldsa"
```

### Test 3: Verify Webhook Delivery

Check the Aladdin application logs for:
```
[Webhook] Received evaluation complete notification: { task_id, status, ... }
[Webhook] Found evaluation: { id, projectId, departmentId, ... }
[Webhook] Processing completed evaluation: { rating, department, ... }
[Webhook] Updated evaluation record successfully
```

---

## 10. Implementation Checklist

- [ ] Add `EVALUATE_DEPARTMENT` to `TaskType` enum
- [ ] Create `celery-redis/app/tasks/evaluation_tasks.py`
- [ ] Implement `EvaluateDepartmentTask` class
- [ ] Implement `_get_department_context()` method
- [ ] Implement `_build_evaluation_prompt()` method
- [ ] Implement `_call_ai_evaluator()` method with your AI service
- [ ] Register task in `celery_app.py`
- [ ] Add route handler in `api/tasks.py`
- [ ] Configure environment variables
- [ ] Test task submission
- [ ] Test task execution
- [ ] Verify webhook delivery
- [ ] Test error handling
- [ ] Test with multiple departments
- [ ] Verify brain service integration (if used)
- [ ] Add logging and monitoring
- [ ] Document any custom configuration

---

## 11. Department Evaluation Criteria

### Story Department (dept #1)
- Narrative structure completeness
- Character development depth
- Plot coherence and pacing
- Theme clarity
- Conflict establishment

### Character Department (dept #2)
- Character profile completeness
- Backstory depth
- Motivation clarity
- Relationship dynamics
- Character arc definition

### Production Department (dept #3)
- Resource planning
- Budget feasibility
- Timeline realism
- Technical requirements
- Location scouting

### Visual Department (dept #4)
- Visual style consistency
- Color palette definition
- Cinematography planning
- Shot composition
- Visual effects planning

*(Continue for all 12 departments as needed)*

---

## 12. Error Handling

### Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `AI service timeout` | AI call takes too long | Implement retry logic, increase timeout |
| `Invalid gather data` | Missing required fields | Validate input before processing |
| `Brain service unavailable` | Brain service down | Continue without brain context (optional) |
| `Insufficient content` | Not enough gather data | Return low rating with specific feedback |
| `Invalid department` | Unknown department slug | Validate against known departments |

### Fallback Behavior

If AI evaluation fails, return a fallback result:
```python
{
    "rating": 50,
    "summary": "Evaluation could not be completed due to service error",
    "issues": ["AI evaluation service unavailable"],
    "suggestions": ["Retry evaluation when service is available"],
    "iteration_count": 0,
    "confidence": 0.0
}
```

---

## 13. Performance Considerations

- **Expected Duration**: 30-120 seconds per evaluation
- **Token Usage**: 1000-5000 tokens per evaluation
- **Concurrent Evaluations**: Support 5-10 concurrent evaluations
- **Queue Priority**: High priority (1) for user-initiated evaluations
- **Retry Logic**: 3 retries with exponential backoff for AI calls
- **Timeout**: 300 seconds maximum per evaluation

---

## 14. Monitoring and Logging

### Key Metrics to Track

- Evaluation success rate
- Average processing time
- Token usage per evaluation
- Rating distribution
- Department-specific metrics
- Webhook delivery success rate

### Log Patterns

```python
logger.info("Starting department evaluation", project_id=..., department=...)
logger.info("Brain context retrieved", context_size=...)
logger.info("AI evaluation completed", rating=..., tokens=...)
logger.info("Department evaluation completed", result=..., time=...)
logger.error("AI evaluation failed", error=..., department=...)
```

---

## 15. Integration with Aladdin

### Flow Diagram

```
User clicks "Evaluate"
    ↓
Aladdin submits task to tasks.ft.tc
    ↓
Celery worker picks up task
    ↓
evaluate_department.execute_task() runs
    ↓
AI evaluates content
    ↓
Task completes
    ↓
Webhook sent to Aladdin
    ↓
Aladdin updates database
    ↓
UI shows results
```

### Aladdin Webhook Handler

The webhook handler at `https://aladdin.ngrok.pro/api/webhooks/evaluation-complete` expects:
- `task_id` to match evaluation record
- `result` object with all required fields
- `status` of "completed" or "failed"
- `metadata` with user_id and department_id

---

## 16. Next Steps After Implementation

1. **Test with real data** from Aladdin application
2. **Monitor performance** and adjust timeouts if needed
3. **Tune AI prompts** based on evaluation quality
4. **Add department-specific logic** if needed
5. **Implement caching** for similar evaluations
6. **Add rate limiting** if needed
7. **Document any custom configuration**
8. **Train team on monitoring and troubleshooting**

---

## 17. Support and Questions

For questions or issues during implementation:
- Check existing task implementations in `celery-redis/app/tasks/`
- Review webhook implementation in `base_task.py`
- Test with `test_prompt` task type first
- Check Celery worker logs for errors
- Verify Redis connection and queue status

---

**End of Implementation Guide**

