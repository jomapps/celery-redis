"""
WebSocket Client for Real-time Progress Updates
Publishes events to Redis pub/sub for WebSocket server
"""
import os
import json
import structlog
from typing import Dict, Any
import redis

logger = structlog.get_logger(__name__)

# Redis client for pub/sub
_redis_client = None


def get_redis_client():
    """
    Get or create Redis client for pub/sub
    """
    global _redis_client
    
    if _redis_client is None:
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        _redis_client = redis.from_url(redis_url, decode_responses=True)
        logger.info("Redis pub/sub client initialized")
    
    return _redis_client


def send_websocket_event(project_id: str, event_data: Dict[str, Any]) -> bool:
    """
    Send event to WebSocket server via Redis pub/sub
    
    Args:
        project_id: Project identifier
        event_data: Event data to send
    
    Returns:
        True if sent successfully
    """
    try:
        client = get_redis_client()
        
        # Channel name: automated-gather:{projectId}
        channel = f"automated-gather:{project_id}"
        
        # Add timestamp
        event_data['timestamp'] = event_data.get('timestamp', None)
        if not event_data['timestamp']:
            from datetime import datetime
            event_data['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        # Add project_id to event
        event_data['project_id'] = project_id
        
        # Serialize to JSON
        message = json.dumps(event_data)
        
        # Publish to Redis
        client.publish(channel, message)
        
        logger.debug(
            "Sent WebSocket event",
            project_id=project_id,
            event_type=event_data.get('type'),
            channel=channel
        )
        
        return True
        
    except Exception as e:
        logger.error(
            "Error sending WebSocket event",
            project_id=project_id,
            event_type=event_data.get('type'),
            error=str(e),
            exc_info=True
        )
        return False

