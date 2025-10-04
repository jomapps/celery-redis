#!/usr/bin/env python3
"""
Example: Using Webhook Callbacks with the Task Service

This example demonstrates how to:
1. Start a simple webhook receiver
2. Submit a task with a callback URL
3. Receive and process the webhook callback

Usage:
    python3 examples/webhook_example.py
"""

import asyncio
import json
from aiohttp import web
import httpx
from datetime import datetime


# Webhook receiver
class WebhookReceiver:
    """Simple webhook receiver for testing"""
    
    def __init__(self, port=8080):
        self.port = port
        self.received_webhooks = []
        self.app = web.Application()
        self.app.router.add_post('/webhook', self.handle_webhook)
    
    async def handle_webhook(self, request):
        """Handle incoming webhook"""
        try:
            payload = await request.json()
            
            print("\n" + "="*60)
            print("📨 WEBHOOK RECEIVED")
            print("="*60)
            print(f"Time: {datetime.now().isoformat()}")
            print(f"Task ID: {payload.get('task_id')}")
            print(f"Status: {payload.get('status')}")
            print(f"Project ID: {payload.get('project_id')}")
            
            if payload.get('status') == 'completed':
                print("\n✅ Task Completed Successfully!")
                print(f"Result: {json.dumps(payload.get('result'), indent=2)}")
                if 'processing_time' in payload:
                    print(f"Processing Time: {payload['processing_time']}s")
            
            elif payload.get('status') == 'failed':
                print("\n❌ Task Failed!")
                print(f"Error: {payload.get('error')}")
                if 'traceback' in payload:
                    print(f"Traceback: {payload.get('traceback')[:200]}...")
            
            if 'metadata' in payload:
                print(f"\nMetadata: {json.dumps(payload.get('metadata'), indent=2)}")
            
            print("="*60 + "\n")
            
            # Store for later inspection
            self.received_webhooks.append({
                'timestamp': datetime.now().isoformat(),
                'payload': payload
            })
            
            return web.json_response({'received': True})
            
        except Exception as e:
            print(f"❌ Error processing webhook: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def start(self):
        """Start the webhook receiver"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()
        print(f"🎯 Webhook receiver started on http://localhost:{self.port}/webhook")
        return runner


# Task submitter
class TaskSubmitter:
    """Submit tasks to the Task Service"""
    
    def __init__(self, task_service_url="http://localhost:8001", api_key="test-api-key"):
        self.task_service_url = task_service_url
        self.api_key = api_key
    
    async def submit_task(self, project_id, task_type, callback_url, parameters=None, metadata=None):
        """Submit a task with webhook callback"""
        
        payload = {
            "project_id": project_id,
            "task_type": task_type,
            "priority": 1,
            "callback_url": callback_url,
            "task_data": parameters or {},
            "metadata": metadata or {}
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
        
        print("\n" + "="*60)
        print("📤 SUBMITTING TASK")
        print("="*60)
        print(f"Project ID: {project_id}")
        print(f"Task Type: {task_type}")
        print(f"Callback URL: {callback_url}")
        print(f"Parameters: {json.dumps(parameters, indent=2)}")
        print(f"Metadata: {json.dumps(metadata, indent=2)}")
        print("="*60 + "\n")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.task_service_url}/api/v1/tasks/submit",
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code in (200, 201):
                    result = response.json()
                    print(f"✅ Task submitted successfully!")
                    print(f"Task ID: {result.get('task_id')}")
                    print(f"Status: {result.get('status')}")
                    return result
                else:
                    print(f"❌ Task submission failed: {response.status_code}")
                    print(f"Response: {response.text}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error submitting task: {e}")
            return None


async def main():
    """Main example function"""
    
    print("\n" + "="*60)
    print("🚀 WEBHOOK CALLBACK EXAMPLE")
    print("="*60)
    print("\nThis example demonstrates webhook callbacks with the Task Service.")
    print("It will:")
    print("1. Start a local webhook receiver on port 8080")
    print("2. Submit a test task with a callback URL")
    print("3. Wait for the webhook callback")
    print("\nMake sure the Task Service is running on http://localhost:8001")
    print("="*60 + "\n")
    
    # Start webhook receiver
    receiver = WebhookReceiver(port=8080)
    runner = await receiver.start()
    
    # Wait a moment for the server to be ready
    await asyncio.sleep(1)
    
    # Submit a task
    submitter = TaskSubmitter()
    
    # Example 1: Video generation task
    task_result = await submitter.submit_task(
        project_id="webhook_test_project",
        task_type="video_generation",
        callback_url="http://localhost:8080/webhook",
        parameters={
            "scene_data": {
                "prompt": "A detective investigating a crime scene",
                "duration": 30
            },
            "video_params": {
                "resolution": "1920x1080",
                "fps": 30
            }
        },
        metadata={
            "userId": "test-user-123",
            "testResultId": "test-result-456",
            "example": "webhook_callback_demo"
        }
    )
    
    if task_result:
        print("\n⏳ Waiting for webhook callback...")
        print("(This may take a while depending on task processing time)")
        print("Press Ctrl+C to stop\n")
        
        # Wait for webhook (or timeout after 5 minutes)
        timeout = 300  # 5 minutes
        start_time = asyncio.get_event_loop().time()
        
        try:
            while True:
                await asyncio.sleep(1)
                
                # Check if we received any webhooks
                if receiver.received_webhooks:
                    print("\n✅ Webhook received! Check the output above.")
                    break
                
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    print(f"\n⏰ Timeout after {timeout} seconds")
                    print("No webhook received. This could mean:")
                    print("- The task is still processing")
                    print("- The Task Service is not running")
                    print("- The callback URL is not accessible")
                    break
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
    
    else:
        print("\n❌ Failed to submit task. Check that:")
        print("- The Task Service is running on http://localhost:8001")
        print("- The API key is correct")
        print("- Redis and Celery workers are running")
    
    # Cleanup
    print("\n🛑 Shutting down webhook receiver...")
    await runner.cleanup()
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    print(f"Total webhooks received: {len(receiver.received_webhooks)}")
    
    if receiver.received_webhooks:
        print("\nWebhook Details:")
        for i, webhook in enumerate(receiver.received_webhooks, 1):
            print(f"\n{i}. Received at: {webhook['timestamp']}")
            print(f"   Task ID: {webhook['payload'].get('task_id')}")
            print(f"   Status: {webhook['payload'].get('status')}")
    
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")

