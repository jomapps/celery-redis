"""
Quality Analyzer for Department Gather Items
Analyzes quality score for a department's gather items
"""
import os
import structlog
from typing import Dict, Any, List

logger = structlog.get_logger(__name__)


def analyze_department_quality(
    project_id: str,
    department: Dict[str, Any],
    gather_items: List[Dict[str, Any]]
) -> float:
    """
    Analyze quality score for a department's gather items
    
    Args:
        project_id: Project identifier
        department: Department configuration
        gather_items: All gather items (will filter by department)
    
    Returns:
        Quality score (0-100)
    """
    dept_slug = department['slug']
    dept_name = department.get('name', dept_slug)
    
    # Filter items for this department
    dept_items = [
        item for item in gather_items
        if item.get('automationMetadata', {}).get('department') == dept_slug
    ]
    
    if not dept_items:
        logger.info(
            "No items found for department",
            department=dept_slug
        )
        return 0.0
    
    logger.info(
        "Analyzing department quality",
        department=dept_slug,
        items_count=len(dept_items)
    )
    
    try:
        # Import CodeBuffSDK (lazy import)
        try:
            from codebuff import CodeBuffSDK
        except ImportError:
            logger.warning("CodeBuffSDK not available, using mock quality score")
            return _calculate_mock_quality(dept_items)
        
        # Check if API key is available
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            logger.warning("OPENROUTER_API_KEY not set, using mock quality score")
            return _calculate_mock_quality(dept_items)
        
        # Initialize SDK
        sdk = CodeBuffSDK(
            api_key=api_key,
            model="anthropic/claude-3-haiku"  # Fast model for quality checks
        )
        
        # Format items for analysis
        items_summary = _format_items_for_analysis(dept_items)
        
        # Build prompt
        prompt = f"""Analyze the quality and completeness of gather items for the **{dept_name}** department.

**Department**: {dept_name}
**Description**: {department.get('description', 'N/A')}
**Number of Items**: {len(dept_items)}

**Gather Items**:
{items_summary}

**Evaluation Criteria**:
1. **Coverage** (30%): Do items cover diverse aspects of {dept_name}?
2. **Depth** (25%): Are items detailed and actionable?
3. **Relevance** (25%): Are items specific to {dept_name}'s needs?
4. **Quality** (20%): Are items well-written and clear?

**Task**: Rate the overall quality on a scale of 0-100.

Consider:
- Are there enough items to cover the department's needs?
- Do items provide actionable, production-ready information?
- Is there good variety and depth?
- Are items specific and relevant?

Return ONLY the numeric score (e.g., 85). No explanation."""

        response = sdk.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0.0  # Deterministic
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse score
        try:
            score = float(content)
            # Clamp to 0-100 range
            score = min(max(score, 0.0), 100.0)
            
            logger.info(
                "Quality analysis complete",
                department=dept_slug,
                quality_score=score,
                items_count=len(dept_items)
            )
            
            return score
        except ValueError:
            logger.warning(
                "Failed to parse quality score",
                department=dept_slug,
                response=content
            )
            return _calculate_mock_quality(dept_items)
            
    except Exception as e:
        logger.error(
            "Error analyzing quality",
            department=dept_slug,
            error=str(e),
            exc_info=True
        )
        return _calculate_mock_quality(dept_items)


def _format_items_for_analysis(items: List[Dict[str, Any]]) -> str:
    """
    Format items for quality analysis prompt
    """
    formatted = []
    for i, item in enumerate(items, 1):
        summary = item.get('summary', item.get('content', '')[:100])
        content_preview = item.get('content', '')[:200]
        iteration = item.get('automationMetadata', {}).get('iteration', 'N/A')
        
        formatted.append(
            f"{i}. **{summary}** (Iteration {iteration})\n"
            f"   Preview: {content_preview}..."
        )
    
    return "\n\n".join(formatted)


def _calculate_mock_quality(items: List[Dict[str, Any]]) -> float:
    """
    Calculate mock quality score based on simple heuristics
    Used when LLM is not available
    """
    if not items:
        return 0.0
    
    # Simple heuristic: base score + bonus for quantity and content length
    base_score = 50.0
    
    # Bonus for number of items (up to 20 points)
    item_bonus = min(len(items) * 2, 20)
    
    # Bonus for content length (up to 20 points)
    avg_length = sum(len(item.get('content', '')) for item in items) / len(items)
    length_bonus = min(avg_length / 50, 20)  # 1000 chars = 20 points
    
    # Bonus for having summaries (up to 10 points)
    summary_bonus = sum(1 for item in items if item.get('summary')) / len(items) * 10
    
    score = base_score + item_bonus + length_bonus + summary_bonus
    score = min(score, 100.0)
    
    logger.info(
        "Calculated mock quality score",
        items_count=len(items),
        score=score,
        item_bonus=item_bonus,
        length_bonus=length_bonus,
        summary_bonus=summary_bonus
    )
    
    return score

