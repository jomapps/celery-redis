# Department Evaluation Task

## Overview

The `evaluate_department` task provides AI-powered evaluation of movie production departments for the Aladdin Project Readiness system. It analyzes gathered content, provides quality ratings, identifies issues, and suggests improvements.

## Task Type

```
evaluate_department
```

## Purpose

Evaluate movie production departments (Story, Character, Production, Visual, etc.) based on gathered content and provide:
- Quality rating (0-100)
- Pass/fail result based on threshold
- Comprehensive evaluation summary
- Specific issues identified
- Actionable improvement suggestions

## Integration

- **Source**: Aladdin application (Project Readiness system)
- **Webhook**: `https://aladdin.ngrok.pro/api/webhooks/evaluation-complete`
- **Queue**: `cpu_intensive`
- **Expected Duration**: 30-120 seconds

## Request Format

### Submit Evaluation Task

**POST** `/api/v1/tasks/submit`

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
| `task_data.department_slug` | string | Yes | Department name (e.g., "story", "character") |
| `task_data.department_number` | integer | Yes | Sequential department number (1-12) |
| `task_data.gather_data` | array | Yes | Array of gathered content items |
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

## Response Format

### Success Response

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

## Webhook Payload

### Success Webhook

```json
{
  "task_id": "abc123-def456-ghi789",
  "project_id": "68df4dab400c86a6a8cf40c6",
  "status": "completed",
  "result": {
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
    "iteration_count": 1,
    "processing_time": 45.2,
    "metadata": {
      "model": "mock-evaluator-v1",
      "tokens_used": 1500,
      "confidence_score": 0.85
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

### Failure Webhook

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

## Result Fields

| Field | Type | Description |
|-------|------|-------------|
| `department` | string | Department slug (echo from input) |
| `rating` | integer | Quality score 0-100 |
| `evaluation_result` | string | "pass" if rating >= threshold, else "fail" |
| `evaluation_summary` | string | 2-3 sentence high-level assessment |
| `issues` | array[string] | 3-5 specific problems identified |
| `suggestions` | array[string] | 3-5 actionable improvement recommendations |
| `iteration_count` | integer | Number of AI refinement iterations |
| `processing_time` | number | Processing time in seconds |
| `metadata.model` | string | AI model used |
| `metadata.tokens_used` | integer | Total tokens consumed |
| `metadata.confidence_score` | number | Confidence metric 0.0-1.0 |

## Example Usage

### cURL Example

```bash
curl -X POST https://tasks.ft.tc/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
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
        }
      ],
      "threshold": 80
    },
    "callback_url": "https://aladdin.ngrok.pro/api/webhooks/evaluation-complete",
    "metadata": {
      "user_id": "test-user-123"
    }
  }'
```

### JavaScript/TypeScript Example

```typescript
const response = await fetch('https://tasks.ft.tc/api/v1/tasks/submit', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify({
    project_id: '68df4dab400c86a6a8cf40c6',
    task_type: 'evaluate_department',
    task_data: {
      department_slug: 'story',
      department_number: 1,
      gather_data: [
        {
          content: 'Story content...',
          summary: 'Story summary',
          context: 'Story context'
        }
      ],
      threshold: 80
    },
    callback_url: 'https://aladdin.ngrok.pro/api/webhooks/evaluation-complete',
    metadata: {
      user_id: 'user123',
      department_id: 'dept-story-001'
    }
  })
});

const result = await response.json();
console.log('Task submitted:', result.task_id);
```

## Department Types

The evaluation system supports these department types:

1. **Story** (dept #1) - Narrative structure, plot, themes
2. **Character** (dept #2) - Character profiles, arcs, relationships
3. **Production** (dept #3) - Resources, budget, timeline
4. **Visual** (dept #4) - Visual style, cinematography, effects
5. **Audio** (dept #5) - Sound design, music, dialogue
6. **Editing** (dept #6) - Pacing, transitions, continuity
7. **Marketing** (dept #7) - Promotion, distribution, audience
8. **Legal** (dept #8) - Rights, contracts, compliance
9. **Technical** (dept #9) - Equipment, software, infrastructure
10. **Post-Production** (dept #10) - Color grading, VFX, final mix
11. **Distribution** (dept #11) - Release strategy, platforms
12. **Archive** (dept #12) - Asset management, preservation

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Insufficient data` | No gather_data provided | Provide at least 1 content item |
| `Invalid department` | Unknown department_slug | Use valid department name |
| `AI service timeout` | Evaluation takes too long | Retry with smaller content |
| `Invalid threshold` | Threshold out of range | Use value between 0-100 |

### Fallback Behavior

If AI evaluation fails, the system returns a fallback result with:
- Rating: 50
- Summary: Error description
- Issues: Service unavailability notice
- Suggestions: Retry recommendation

## Performance

- **Expected Duration**: 30-120 seconds
- **Token Usage**: 1000-5000 tokens per evaluation
- **Concurrent Limit**: 5-10 evaluations
- **Timeout**: 300 seconds maximum

## Monitoring

### Key Metrics

- Evaluation success rate
- Average processing time
- Token usage per evaluation
- Rating distribution
- Department-specific metrics

### Log Patterns

```
INFO: Starting department evaluation project_id=... department=...
INFO: Department evaluation completed rating=... result=... time=...
ERROR: AI evaluation failed error=... department=...
```

## Testing

Run the test suite:

```bash
python3 -m pytest tests/test_evaluation_tasks.py -v
```

Expected: 9 tests passing

## Notes

- The current implementation uses a mock AI evaluator for testing
- To integrate with real AI (OpenAI, Anthropic, etc.), update the `_call_ai_evaluator` method in `app/tasks/evaluation_tasks.py`
- Webhook delivery uses the existing webhook infrastructure with retry logic
- Brain service integration provides context from similar evaluations

## Support

For issues or questions:
- Check task logs: `docker logs celery-redis-worker-1`
- Verify webhook delivery in Aladdin logs
- Test with smaller gather_data first
- Contact support with task_id for debugging

