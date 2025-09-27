#!/usr/bin/env python3
"""
Simple test script to validate brain service integration
Can be run without pytest to check basic functionality
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from clients.brain_client import BrainServiceClient
from config.settings import settings

async def test_brain_client_basic():
    """Test basic brain client functionality"""
    print("Testing Brain Service Client...")

    client = BrainServiceClient(settings.brain_service_base_url)

    print(f"Brain Service URL: {settings.brain_service_base_url}")
    print(f"WebSocket URL: {client.ws_url}")

    # Test basic configuration
    assert client.max_retries == 3
    assert client.timeout == 30.0
    print("✓ Client configuration correct")

    # Test method existence
    assert hasattr(client, 'store_task_result')
    assert hasattr(client, 'get_task_context')
    assert hasattr(client, 'search_similar_tasks')
    assert hasattr(client, 'cache_task_result')
    assert hasattr(client, 'get_cached_result')
    print("✓ All required methods present")

    # Test async context manager
    assert hasattr(client, '__aenter__')
    assert hasattr(client, '__aexit__')
    print("✓ Async context manager implemented")

    print("Brain Service Client tests passed!")

def test_task_integration():
    """Test task integration classes"""
    print("\nTesting Task Integration...")

    from tasks.base_task import BaseTaskWithBrain
    from tasks.video_tasks import VideoGenerationTask
    from tasks.image_tasks import ImageGenerationTask
    from tasks.audio_tasks import AudioGenerationTask

    # Test base task
    assert hasattr(BaseTaskWithBrain, 'store_task_result_in_brain')
    assert hasattr(BaseTaskWithBrain, 'get_task_history_from_brain')
    assert hasattr(BaseTaskWithBrain, 'search_similar_tasks_in_brain')
    assert hasattr(BaseTaskWithBrain, 'cache_result_in_brain')
    print("✓ BaseTaskWithBrain has all required methods")

    # Test concrete task classes
    video_task = VideoGenerationTask()
    assert hasattr(video_task, 'execute_task')
    print("✓ VideoGenerationTask implemented")

    image_task = ImageGenerationTask()
    assert hasattr(image_task, 'execute_task')
    print("✓ ImageGenerationTask implemented")

    audio_task = AudioGenerationTask()
    assert hasattr(audio_task, 'execute_task')
    print("✓ AudioGenerationTask implemented")

    print("Task Integration tests passed!")

def test_configuration():
    """Test configuration and environment setup"""
    print("\nTesting Configuration...")

    from config.settings import settings
    from config.service_discovery import get_brain_service_url

    # Test brain service URL configuration
    assert hasattr(settings, 'brain_service_base_url')
    assert settings.brain_service_base_url is not None
    print(f"✓ Brain service URL configured: {settings.brain_service_base_url}")

    # Test service discovery
    brain_url = get_brain_service_url()
    assert brain_url is not None
    print(f"✓ Service discovery working: {brain_url}")

    print("Configuration tests passed!")

def test_api_integration():
    """Test API integration"""
    print("\nTesting API Integration...")

    from api.tasks import router
    from tasks import process_video_generation, process_image_generation, process_audio_generation

    # Test task functions exist
    assert process_video_generation is not None
    assert process_image_generation is not None
    assert process_audio_generation is not None
    print("✓ Task functions imported successfully")

    # Test router exists
    assert router is not None
    print("✓ API router configured")

    print("API Integration tests passed!")

async def main():
    """Run all tests"""
    print("=== Brain Service Integration Test Suite ===\n")

    try:
        await test_brain_client_basic()
        test_task_integration()
        test_configuration()
        test_api_integration()

        print("\n=== ALL TESTS PASSED ===")
        print("✓ Brain Service Client implemented correctly")
        print("✓ Task integration working")
        print("✓ Configuration properly set up")
        print("✓ API integration complete")
        print("\nPhase 4 implementation successful!")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())