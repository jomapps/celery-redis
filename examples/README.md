# Task Service Examples

This directory contains example scripts demonstrating how to use the Task Service features.

## Available Examples

### 1. Webhook Callback Example (`webhook_example.py`)

Demonstrates how to use webhook callbacks to receive notifications when tasks complete.

**Features:**
- Simple webhook receiver implementation
- Task submission with callback URL
- Webhook payload handling
- Success and failure scenarios

**Usage:**

```bash
# Make sure the Task Service is running
docker-compose up -d

# Run the example
python3 examples/webhook_example.py
```

**What it does:**
1. Starts a local webhook receiver on port 8080
2. Submits a test task with callback URL
3. Waits for and displays the webhook callback
4. Shows the complete payload structure

**Requirements:**
- Task Service running on http://localhost:8001
- Redis and Celery workers running
- Python packages: `aiohttp`, `httpx`

**Install dependencies:**
```bash
pip install aiohttp httpx
```

## Testing with ngrok

For testing webhooks with external services, you can use ngrok:

```bash
# Start ngrok
ngrok http 8080

# Use the ngrok URL in your task submission
# Example: https://abc123.ngrok.io/webhook
```

## Example Output

When you run the webhook example, you'll see output like:

```
============================================================
🚀 WEBHOOK CALLBACK EXAMPLE
============================================================

🎯 Webhook receiver started on http://localhost:8080/webhook

============================================================
📤 SUBMITTING TASK
============================================================
Project ID: webhook_test_project
Task Type: video_generation
Callback URL: http://localhost:8080/webhook
...

✅ Task submitted successfully!
Task ID: abc123-def456-ghi789

⏳ Waiting for webhook callback...

============================================================
📨 WEBHOOK RECEIVED
============================================================
Time: 2025-01-15T10:35:30
Task ID: abc123-def456-ghi789
Status: completed
Project ID: webhook_test_project

✅ Task Completed Successfully!
Result: {
  "media_url": "https://media.ft.tc/video.mp4",
  "payload_media_id": "64f1b2c3a8d9e0f1"
}
Processing Time: 315s
============================================================
```

## Creating Your Own Examples

To create a new example:

1. Create a new Python file in this directory
2. Add clear documentation at the top
3. Include usage instructions
4. Update this README with the new example

## Common Issues

### Webhook not received

**Possible causes:**
- Task Service not running
- Celery workers not running
- Callback URL not accessible
- Task still processing

**Solutions:**
- Check `docker-compose ps` to verify services are running
- Check logs: `docker logs celery-redis-api-1`
- Verify webhook receiver is accessible
- Wait longer for task completion

### Connection refused

**Possible causes:**
- Task Service not running on expected port
- Wrong API key

**Solutions:**
- Verify Task Service is running: `curl http://localhost:8001/health`
- Check API key in environment variables
- Update the example script with correct URL/key

## Additional Resources

- [Webhook Callbacks Documentation](../docs/webhook-callbacks.md)
- [How to Use Celery Redis](../docs/how-to-use-celery-redis.md)
- [System Integration Guide](../docs/system-integration.md)

