"""
Test department evaluation tasks
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from app.tasks.evaluation_tasks import EvaluateDepartmentTask, evaluate_department


class TestEvaluateDepartmentTask:
    """Test the EvaluateDepartmentTask class"""
    
    def test_execute_task_with_valid_data(self):
        """Test successful evaluation with valid gather data"""
        task = EvaluateDepartmentTask()
        
        gather_data = [
            {
                "content": "Story follows a young wizard discovering magical powers",
                "summary": "Main story premise",
                "context": "Fantasy adventure"
            },
            {
                "content": "Three-act structure with clear character arc",
                "summary": "Story structure",
                "context": "Narrative framework"
            }
        ]
        
        with patch.object(task, 'run_async_in_sync', return_value={}):
            result = task.execute_task(
                project_id="test-project-123",
                department_slug="story",
                department_number=1,
                gather_data=gather_data,
                previous_evaluations=[],
                threshold=80
            )
        
        # Verify result structure
        assert "department" in result
        assert result["department"] == "story"
        assert "rating" in result
        assert isinstance(result["rating"], int)
        assert 0 <= result["rating"] <= 100
        assert "evaluation_result" in result
        assert result["evaluation_result"] in ["pass", "fail"]
        assert "evaluation_summary" in result
        assert isinstance(result["evaluation_summary"], str)
        assert "issues" in result
        assert isinstance(result["issues"], list)
        assert "suggestions" in result
        assert isinstance(result["suggestions"], list)
        assert "iteration_count" in result
        assert "processing_time" in result
        assert "metadata" in result
    
    def test_execute_task_with_no_gather_data(self):
        """Test evaluation with no gather data returns insufficient data result"""
        task = EvaluateDepartmentTask()
        
        with patch.object(task, 'run_async_in_sync', return_value={}):
            result = task.execute_task(
                project_id="test-project-123",
                department_slug="character",
                department_number=2,
                gather_data=[],
                previous_evaluations=[],
                threshold=80
            )
        
        # Should return insufficient data result
        assert result["rating"] == 0
        assert result["evaluation_result"] == "fail"
        assert "insufficient" in result["evaluation_summary"].lower()
        assert len(result["issues"]) > 0
        assert len(result["suggestions"]) > 0
    
    def test_execute_task_with_previous_evaluations(self):
        """Test evaluation considers previous evaluations"""
        task = EvaluateDepartmentTask()
        
        gather_data = [
            {"content": "Production schedule and budget", "summary": "Planning docs"}
        ]
        
        previous_evaluations = [
            {"department": "story", "rating": 85, "summary": "Strong narrative"},
            {"department": "character", "rating": 90, "summary": "Well-developed characters"}
        ]
        
        with patch.object(task, 'run_async_in_sync', return_value={}):
            result = task.execute_task(
                project_id="test-project-123",
                department_slug="production",
                department_number=3,
                gather_data=gather_data,
                previous_evaluations=previous_evaluations,
                threshold=80
            )
        
        assert result["department"] == "production"
        assert "rating" in result
    
    def test_evaluation_result_pass_or_fail(self):
        """Test evaluation_result is correctly set based on threshold"""
        task = EvaluateDepartmentTask()
        
        gather_data = [{"content": "Test content", "summary": "Test"}]
        
        with patch.object(task, 'run_async_in_sync', return_value={}):
            # Mock the AI evaluator to return specific rating
            with patch.object(task, '_call_ai_evaluator') as mock_ai:
                # Test pass scenario
                mock_ai.return_value = {
                    "rating": 85,
                    "summary": "Good work",
                    "issues": ["Minor issue"],
                    "suggestions": ["Suggestion"],
                    "iteration_count": 1,
                    "confidence": 0.9,
                    "model": "test",
                    "tokens_used": 100
                }
                
                result = task.execute_task(
                    project_id="test-project",
                    department_slug="story",
                    department_number=1,
                    gather_data=gather_data,
                    threshold=80
                )
                
                assert result["rating"] == 85
                assert result["evaluation_result"] == "pass"
                
                # Test fail scenario
                mock_ai.return_value["rating"] = 75
                
                result = task.execute_task(
                    project_id="test-project",
                    department_slug="story",
                    department_number=1,
                    gather_data=gather_data,
                    threshold=80
                )
                
                assert result["rating"] == 75
                assert result["evaluation_result"] == "fail"
    
    def test_build_evaluation_prompt(self):
        """Test prompt building includes all necessary information"""
        task = EvaluateDepartmentTask()
        
        gather_data = [
            {"content": "Content 1", "summary": "Summary 1", "context": "Context 1"},
            {"content": "Content 2", "summary": "Summary 2"}
        ]
        
        previous_evaluations = [
            {"department": "story", "rating": 85, "summary": "Good"}
        ]
        
        prompt = task._build_evaluation_prompt(
            department_slug="character",
            department_number=2,
            gather_data=gather_data,
            previous_evaluations=previous_evaluations,
            threshold=80,
            brain_context={}
        )
        
        # Verify prompt contains key information
        assert "character" in prompt.lower()
        assert "Department #2" in prompt
        assert "80/100" in prompt
        assert "Content 1" in prompt
        assert "Content 2" in prompt
        assert "story: 85/100" in prompt
    
    def test_call_ai_evaluator_returns_valid_structure(self):
        """Test AI evaluator returns properly structured result"""
        task = EvaluateDepartmentTask()
        
        result = task._call_ai_evaluator(
            prompt="Test prompt",
            department="story",
            threshold=80
        )
        
        # Verify all required fields are present
        assert "rating" in result
        assert "summary" in result
        assert "issues" in result
        assert "suggestions" in result
        assert "iteration_count" in result
        assert "confidence" in result
        assert "model" in result
        assert "tokens_used" in result
        
        # Verify types
        assert isinstance(result["rating"], int)
        assert isinstance(result["summary"], str)
        assert isinstance(result["issues"], list)
        assert isinstance(result["suggestions"], list)
        assert isinstance(result["iteration_count"], int)
        assert isinstance(result["confidence"], float)
    
    def test_create_insufficient_data_result(self):
        """Test insufficient data result structure"""
        task = EvaluateDepartmentTask()
        
        result = task._create_insufficient_data_result(
            department_slug="visual",
            threshold=80
        )
        
        assert result["department"] == "visual"
        assert result["rating"] == 0
        assert result["evaluation_result"] == "fail"
        assert "insufficient" in result["evaluation_summary"].lower()
        assert len(result["issues"]) > 0
        assert len(result["suggestions"]) > 0
        assert result["iteration_count"] == 0
        assert result["processing_time"] == 0.0


class TestEvaluateDepartmentCeleryTask:
    """Test the Celery task wrapper"""
    
    @patch('app.tasks.evaluation_tasks.evaluate_department.delay')
    def test_task_can_be_called(self, mock_delay):
        """Test that the Celery task can be called"""
        mock_delay.return_value = Mock(id="test-task-id")
        
        result = evaluate_department.delay(
            project_id="test-project",
            department_slug="story",
            department_number=1,
            gather_data=[{"content": "Test"}],
            threshold=80
        )
        
        assert result.id == "test-task-id"
        mock_delay.assert_called_once()


class TestEvaluationIntegration:
    """Integration tests for evaluation workflow"""
    
    def test_full_evaluation_workflow(self):
        """Test complete evaluation workflow"""
        task = EvaluateDepartmentTask()
        
        # Simulate real-world data
        gather_data = [
            {
                "content": "The story follows a detective investigating a series of mysterious disappearances in a small coastal town. As they dig deeper, they uncover a conspiracy involving the town's founding families.",
                "summary": "Main plot synopsis",
                "context": "Mystery thriller genre"
            },
            {
                "content": "Three-act structure: Act 1 - Detective arrives and first disappearance occurs. Act 2 - Investigation reveals patterns and personal stakes. Act 3 - Confrontation with antagonist and resolution.",
                "summary": "Story structure breakdown",
                "context": "Narrative framework"
            },
            {
                "content": "Protagonist: Detective Sarah Chen - experienced, intuitive, haunted by past failure. Antagonist: Town Mayor - charismatic, ruthless, protecting dark secret.",
                "summary": "Character profiles",
                "context": "Character development"
            }
        ]
        
        previous_evaluations = []
        
        with patch.object(task, 'run_async_in_sync', return_value={}):
            result = task.execute_task(
                project_id="mystery-thriller-001",
                department_slug="story",
                department_number=1,
                gather_data=gather_data,
                previous_evaluations=previous_evaluations,
                threshold=80
            )
        
        # Verify comprehensive result
        assert result["department"] == "story"
        assert result["rating"] > 0
        assert result["evaluation_result"] in ["pass", "fail"]
        assert len(result["evaluation_summary"]) > 50  # Substantial summary
        assert len(result["issues"]) >= 3  # At least 3 issues
        assert len(result["suggestions"]) >= 3  # At least 3 suggestions
        assert result["processing_time"] > 0
        assert result["metadata"]["tokens_used"] > 0

