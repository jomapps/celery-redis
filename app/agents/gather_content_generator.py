"""
Gather Content Generator using @codebuff/sdk
Generates department-specific gather items with AI
"""
import os
import json
import re
import structlog
from typing import Dict, Any, List

logger = structlog.get_logger(__name__)


def generate_content_batch(
    project_id: str,
    department: Dict[str, Any],
    existing_context: List[Dict[str, Any]],
    previous_departments: List[Dict[str, Any]],
    model: str
) -> List[Dict[str, Any]]:
    """
    Generate gather items for a department using @codebuff/sdk
    Uses department-specific model from defaultModel field
    
    Args:
        project_id: Project identifier
        department: Department configuration dict
        existing_context: Existing gather items + brain context
        previous_departments: Results from previously processed departments
        model: OpenRouter model to use (from department.defaultModel)
    
    Returns:
        List of generated gather items with content, summary, context
    """
    try:
        # Import CodeBuffSDK (lazy import to avoid startup issues)
        try:
            from codebuff import CodeBuffSDK
        except ImportError:
            logger.warning("CodeBuffSDK not available, using mock generation")
            return _generate_mock_content(department, previous_departments)
        
        # Initialize SDK
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            logger.warning("OPENROUTER_API_KEY not set, using mock generation")
            return _generate_mock_content(department, previous_departments)
        
        sdk = CodeBuffSDK(
            api_key=api_key,
            model=model  # Use department's model preference
        )
        
        dept_slug = department['slug']
        dept_name = department.get('name', dept_slug)
        dept_description = department.get('description', f'Generate content for {dept_name}')
        
        # Build cascading context from ALL previous departments
        prev_context = ""
        if previous_departments:
            prev_context = "\n\n".join([
                f"**{dept['name']}** (Quality: {dept['quality_score']}%, {dept['items_created']} items):\n"
                f"- Iterations: {dept['iterations']}\n"
                f"- Model: {dept.get('model', 'N/A')}"
                for dept in previous_departments
            ])
        
        # Format existing gather items (last 20 for context)
        existing_summary = _format_gather_items(existing_context[-20:] if len(existing_context) > 20 else existing_context)
        
        # Build the prompt
        prompt = f"""You are generating gather items for the **{dept_name}** department in a movie production project.

**Your Role**: {dept_description}

**Previous Department Context** (Build upon this):
{prev_context if prev_context else "No previous context yet (this is the first department)"}

**Existing Gather Items Summary** (Last 20 items):
{existing_summary if existing_summary else "No existing items yet"}

**Task**: Generate 5-10 NEW gather items that:
1. Build upon insights from previous departments{f" (especially {previous_departments[-1]['name']})" if previous_departments else " (or the overall project)"}
2. Provide rich, detailed content specific to {dept_name}
3. Are NOT duplicates of existing content (check summaries above)
4. Cover different aspects/angles of {dept_name} (e.g., technical specs, creative vision, practical considerations)
5. Are production-ready and actionable
6. Each item should be 200-500 words of detailed, specific content

**Output Format** (JSON array):
[
  {{
    "content": "Detailed content here (200-500 words). Be specific and actionable.",
    "summary": "One-line summary (max 100 chars)",
    "context": "Why this matters for {dept_name} and how it connects to previous departments"
  }},
  ...
]

Return ONLY the JSON array. No explanation or markdown formatting."""

        logger.info(
            "Generating content with AI",
            department=dept_slug,
            model=model,
            prompt_length=len(prompt)
        )
        
        # Call the AI model
        response = sdk.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000,
            temperature=0.7
        )
        
        content = response.choices[0].message.content.strip()
        
        logger.info(
            "Received AI response",
            department=dept_slug,
            response_length=len(content)
        )
        
        # Parse JSON response
        items = _parse_json_response(content)
        
        if not items:
            logger.warning(
                "Failed to parse AI response, using mock generation",
                department=dept_slug
            )
            return _generate_mock_content(department, previous_departments)
        
        logger.info(
            "Successfully generated content",
            department=dept_slug,
            items_count=len(items)
        )
        
        return items
        
    except Exception as e:
        logger.error(
            "Error generating content",
            department=department.get('slug'),
            error=str(e),
            exc_info=True
        )
        # Fallback to mock generation
        return _generate_mock_content(department, previous_departments)


def _parse_json_response(content: str) -> List[Dict[str, Any]]:
    """
    Parse JSON from AI response, handling various formats
    """
    try:
        # Try direct JSON parse
        items = json.loads(content)
        if isinstance(items, list):
            return items
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON array from markdown or text
    try:
        # Remove markdown code blocks
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        
        # Find JSON array
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            items = json.loads(match.group(0))
            if isinstance(items, list):
                return items
    except (json.JSONDecodeError, AttributeError):
        pass
    
    return []


def _format_gather_items(items: List[Dict[str, Any]]) -> str:
    """
    Format gather items for context in prompt
    """
    if not items:
        return "No items available"
    
    formatted = []
    for i, item in enumerate(items[-20:], 1):  # Last 20 items
        summary = item.get('summary', item.get('content', '')[:100])
        dept = item.get('automationMetadata', {}).get('department', 'manual')
        formatted.append(f"{i}. [{dept}] {summary}")
    
    return "\n".join(formatted)


def _generate_mock_content(
    department: Dict[str, Any],
    previous_departments: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Generate mock content when AI is not available
    Used for testing and fallback
    """
    dept_slug = department['slug']
    dept_name = department.get('name', dept_slug)
    
    # Build context from previous departments
    prev_context = ""
    if previous_departments:
        prev_context = f" Building on insights from {previous_departments[-1]['name']}."
    
    mock_items = [
        {
            "content": f"Mock gather item 1 for {dept_name}.{prev_context} This is a detailed description of a key aspect that needs to be considered for this department. It includes technical specifications, creative requirements, and practical considerations that the team should address during production.",
            "summary": f"Mock item 1 for {dept_name}",
            "context": f"This is important for {dept_name} because it establishes the foundation for subsequent work."
        },
        {
            "content": f"Mock gather item 2 for {dept_name}.{prev_context} This item focuses on a different angle, providing complementary information that enhances the overall understanding of what this department needs to accomplish. It includes specific examples and actionable steps.",
            "summary": f"Mock item 2 for {dept_name}",
            "context": f"This connects to {dept_name}'s core responsibilities and ensures quality standards are met."
        },
        {
            "content": f"Mock gather item 3 for {dept_name}.{prev_context} This third item explores yet another dimension, offering insights into potential challenges and solutions. It provides a comprehensive view that helps the team anticipate and prepare for various scenarios.",
            "summary": f"Mock item 3 for {dept_name}",
            "context": f"This is crucial for {dept_name} to maintain consistency and achieve the desired outcomes."
        }
    ]
    
    logger.info(
        "Generated mock content",
        department=dept_slug,
        items_count=len(mock_items)
    )
    
    return mock_items

