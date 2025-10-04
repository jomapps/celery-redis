"""
Webhook utility for sending HTTP callbacks to external services
"""
import httpx
import asyncio
import structlog
from typing import Dict, Any, Optional
from datetime import datetime

logger = structlog.get_logger(__name__)


async def send_webhook_async(
    callback_url: str,
    payload: Dict[str, Any],
    timeout: float = 30.0,
    max_retries: int = 3
) -> bool:
    """
    Send webhook callback asynchronously with retry logic
    
    Args:
        callback_url: The URL to send the webhook to
        payload: The JSON payload to send
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        
    Returns:
        bool: True if webhook was sent successfully, False otherwise
    """
    if not callback_url:
        logger.warning("No callback URL provided, skipping webhook")
        return False
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "AI-Movie-Task-Service/1.0"
    }
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    callback_url,
                    json=payload,
                    headers=headers
                )
                
                if response.status_code in (200, 201, 202, 204):
                    logger.info(
                        "Webhook sent successfully",
                        callback_url=callback_url,
                        status_code=response.status_code,
                        task_id=payload.get('task_id')
                    )
                    return True
                else:
                    logger.warning(
                        "Webhook returned non-success status",
                        callback_url=callback_url,
                        status_code=response.status_code,
                        response_body=response.text[:500],
                        attempt=attempt + 1
                    )
                    
        except httpx.TimeoutException:
            logger.warning(
                "Webhook request timed out",
                callback_url=callback_url,
                timeout=timeout,
                attempt=attempt + 1
            )
            
        except httpx.RequestError as e:
            logger.warning(
                "Webhook request failed",
                callback_url=callback_url,
                error=str(e),
                attempt=attempt + 1
            )
            
        except Exception as e:
            logger.error(
                "Unexpected error sending webhook",
                callback_url=callback_url,
                error=str(e),
                attempt=attempt + 1
            )
        
        # Wait before retrying (exponential backoff)
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            await asyncio.sleep(wait_time)
    
    logger.error(
        "Failed to send webhook after all retries",
        callback_url=callback_url,
        max_retries=max_retries,
        task_id=payload.get('task_id')
    )
    return False


def send_webhook_sync(
    callback_url: str,
    payload: Dict[str, Any],
    timeout: float = 30.0,
    max_retries: int = 3
) -> bool:
    """
    Synchronous wrapper for send_webhook_async
    Used in Celery task context where we need to run async code synchronously
    
    Args:
        callback_url: The URL to send the webhook to
        payload: The JSON payload to send
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        
    Returns:
        bool: True if webhook was sent successfully, False otherwise
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(
        send_webhook_async(callback_url, payload, timeout, max_retries)
    )


def build_success_webhook_payload(
    task_id: str,
    project_id: str,
    result: Dict[str, Any],
    processing_time: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build standardized webhook payload for successful task completion
    
    Args:
        task_id: The task UUID
        project_id: The project ID
        result: The task result data
        processing_time: Optional processing time in seconds
        metadata: Optional additional metadata
        
    Returns:
        Dict containing the webhook payload
    """
    payload = {
        "task_id": task_id,
        "project_id": project_id,
        "status": "completed",
        "result": result,
        "completed_at": datetime.utcnow().isoformat() + "Z"
    }
    
    if processing_time is not None:
        payload["processing_time"] = processing_time
    
    if metadata:
        payload["metadata"] = metadata
    
    return payload


def build_failure_webhook_payload(
    task_id: str,
    project_id: str,
    error: str,
    traceback: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build standardized webhook payload for failed task
    
    Args:
        task_id: The task UUID
        project_id: The project ID
        error: The error message
        traceback: Optional error traceback
        metadata: Optional additional metadata
        
    Returns:
        Dict containing the webhook payload
    """
    payload = {
        "task_id": task_id,
        "project_id": project_id,
        "status": "failed",
        "error": error,
        "failed_at": datetime.utcnow().isoformat() + "Z"
    }
    
    if traceback:
        payload["traceback"] = traceback[:2000]  # Limit traceback size
    
    if metadata:
        payload["metadata"] = metadata
    
    return payload

