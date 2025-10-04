"""
Tests for automated gather creation task
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestAutomatedGatherCreation:
    """Test automated gather creation task"""

    def test_task_is_registered(self):
        """Test that task is properly registered with Celery"""
        from app.tasks.automated_gather_tasks import automated_gather_creation

        # Verify task exists
        assert automated_gather_creation is not None
        assert hasattr(automated_gather_creation, 'name')
        assert automated_gather_creation.name == 'automated_gather_creation'

    def test_task_configuration(self):
        """Test that task has correct configuration"""
        from app.tasks.automated_gather_tasks import automated_gather_creation

        # Verify timeout configuration
        assert automated_gather_creation.soft_time_limit == 540  # 9 minutes
        assert automated_gather_creation.time_limit == 600  # 10 minutes

        # Verify retry configuration
        assert automated_gather_creation.max_retries == 3
        assert automated_gather_creation.autoretry_for == (ConnectionError, TimeoutError)

    def test_task_type_registered(self):
        """Test that task type is registered in enum"""
        from app.models.task import TaskType

        assert hasattr(TaskType, 'AUTOMATED_GATHER_CREATION')
        assert TaskType.AUTOMATED_GATHER_CREATION.value == 'automated_gather_creation'
    


class TestContentGenerator:
    """Test content generator agent"""
    
    def test_generate_mock_content(self):
        """Test mock content generation"""
        from app.agents.gather_content_generator import _generate_mock_content
        
        department = {
            'slug': 'story',
            'name': 'Story',
            'description': 'Story development'
        }
        
        previous_departments = []
        
        items = _generate_mock_content(department, previous_departments)
        
        assert len(items) == 3
        assert all('content' in item for item in items)
        assert all('summary' in item for item in items)
        assert all('context' in item for item in items)


class TestDuplicateDetector:
    """Test duplicate detector agent"""
    
    def test_content_hash(self):
        """Test content hashing"""
        from app.agents.duplicate_detector import _content_hash
        
        content1 = "This is a test"
        content2 = "This is a test"
        content3 = "This is different"
        
        hash1 = _content_hash(content1)
        hash2 = _content_hash(content2)
        hash3 = _content_hash(content3)
        
        assert hash1 == hash2
        assert hash1 != hash3
    
    def test_fallback_similarity(self):
        """Test fallback similarity calculation"""
        from app.agents.duplicate_detector import _fallback_similarity
        
        text1 = "The quick brown fox jumps over the lazy dog"
        text2 = "The quick brown fox jumps over the lazy dog"
        text3 = "A completely different sentence"
        
        similarity1 = _fallback_similarity(text1, text2)
        similarity2 = _fallback_similarity(text1, text3)
        
        assert similarity1 == 1.0  # Identical
        assert similarity2 < 0.5  # Very different


class TestQualityAnalyzer:
    """Test quality analyzer agent"""
    
    def test_calculate_mock_quality(self):
        """Test mock quality calculation"""
        from app.agents.quality_analyzer import _calculate_mock_quality
        
        items = [
            {
                'content': 'A' * 500,
                'summary': 'Item 1',
                'automationMetadata': {'department': 'story'}
            },
            {
                'content': 'B' * 500,
                'summary': 'Item 2',
                'automationMetadata': {'department': 'story'}
            }
        ]
        
        score = _calculate_mock_quality(items)
        
        assert 0 <= score <= 100
        assert score > 50  # Should have decent score with 2 items

