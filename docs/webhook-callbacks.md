# Webhook Callbacks

The Task Service supports webhook callbacks to notify external services when tasks complete (successfully or with failure).

## Overview

When submitting a task, you can provide a `callback_url` parameter. The Task Service will automatically POST to this URL when the task completes, regardless of success or failure.

## Features

- ✅ Automatic webhook delivery on task completion
- ✅ Retry logic with exponential backoff (3 retries by default)
- ✅ Standardized payload format
- ✅ Support for both success and failure scenarios
- ✅ Metadata passthrough for custom tracking
- ✅ Timeout handling (30 seconds default)

## Submitting a Task with Callback

### Request Example

```bash
curl -X POST http://localhost:8001/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "project_id": "detective_series_001",
    "task_type": "video_generation",
    "priority": 1,
    "callback_url": "https://your-app.com/api/webhooks/task-complete",
    "parameters": {
      "prompt": "Generate a detective scene",
      "duration": 30
    },
    "metadata": {
      "userId": "user-123",
      "testResultId": "result-456"
    }
  }'
```

### Key Parameters

- **callback_url** (optional): The URL to POST results to when the task completes
- **metadata** (optional): Custom metadata that will be included in the webhook payload

## Webhook Payload Format

### Success Payload

When a task completes successfully, the webhook receives:

```json
{
  "task_id": "abc123-def456-ghi789",
  "project_id": "detective_series_001",
  "status": "completed",
  "result": {
    "media_url": "https://media.ft.tc/detective_001/video_001.mp4",
    "payload_media_id": "64f1b2c3a8d9e0f1",
    "metadata": {
      "processing_time": 45.2,
      "tokens_used": 1250
    }
  },
  "processing_time": 315,
  "completed_at": "2025-01-15T10:35:30Z",
  "metadata": {
    "userId": "user-123",
    "testResultId": "result-456"
  }
}
```

### Failure Payload

When a task fails, the webhook receives:

```json
{
  "task_id": "abc123-def456-ghi789",
  "project_id": "detective_series_001",
  "status": "failed",
  "error": "Task execution failed: Invalid prompt format",
  "traceback": "Traceback (most recent call last):\n  File ...",
  "failed_at": "2025-01-15T10:35:30Z",
  "metadata": {
    "userId": "user-123",
    "testResultId": "result-456"
  }
}
```

## Implementing a Webhook Handler

### Node.js/Express Example

```javascript
const express = require('express');
const app = express();

app.post('/api/webhooks/task-complete', express.json(), async (req, res) => {
  const { task_id, status, result, error, project_id, metadata } = req.body;
  
  try {
    if (status === 'completed') {
      // Handle successful task completion
      console.log(`Task ${task_id} completed successfully`);
      
      // Update your database
      await db.tasks.update({
        where: { id: task_id },
        data: {
          status: 'completed',
          result: result,
          completedAt: new Date()
        }
      });
      
      // Notify user via WebSocket or other means
      if (metadata?.userId) {
        await notifyUser(metadata.userId, {
          type: 'task_completed',
          task_id,
          result
        });
      }
      
    } else if (status === 'failed') {
      // Handle task failure
      console.error(`Task ${task_id} failed:`, error);
      
      await db.tasks.update({
        where: { id: task_id },
        data: {
          status: 'failed',
          error: error,
          failedAt: new Date()
        }
      });
      
      // Notify user of failure
      if (metadata?.userId) {
        await notifyUser(metadata.userId, {
          type: 'task_failed',
          task_id,
          error
        });
      }
    }
    
    // Always respond with 200 to acknowledge receipt
    res.status(200).json({ received: true });
    
  } catch (error) {
    console.error('Webhook processing error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

app.listen(3010, () => {
  console.log('Webhook handler listening on port 3010');
});
```

### Python/FastAPI Example

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

app = FastAPI()

class WebhookPayload(BaseModel):
    task_id: str
    project_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    traceback: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@app.post("/api/webhooks/task-complete")
async def handle_task_webhook(payload: WebhookPayload):
    try:
        if payload.status == "completed":
            # Handle successful completion
            print(f"Task {payload.task_id} completed successfully")
            
            # Update database
            await update_task_status(
                task_id=payload.task_id,
                status="completed",
                result=payload.result
            )
            
            # Notify user
            if payload.metadata and "userId" in payload.metadata:
                await notify_user(
                    user_id=payload.metadata["userId"],
                    message={
                        "type": "task_completed",
                        "task_id": payload.task_id,
                        "result": payload.result
                    }
                )
        
        elif payload.status == "failed":
            # Handle failure
            print(f"Task {payload.task_id} failed: {payload.error}")
            
            await update_task_status(
                task_id=payload.task_id,
                status="failed",
                error=payload.error
            )
            
            if payload.metadata and "userId" in payload.metadata:
                await notify_user(
                    user_id=payload.metadata["userId"],
                    message={
                        "type": "task_failed",
                        "task_id": payload.task_id,
                        "error": payload.error
                    }
                )
        
        return {"received": True}
    
    except Exception as e:
        print(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

## Webhook Delivery Behavior

### Retry Logic

The Task Service implements automatic retry logic for webhook delivery:

1. **Initial attempt**: Immediate delivery after task completion
2. **Retry 1**: After 1 second (if initial fails)
3. **Retry 2**: After 2 seconds (if retry 1 fails)
4. **Retry 3**: After 4 seconds (if retry 2 fails)

Total retry attempts: 3 (exponential backoff)

### Success Criteria

A webhook delivery is considered successful if the receiving endpoint returns:
- HTTP 200 (OK)
- HTTP 201 (Created)
- HTTP 202 (Accepted)
- HTTP 204 (No Content)

Any other status code will trigger a retry.

### Timeout

Each webhook request has a 30-second timeout. If your endpoint doesn't respond within this time, the request will be retried.

### Failure Handling

If all retry attempts fail:
- The task result is still stored in the brain service
- An error is logged in the Task Service logs
- You can still query the task status via the `/api/v1/tasks/{task_id}/status` endpoint

## Security Considerations

### Webhook Authentication

Currently, webhooks are sent without authentication headers. For production use, consider:

1. **IP Whitelisting**: Only accept webhooks from known Task Service IPs
2. **Shared Secret**: Implement HMAC signature verification (future enhancement)
3. **HTTPS Only**: Always use HTTPS endpoints for webhook URLs
4. **Request Validation**: Validate the webhook payload structure

### Example: IP Whitelisting (Express)

```javascript
const ALLOWED_IPS = ['10.0.0.1', '10.0.0.2']; // Task Service IPs

app.post('/api/webhooks/task-complete', (req, res, next) => {
  const clientIP = req.ip || req.connection.remoteAddress;
  
  if (!ALLOWED_IPS.includes(clientIP)) {
    return res.status(403).json({ error: 'Forbidden' });
  }
  
  next();
}, handleWebhook);
```

## Testing Webhooks

### Using ngrok for Local Development

```bash
# Start ngrok to expose your local server
ngrok http 3010

# Use the ngrok URL as your callback_url
# Example: https://abc123.ngrok.io/api/webhooks/task-complete
```

### Mock Webhook Server

For testing, you can use a simple mock server:

```javascript
const express = require('express');
const app = express();

app.post('/api/webhooks/task-complete', express.json(), (req, res) => {
  console.log('Received webhook:', JSON.stringify(req.body, null, 2));
  res.status(200).json({ received: true });
});

app.listen(3010, () => {
  console.log('Mock webhook server running on port 3010');
});
```

## Monitoring and Debugging

### Checking Webhook Logs

Webhook delivery attempts are logged in the Task Service logs:

```bash
# View webhook logs
docker logs celery-redis-api-1 | grep "webhook"

# Successful delivery
# INFO: Webhook sent successfully callback_url=https://... status_code=200

# Failed delivery
# WARNING: Webhook request failed callback_url=https://... error=...
```

### Common Issues

1. **Webhook not received**: Check that your callback_url is accessible from the Task Service
2. **Timeout errors**: Ensure your webhook handler responds quickly (< 30 seconds)
3. **Retry exhaustion**: Check your endpoint logs for errors

## Best Practices

1. **Respond Quickly**: Acknowledge webhook receipt immediately (return 200), then process asynchronously
2. **Idempotency**: Handle duplicate webhook deliveries gracefully (use task_id for deduplication)
3. **Error Handling**: Always return appropriate HTTP status codes
4. **Logging**: Log all webhook receipts for debugging
5. **Monitoring**: Set up alerts for webhook delivery failures

## Future Enhancements

Planned improvements for webhook functionality:

- [ ] HMAC signature verification for authentication
- [ ] Configurable retry policy
- [ ] Webhook delivery status tracking
- [ ] Dead letter queue for failed webhooks
- [ ] Webhook replay functionality

