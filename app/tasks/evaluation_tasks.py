"""
Department evaluation tasks for Aladdin project readiness system
Evaluates movie production departments using AI-powered analysis
"""
import json
import structlog
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_task import BaseTaskWithBrain
from ..celery_app import celery_app
from ..config.settings import settings

logger = structlog.get_logger(__name__)


class EvaluateDepartmentTask(BaseTaskWithBrain):
    """
    Evaluate a department's readiness based on gathered data
    Uses AI to analyze content quality and provide ratings
    
    This task integrates with the Aladdin application's Project Readiness system
    and provides comprehensive evaluation with ratings, issues, and suggestions.
    """
    
    name = "evaluate_department"
    
    def execute_task(
        self,
        project_id: str,
        department_slug: str,
        department_number: int,
        gather_data: List[Dict[str, Any]],
        previous_evaluations: Optional[List[Dict[str, Any]]] = None,
        threshold: int = 80,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Main evaluation logic
        
        Args:
            project_id: Project identifier
            department_slug: Department name (e.g., "story", "character")
            department_number: Sequential department number (1-12)
            gather_data: Array of gathered content items
            previous_evaluations: Array of previous department evaluations
            threshold: Minimum passing score (0-100)
            
        Returns:
            Evaluation result with rating, summary, issues, and suggestions
        """
        start_time = datetime.utcnow()
        
        if previous_evaluations is None:
            previous_evaluations = []
        
        logger.info(
            "Starting department evaluation",
            project_id=project_id,
            department=department_slug,
            department_number=department_number,
            gather_count=len(gather_data),
            threshold=threshold
        )
        
        # Validate input
        if not gather_data:
            logger.warning("No gather data provided", department=department_slug)
            return self._create_insufficient_data_result(department_slug, threshold)
        
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
                query = f"department evaluation best practices for {department_slug}"
                context = await brain_client.query_context(
                    query=query,
                    project_id=project_id,
                    limit=5
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
            f"- {eval.get('department', 'unknown')}: {eval.get('rating', 0)}/100 - {eval.get('summary', 'N/A')}"
            for eval in previous_evaluations
        ]) if previous_evaluations else "No previous evaluations"
        
        prompt = f"""You are an expert film production evaluator. Evaluate the {department_slug} department for a movie production project.

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
        Call AI service to evaluate department
        
        This is a placeholder implementation that returns mock data.
        Replace with actual AI integration (OpenAI, Anthropic, etc.)
        """
        try:
            # TODO: Implement actual AI integration
            # Example with OpenAI:
            # import openai
            # response = openai.ChatCompletion.create(
            #     model="gpt-4",
            #     messages=[
            #         {"role": "system", "content": "You are an expert film production evaluator."},
            #         {"role": "user", "content": prompt}
            #     ],
            #     temperature=0.7,
            #     max_tokens=2000
            # )
            # result_text = response.choices[0].message.content
            # result = json.loads(result_text)
            
            # Mock implementation for testing
            logger.info("Using mock AI evaluator", department=department)
            
            # Generate realistic mock evaluation
            rating = 75 + (hash(department) % 20)  # 75-94
            
            result = {
                "rating": rating,
                "summary": f"The {department} department shows strong foundational work with clear direction. "
                          f"Content demonstrates professional quality and aligns well with production requirements. "
                          f"Some areas need refinement before final approval.",
                "issues": [
                    f"{department.capitalize()} documentation needs more detail in technical specifications",
                    f"Timeline estimates for {department} tasks appear optimistic",
                    f"Resource allocation for {department} needs clarification",
                    f"Dependencies with other departments not fully mapped"
                ],
                "suggestions": [
                    f"Add detailed technical specifications for {department} deliverables",
                    f"Review and adjust {department} timeline with 20% buffer",
                    f"Create resource allocation matrix for {department}",
                    f"Document cross-department dependencies clearly",
                    f"Schedule review meeting with {department} stakeholders"
                ],
                "iteration_count": 1,
                "confidence": 0.85,
                "model": "mock-evaluator-v1",
                "tokens_used": 1500
            }
            
            return result
            
        except Exception as e:
            logger.error("AI evaluation failed", error=str(e), department=department)
            # Return fallback result
            return {
                "rating": 50,
                "summary": f"Evaluation could not be completed: {str(e)}",
                "issues": ["AI evaluation service unavailable", "Unable to assess content quality"],
                "suggestions": ["Retry evaluation when service is available", "Check AI service configuration"],
                "iteration_count": 0,
                "confidence": 0.0,
                "model": "fallback",
                "tokens_used": 0
            }
    
    def _create_insufficient_data_result(
        self,
        department_slug: str,
        threshold: int
    ) -> Dict[str, Any]:
        """Create result for insufficient gather data"""
        return {
            "department": department_slug,
            "rating": 0,
            "evaluation_result": "fail",
            "evaluation_summary": f"Insufficient data provided for {department_slug} evaluation. No content available to assess.",
            "issues": [
                "No gather data provided",
                "Cannot assess department readiness without content",
                "Minimum content requirements not met"
            ],
            "suggestions": [
                f"Gather content for {department_slug} department",
                "Ensure all required fields are populated",
                "Provide at least 2-3 content items for evaluation"
            ],
            "iteration_count": 0,
            "processing_time": 0.0,
            "metadata": {
                "model": "validation",
                "tokens_used": 0,
                "confidence_score": 1.0
            }
        }


# Create Celery task instance
@celery_app.task(bind=True, base=EvaluateDepartmentTask, queue='cpu_intensive')
def evaluate_department(
    self,
    project_id: str,
    department_slug: str,
    department_number: int,
    gather_data: List[Dict[str, Any]],
    previous_evaluations: Optional[List[Dict[str, Any]]] = None,
    threshold: int = 80,
    callback_url: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluate department readiness with AI-powered analysis
    
    This task is called by the Aladdin application to evaluate
    movie production departments based on gathered content.
    """
    return self.execute_task(
        project_id=project_id,
        department_slug=department_slug,
        department_number=department_number,
        gather_data=gather_data,
        previous_evaluations=previous_evaluations,
        threshold=threshold
    )

