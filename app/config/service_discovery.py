"""
Service discovery configuration for AI Movie Platform
Defines service URLs and communication patterns across environments
"""
from enum import Enum
from typing import Dict, Optional
import os


class Environment(str, Enum):
    """Environment types for service discovery"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


# Complete service registry for AI Movie Platform
SERVICE_REGISTRY: Dict[Environment, Dict[str, str]] = {
    Environment.DEVELOPMENT: {
        # Core application services
        "auto_movie": "http://localhost:3010",
        "task_service": "http://localhost:8001",
        "brain_service": "http://localhost:8002",
        
        # Database services
        # "neo4j_http": "http://localhost:7474",  # Now accessed via brain service
        # "neo4j_bolt": "bolt://localhost:7687",   # Now accessed via brain service
        "redis": "redis://default:8XTmX6Zbo1iNV6ZHvsvUQfKxssr2EmGTemAaqq2G4ZTc2BJky11MAnwQaKU879pI@zs0gg4csc00k800kwgc84gcg:6379/0",
        "mongodb": "mongodb://localhost:27017",
        
        # Monitoring services
        "prometheus": "http://localhost:9090",
        "grafana": "http://localhost:3001",
        "health_api": "http://localhost:8100",
        
        # Development services
        "api_docs": "http://localhost:8300",
        "test_env": "http://localhost:3011",
        "upload_proxy": "http://localhost:8200",
        
        # Future services (Phase 4+)
        "agent_orchestrator": "http://localhost:8003",
        "story_mcp": "http://localhost:8010",
        "character_mcp": "http://localhost:8011",
        "visual_mcp": "http://localhost:8012",
        "audio_mcp": "http://localhost:8013",
        "asset_mcp": "http://localhost:8014",
    },
    Environment.STAGING: {
        # Core application services  
        "auto_movie": "https://auto-movie.ngrok.pro",
        "task_service": "https://tasks.ngrok.pro",
        "brain_service": "https://brain.ngrok.pro",
        
        # Database and infrastructure
        # "neo4j_http": "https://neo4j.ngrok.pro",  # Now accessed via brain service
        
        # Monitoring services
        "prometheus": "https://metrics.ngrok.pro",
        "grafana": "https://dashboard.ngrok.pro",
        "health_api": "https://health.ngrok.pro",
        
        # Extended services
        "agent_orchestrator": "https://agents.ngrok.pro",
        "story_mcp": "https://story.ngrok.pro",
        "character_mcp": "https://characters.ngrok.pro",
        "visual_mcp": "https://visuals.ngrok.pro",
        "audio_mcp": "https://audio.ngrok.pro",
        "asset_mcp": "https://assets.ngrok.pro",
        
        # Development services
        "api_docs": "https://app-docs.ngrok.pro",
        "test_env": "https://app-test.ngrok.pro",
    },
    Environment.PRODUCTION: {
        # Core application services
        "auto_movie": "https://auto-movie.ft.tc",
        "task_service": "https://tasks.ft.tc",
        "brain_service": "https://brain.ft.tc",
        
        # Database and infrastructure
        # "neo4j_http": "https://neo4j.ft.tc",  # Now accessed via brain service
        
        # Media CDN
        "media_cdn": "https://media.ft.tc",
        
        # Monitoring services
        "prometheus": "https://metrics.ft.tc",
        "grafana": "https://dashboard.ft.tc",
        "health_api": "https://health.ft.tc",
        
        # Extended services
        "agent_orchestrator": "https://agents.ft.tc",
        "story_mcp": "https://story.ft.tc",
        "character_mcp": "https://characters.ft.tc",
        "visual_mcp": "https://visuals.ft.tc",
        "audio_mcp": "https://audio.ft.tc",
        "asset_mcp": "https://assets.ft.tc",
        
        # Development/staging services
        "api_docs": "https://app-docs.ft.tc",
        "test_env": "https://app-test.ft.tc",
    }
}


def get_current_environment() -> Environment:
    """Determine current environment from environment variables"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    try:
        return Environment(env)
    except ValueError:
        return Environment.DEVELOPMENT


def get_service_url(service_name: str, environment: Optional[Environment] = None) -> str:
    """
    Get service URL for the current or specified environment
    
    Args:
        service_name: Name of the service (e.g., 'auto_movie', 'brain_service')
        environment: Optional environment override
        
    Returns:
        str: Service URL or empty string if not found
    """
    if environment is None:
        environment = get_current_environment()
    
    return SERVICE_REGISTRY[environment].get(service_name, "")


def get_auto_movie_app_url(environment: Optional[Environment] = None) -> str:
    """Get Auto-Movie App URL for current environment"""
    return get_service_url("auto_movie", environment)


def get_brain_service_url(environment: Optional[Environment] = None) -> str:
    """Get MCP Brain Service URL for current environment"""
    return get_service_url("brain_service", environment)


def get_media_cdn_url(environment: Optional[Environment] = None) -> str:
    """Get media CDN URL for current environment"""
    if environment is None:
        environment = get_current_environment()
        
    if environment == Environment.PRODUCTION:
        return get_service_url("media_cdn", environment)
    else:
        # Use R2 endpoint for development/staging
        return os.getenv("R2_PUBLIC_URL", "")


def get_webhook_url(endpoint: str, environment: Optional[Environment] = None) -> str:
    """
    Get webhook URL for specific endpoint
    
    Args:
        endpoint: Webhook endpoint path (e.g., 'task-complete')
        environment: Optional environment override
        
    Returns:
        str: Complete webhook URL
    """
    base_url = get_auto_movie_app_url(environment)
    return f"{base_url}/api/webhooks/{endpoint}"


# Service health check endpoints
HEALTH_CHECK_ENDPOINTS = {
    "auto_movie": "/api/health",
    "task_service": "/api/v1/health", 
    "brain_service": "/api/v1/health",
    "prometheus": "/-/healthy",
    "grafana": "/api/health",
}


def get_health_check_url(service_name: str, environment: Optional[Environment] = None) -> str:
    """Get health check URL for a service"""
    base_url = get_service_url(service_name, environment)
    endpoint = HEALTH_CHECK_ENDPOINTS.get(service_name, "/health")
    return f"{base_url}{endpoint}"


# Service communication timeouts (seconds)
SERVICE_TIMEOUTS = {
    "auto_movie": 30,       # Auto-Movie App API calls
    "brain_service": 60,    # Knowledge graph queries can be slower
    "media_upload": 300,    # Large media file uploads
    "webhook": 10,          # Webhook callbacks should be fast
    "health_check": 5,      # Health checks should be immediate
}


def get_service_timeout(operation: str) -> int:
    """Get appropriate timeout for service operation"""
    return SERVICE_TIMEOUTS.get(operation, 30)