#!/usr/bin/env python3
"""
Example: Testing evaluate_department task

This script demonstrates how to submit an evaluation task
and verify the response format.

Usage:
    python3 examples/test_evaluate_department.py
"""

import json
import httpx
import asyncio
from datetime import datetime


async def test_evaluate_department():
    """Test the evaluate_department task submission"""
    
    print("\n" + "="*60)
    print("🧪 TESTING evaluate_department TASK")
    print("="*60 + "\n")
    
    # Task Service configuration
    task_service_url = "http://localhost:8001"
    api_key = "test-api-key"  # Replace with actual API key
    
    # Prepare test data
    payload = {
        "project_id": "68df4dab400c86a6a8cf40c6",
        "task_type": "evaluate_department",
        "task_data": {
            "department_slug": "story",
            "department_number": 1,
            "gather_data": [
                {
                    "content": "A young detective arrives in a small coastal town to investigate a series of mysterious disappearances. As she digs deeper, she uncovers a conspiracy involving the town's founding families and a dark secret buried for generations.",
                    "summary": "Main story premise - mystery thriller",
                    "context": "Genre: Mystery/Thriller, Target audience: Adults 25-45"
                },
                {
                    "content": "Three-act structure: Act 1 - Detective arrives, first disappearance occurs (30 min). Act 2 - Investigation reveals patterns, personal stakes emerge (60 min). Act 3 - Confrontation with antagonist, resolution (30 min).",
                    "summary": "Story structure breakdown",
                    "context": "Total runtime: 120 minutes"
                },
                {
                    "content": "Protagonist: Detective Sarah Chen - 35, experienced investigator, intuitive, haunted by a past case. Antagonist: Mayor Thomas Blackwood - 55, charismatic, ruthless, protecting family legacy at any cost.",
                    "summary": "Main character profiles",
                    "context": "Character-driven narrative with strong antagonist"
                }
            ],
            "previous_evaluations": [],
            "threshold": 80
        },
        "priority": 1,
        "callback_url": "https://aladdin.ngrok.pro/api/webhooks/evaluation-complete",
        "metadata": {
            "user_id": "test-user-123",
            "department_id": "dept-story-001",
            "test_run": True
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }
    
    print("📤 Submitting evaluation task...")
    print(f"Project ID: {payload['project_id']}")
    print(f"Department: {payload['task_data']['department_slug']}")
    print(f"Gather items: {len(payload['task_data']['gather_data'])}")
    print(f"Threshold: {payload['task_data']['threshold']}")
    print()
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{task_service_url}/api/v1/tasks/submit",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code in (200, 201):
                result = response.json()
                
                print("✅ Task submitted successfully!")
                print()
                print("Response:")
                print(json.dumps(result, indent=2))
                print()
                
                # Verify response structure
                print("🔍 Verifying response structure...")
                required_fields = ["task_id", "status", "project_id"]
                
                for field in required_fields:
                    if field in result:
                        print(f"  ✅ {field}: {result[field]}")
                    else:
                        print(f"  ❌ Missing field: {field}")
                
                print()
                print("📋 Task Details:")
                print(f"  Task ID: {result.get('task_id')}")
                print(f"  Status: {result.get('status')}")
                print(f"  Queue Position: {result.get('queue_position', 'N/A')}")
                print(f"  Estimated Duration: {result.get('estimated_duration', 'N/A')}s")
                print()
                
                print("💡 Next Steps:")
                print(f"  1. Check task status: GET /api/v1/tasks/{result.get('task_id')}/status")
                print(f"  2. Monitor webhook at: {payload['callback_url']}")
                print(f"  3. View logs: docker logs celery-redis-worker-1 | grep {result.get('task_id')}")
                print()
                
                return result
                
            else:
                print(f"❌ Task submission failed: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
    except httpx.ConnectError:
        print("❌ Connection Error: Could not connect to Task Service")
        print(f"   Make sure the service is running on {task_service_url}")
        print("   Run: docker-compose up -d")
        return None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


async def check_task_status(task_id: str):
    """Check the status of a submitted task"""
    
    task_service_url = "http://localhost:8001"
    api_key = "test-api-key"
    
    print("\n" + "="*60)
    print(f"🔍 CHECKING TASK STATUS: {task_id}")
    print("="*60 + "\n")
    
    headers = {"X-API-Key": api_key}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{task_service_url}/api/v1/tasks/{task_id}/status",
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                
                print("Task Status:")
                print(json.dumps(result, indent=2))
                print()
                
                status = result.get('status')
                if status == 'completed':
                    print("✅ Task completed successfully!")
                    
                    if 'result' in result:
                        eval_result = result['result']
                        print()
                        print("Evaluation Result:")
                        print(f"  Department: {eval_result.get('department')}")
                        print(f"  Rating: {eval_result.get('rating')}/100")
                        print(f"  Result: {eval_result.get('evaluation_result')}")
                        print(f"  Summary: {eval_result.get('evaluation_summary')}")
                        print()
                        print(f"  Issues ({len(eval_result.get('issues', []))}):")
                        for i, issue in enumerate(eval_result.get('issues', []), 1):
                            print(f"    {i}. {issue}")
                        print()
                        print(f"  Suggestions ({len(eval_result.get('suggestions', []))}):")
                        for i, suggestion in enumerate(eval_result.get('suggestions', []), 1):
                            print(f"    {i}. {suggestion}")
                        
                elif status == 'failed':
                    print("❌ Task failed")
                    print(f"Error: {result.get('error')}")
                    
                elif status in ['queued', 'processing']:
                    print(f"⏳ Task is {status}...")
                    
                return result
                
            else:
                print(f"❌ Failed to get status: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


async def main():
    """Main test function"""
    
    print("\n" + "="*60)
    print("🚀 evaluate_department TASK TEST SUITE")
    print("="*60)
    print()
    print("This script will:")
    print("1. Submit an evaluate_department task")
    print("2. Verify the response structure")
    print("3. Optionally check task status")
    print()
    print("Make sure the Task Service is running:")
    print("  docker-compose up -d")
    print()
    print("="*60 + "\n")
    
    # Submit task
    result = await test_evaluate_department()
    
    if result and result.get('task_id'):
        print("="*60)
        print()
        
        # Ask if user wants to check status
        print("Would you like to check the task status? (y/n)")
        print("Note: The task may take 30-120 seconds to complete")
        print()
        
        # For automated testing, skip the input
        # Uncomment the following lines for interactive mode:
        # choice = input("> ").strip().lower()
        # if choice == 'y':
        #     await asyncio.sleep(5)  # Wait a bit
        #     await check_task_status(result['task_id'])
        
        print("✅ Test completed successfully!")
        print()
        print("To check task status later, run:")
        print(f"  curl -H 'X-API-Key: test-api-key' http://localhost:8001/api/v1/tasks/{result['task_id']}/status")
        
    else:
        print("❌ Test failed - could not submit task")
    
    print()
    print("="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print()
    
    if result:
        print("✅ Task submission: SUCCESS")
        print(f"✅ Task ID: {result.get('task_id')}")
        print(f"✅ Status: {result.get('status')}")
    else:
        print("❌ Task submission: FAILED")
        print()
        print("Troubleshooting:")
        print("1. Check if Task Service is running: docker-compose ps")
        print("2. Check service health: curl http://localhost:8001/api/v1/health")
        print("3. Check logs: docker logs celery-redis-api-1")
    
    print()
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user")

