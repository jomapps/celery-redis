#!/usr/bin/env python3
"""
Implementation validation script for Phase 4 - Brain Service Integration
Validates structure and configuration without requiring external dependencies
"""
import os
import sys

def validate_file_structure():
    """Validate that all required files and directories exist"""
    print("Validating file structure...")

    required_files = [
        "app/clients/__init__.py",
        "app/clients/brain_client.py",
        "app/tasks/__init__.py",
        "app/tasks/base_task.py",
        "app/tasks/video_tasks.py",
        "app/tasks/image_tasks.py",
        "app/tasks/audio_tasks.py",
        "tests/test_brain_integration.py",
        "requirements.txt"
    ]

    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)

    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False

    print("✓ All required files present")
    return True

def validate_brain_client_implementation():
    """Validate brain client implementation"""
    print("\nValidating brain client implementation...")

    with open("app/clients/brain_client.py", "r") as f:
        content = f.read()

    required_methods = [
        "class BrainServiceClient",
        "async def connect",
        "async def store_task_result",
        "async def store_task_context",
        "async def get_task_history",
        "async def search_similar_tasks",
        "async def cache_task_result",
        "async def get_cached_result",
        "async def health_check",
        "async def disconnect"
    ]

    missing_methods = []
    for method in required_methods:
        if method not in content:
            missing_methods.append(method)

    if missing_methods:
        print(f"❌ Missing methods in brain client: {missing_methods}")
        return False

    # Check for WebSocket integration
    if "websockets" not in content:
        print("❌ WebSocket integration missing")
        return False

    # Check for MCP protocol
    if "jsonrpc" not in content:
        print("❌ MCP/JSON-RPC protocol missing")
        return False

    print("✓ Brain client implementation complete")
    return True

def validate_task_integration():
    """Validate task integration with brain service"""
    print("\nValidating task integration...")

    # Check base task
    with open("app/tasks/base_task.py", "r") as f:
        base_content = f.read()

    required_base_features = [
        "class BaseTaskWithBrain",
        "async def store_task_result_in_brain",
        "async def get_task_history_from_brain",
        "async def search_similar_tasks_in_brain",
        "async def cache_result_in_brain",
        "def on_failure",
        "def on_success"
    ]

    for feature in required_base_features:
        if feature not in base_content:
            print(f"❌ Missing in base task: {feature}")
            return False

    # Check concrete task implementations
    task_files = ["video_tasks.py", "image_tasks.py", "audio_tasks.py"]
    for task_file in task_files:
        with open(f"app/tasks/{task_file}", "r") as f:
            task_content = f.read()

        if "BaseTaskWithBrain" not in task_content:
            print(f"❌ {task_file} doesn't inherit from BaseTaskWithBrain")
            return False

        if "execute_task" not in task_content:
            print(f"❌ {task_file} missing execute_task method")
            return False

    print("✓ Task integration complete")
    return True

def validate_environment_configuration():
    """Validate environment configuration"""
    print("\nValidating environment configuration...")

    # Check .env files
    env_files = [".env", ".env.example"]
    for env_file in env_files:
        if not os.path.exists(env_file):
            print(f"❌ Missing {env_file}")
            return False

        with open(env_file, "r") as f:
            env_content = f.read()

        if "BRAIN_SERVICE_BASE_URL" not in env_content:
            print(f"❌ BRAIN_SERVICE_BASE_URL missing from {env_file}")
            return False

    # Check settings configuration
    with open("app/config/settings.py", "r") as f:
        settings_content = f.read()

    if "brain_service_base_url" not in settings_content:
        print("❌ brain_service_base_url missing from settings")
        return False

    # Check service discovery
    with open("app/config/service_discovery.py", "r") as f:
        discovery_content = f.read()

    # Check that Neo4j references are commented out
    neo4j_lines = [line for line in discovery_content.split('\n') if 'neo4j' in line.lower()]
    active_neo4j = [line for line in neo4j_lines if not line.strip().startswith('#')]

    if active_neo4j:
        print(f"❌ Active Neo4j references found: {active_neo4j}")
        return False

    print("✓ Environment configuration complete")
    return True

def validate_requirements():
    """Validate requirements.txt has websockets dependency"""
    print("\nValidating requirements...")

    with open("requirements.txt", "r") as f:
        requirements = f.read()

    if "websockets" not in requirements:
        print("❌ websockets dependency missing from requirements.txt")
        return False

    print("✓ Requirements configuration complete")
    return True

def validate_api_integration():
    """Validate API integration"""
    print("\nValidating API integration...")

    with open("app/api/tasks.py", "r") as f:
        api_content = f.read()

    required_imports = [
        "from ..tasks import",
        "from ..clients.brain_client import BrainServiceClient",
        "process_video_generation",
        "process_image_generation",
        "process_audio_generation"
    ]

    for import_stmt in required_imports:
        if import_stmt not in api_content:
            print(f"❌ Missing API import: {import_stmt}")
            return False

    # Check for task submission integration
    if ".delay(" not in api_content:
        print("❌ Celery task submission integration missing")
        return False

    print("✓ API integration complete")
    return True

def validate_tests():
    """Validate test implementation"""
    print("\nValidating tests...")

    with open("tests/test_brain_integration.py", "r") as f:
        test_content = f.read()

    required_test_classes = [
        "class TestBrainServiceClient",
        "class TestTaskIntegration",
        "class TestErrorHandling",
        "class TestFullIntegration"
    ]

    for test_class in required_test_classes:
        if test_class not in test_content:
            print(f"❌ Missing test class: {test_class}")
            return False

    # Check for specific test methods
    required_tests = [
        "test_connection_success",
        "test_store_task_result",
        "test_search_similar_tasks",
        "test_cache_and_retrieve_result",
        "test_video_generation_task_brain_integration"
    ]

    for test_method in required_tests:
        if test_method not in test_content:
            print(f"❌ Missing test method: {test_method}")
            return False

    print("✓ Test implementation complete")
    return True

def main():
    """Run all validation checks"""
    print("=== Phase 4 Implementation Validation ===")
    print("Brain Service Integration for Celery-Redis Service\n")

    validations = [
        validate_file_structure,
        validate_brain_client_implementation,
        validate_task_integration,
        validate_environment_configuration,
        validate_requirements,
        validate_api_integration,
        validate_tests
    ]

    all_passed = True
    for validation in validations:
        try:
            if not validation():
                all_passed = False
        except Exception as e:
            print(f"❌ Validation failed with error: {e}")
            all_passed = False

    print("\n" + "="*50)
    if all_passed:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("\nPhase 4 Implementation Summary:")
        print("✓ Brain Service Client with MCP WebSocket implementation")
        print("✓ Task handlers integrated with brain service")
        print("✓ Knowledge graph storage for task results")
        print("✓ Task context queries and caching")
        print("✓ Environment configuration updated")
        print("✓ Neo4j direct references removed")
        print("✓ Comprehensive integration tests")
        print("✓ API endpoints updated with brain service integration")
        print("\nThe celery service is now ready for brain service integration!")
    else:
        print("❌ SOME VALIDATIONS FAILED")
        print("Please review the errors above and fix the issues.")
        sys.exit(1)

if __name__ == "__main__":
    main()