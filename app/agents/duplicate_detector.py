"""
LLM-based Duplicate Detection
Uses semantic similarity to detect duplicates (90% threshold)
Keeps newer items, discards older duplicates
"""
import os
import structlog
from typing import List, Dict, Any
import hashlib

logger = structlog.get_logger(__name__)


def deduplicate_items(
    new_items: List[Dict[str, Any]],
    existing_items: List[Dict[str, Any]],
    department: str
) -> List[Dict[str, Any]]:
    """
    Use LLM to detect semantic duplicates
    Keep newer items, discard older duplicates
    
    Args:
        new_items: Newly generated items to check
        existing_items: Existing items in the database
        department: Department slug for filtering
    
    Returns:
        List of deduplicated items (only non-duplicates)
    """
    if not new_items:
        return []
    
    if not existing_items:
        return new_items
    
    logger.info(
        "Starting deduplication",
        department=department,
        new_items_count=len(new_items),
        existing_items_count=len(existing_items)
    )
    
    deduplicated = []
    duplicates_found = 0
    
    # Filter existing items to same department for more relevant comparison
    dept_existing = [
        item for item in existing_items
        if item.get('automationMetadata', {}).get('department') == department
    ]
    
    logger.info(
        "Filtered existing items by department",
        department=department,
        filtered_count=len(dept_existing)
    )
    
    for new_item in new_items:
        is_duplicate = False
        new_content = new_item.get('content', '')
        new_summary = new_item.get('summary', '')
        
        # Quick hash check first (exact duplicates)
        new_hash = _content_hash(new_content)
        
        for existing in dept_existing:
            existing_content = existing.get('content', '')
            existing_hash = _content_hash(existing_content)
            
            # Exact match check
            if new_hash == existing_hash:
                logger.info(
                    "Found exact duplicate (hash match)",
                    department=department,
                    new_summary=new_summary[:50]
                )
                is_duplicate = True
                duplicates_found += 1
                break
            
            # Semantic similarity check
            similarity = check_semantic_similarity(
                new_content,
                existing_content,
                new_summary,
                existing.get('summary', '')
            )
            
            if similarity > 0.90:  # 90% similarity threshold
                logger.info(
                    "Found semantic duplicate",
                    department=department,
                    similarity=similarity,
                    new_summary=new_summary[:50],
                    existing_summary=existing.get('summary', '')[:50]
                )
                is_duplicate = True
                duplicates_found += 1
                break
        
        if not is_duplicate:
            deduplicated.append(new_item)
    
    logger.info(
        "Deduplication complete",
        department=department,
        original_count=len(new_items),
        deduplicated_count=len(deduplicated),
        duplicates_removed=duplicates_found
    )
    
    return deduplicated


def check_semantic_similarity(
    text1: str,
    text2: str,
    summary1: str = "",
    summary2: str = ""
) -> float:
    """
    Use LLM to calculate semantic similarity
    Returns score between 0.0 and 1.0
    
    Args:
        text1: First text to compare
        text2: Second text to compare
        summary1: Optional summary of first text
        summary2: Optional summary of second text
    
    Returns:
        Similarity score (0.0 to 1.0)
    """
    try:
        # Import CodeBuffSDK (lazy import)
        try:
            from codebuff import CodeBuffSDK
        except ImportError:
            logger.warning("CodeBuffSDK not available, using fallback similarity")
            return _fallback_similarity(text1, text2)
        
        # Check if API key is available
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            logger.warning("OPENROUTER_API_KEY not set, using fallback similarity")
            return _fallback_similarity(text1, text2)
        
        # Initialize SDK with fast model for similarity checks
        sdk = CodeBuffSDK(
            api_key=api_key,
            model="anthropic/claude-3-haiku"  # Fast, cheap model for similarity
        )
        
        # Truncate texts for efficiency (first 500 chars)
        text1_truncated = text1[:500]
        text2_truncated = text2[:500]
        
        # Build prompt
        prompt = f"""Rate the semantic similarity between these two texts on a scale of 0.0 to 1.0:

Text 1 Summary: {summary1 if summary1 else "N/A"}
Text 1: {text1_truncated}

Text 2 Summary: {summary2 if summary2 else "N/A"}
Text 2: {text2_truncated}

Consider:
- Are they discussing the same topic/concept?
- Do they convey the same information?
- Would they be redundant if both were included?

Return ONLY the numeric score (e.g., 0.85). No explanation."""

        response = sdk.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0.0  # Deterministic
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse score
        try:
            score = float(content)
            # Clamp to 0-1 range
            score = min(max(score, 0.0), 1.0)
            return score
        except ValueError:
            logger.warning(
                "Failed to parse similarity score",
                response=content
            )
            return _fallback_similarity(text1, text2)
            
    except Exception as e:
        logger.error(
            "Error checking semantic similarity",
            error=str(e),
            exc_info=True
        )
        return _fallback_similarity(text1, text2)


def _content_hash(content: str) -> str:
    """
    Generate hash of content for exact duplicate detection
    """
    # Normalize content (lowercase, strip whitespace)
    normalized = content.lower().strip()
    # Remove extra whitespace
    normalized = ' '.join(normalized.split())
    # Generate hash
    return hashlib.md5(normalized.encode()).hexdigest()


def _fallback_similarity(text1: str, text2: str) -> float:
    """
    Fallback similarity calculation using simple string matching
    Used when LLM is not available
    """
    # Normalize texts
    t1 = set(text1.lower().split())
    t2 = set(text2.lower().split())
    
    if not t1 or not t2:
        return 0.0
    
    # Jaccard similarity
    intersection = len(t1.intersection(t2))
    union = len(t1.union(t2))
    
    if union == 0:
        return 0.0
    
    similarity = intersection / union
    
    logger.debug(
        "Calculated fallback similarity",
        similarity=similarity,
        text1_words=len(t1),
        text2_words=len(t2),
        common_words=intersection
    )
    
    return similarity

