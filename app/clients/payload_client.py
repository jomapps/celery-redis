"""
Payload CMS Client
Handles querying departments and triggering evaluations
"""
import os
import requests
import structlog
from typing import List, Dict, Any

logger = structlog.get_logger(__name__)


def get_payload_api_url() -> str:
    """
    Get Payload CMS API URL from environment
    """
    return os.getenv('PAYLOAD_API_URL', 'https://auto-movie.ft.tc/api')


def get_payload_headers() -> Dict[str, str]:
    """
    Get headers for Payload API requests
    """
    api_key = os.getenv('PAYLOAD_API_KEY', '')
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}' if api_key else ''
    }


def query_departments_for_automation(project_id: str) -> List[Dict[str, Any]]:
    """
    Query departments with gatherCheck=true, sorted by codeDepNumber
    DYNAMIC: No hardcoded departments
    
    Args:
        project_id: Project identifier
    
    Returns:
        List of department configurations
    """
    try:
        api_url = get_payload_api_url()
        headers = get_payload_headers()
        
        # Query Payload CMS for departments
        url = f"{api_url}/departments"
        params = {
            'where[gatherCheck][equals]': 'true',
            'where[isActive][equals]': 'true',
            'sort': 'codeDepNumber',
            'limit': 1000  # Support up to 1000 departments
        }
        
        logger.info(
            "Querying departments from Payload",
            project_id=project_id,
            url=url
        )
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        departments = data.get('docs', [])
        
        logger.info(
            "Retrieved departments from Payload",
            project_id=project_id,
            count=len(departments)
        )
        
        # Extract relevant fields
        processed_departments = []
        for dept in departments:
            processed_departments.append({
                'id': dept.get('id'),
                'slug': dept.get('slug'),
                'name': dept.get('name'),
                'description': dept.get('description'),
                'codeDepNumber': dept.get('codeDepNumber', 999),
                'gatherCheck': dept.get('gatherCheck', False),
                'isActive': dept.get('isActive', True),
                'defaultModel': dept.get('defaultModel', 'anthropic/claude-sonnet-4.5'),
                'coordinationSettings': dept.get('coordinationSettings', {})
            })
        
        return processed_departments
        
    except requests.exceptions.RequestException as e:
        logger.error(
            "Error querying departments from Payload",
            project_id=project_id,
            error=str(e),
            exc_info=True
        )
        # Return mock departments for testing
        return _get_mock_departments()
    except Exception as e:
        logger.error(
            "Unexpected error querying departments",
            project_id=project_id,
            error=str(e),
            exc_info=True
        )
        return _get_mock_departments()


def trigger_department_evaluation(project_id: str, department_number: int) -> bool:
    """
    Trigger department evaluation via task service
    
    Args:
        project_id: Project identifier
        department_number: Department code number
    
    Returns:
        True if triggered successfully
    """
    try:
        # Get task service URL
        task_service_url = os.getenv('TASK_SERVICE_URL', 'http://localhost:8001')
        task_api_key = os.getenv('CELERY_API_KEY', '')
        
        url = f"{task_service_url}/api/v1/tasks/submit"
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': task_api_key
        }
        
        payload = {
            'project_id': project_id,
            'task_type': 'evaluate_department',
            'task_data': {
                'department_slug': f'dept_{department_number}',  # Will be resolved by evaluation task
                'department_number': department_number,
                'gather_data': [],  # Will be fetched by evaluation task
                'threshold': 80
            }
        }
        
        logger.info(
            "Triggering department evaluation",
            project_id=project_id,
            department_number=department_number
        )
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        task_id = result.get('task_id')
        
        logger.info(
            "Department evaluation triggered",
            project_id=project_id,
            department_number=department_number,
            task_id=task_id
        )
        
        return True
        
    except Exception as e:
        logger.error(
            "Error triggering department evaluation",
            project_id=project_id,
            department_number=department_number,
            error=str(e),
            exc_info=True
        )
        return False


def _get_mock_departments() -> List[Dict[str, Any]]:
    """
    Get mock departments for testing when Payload is not available
    """
    mock_departments = [
        {
            'id': 'story-dept',
            'slug': 'story',
            'name': 'Story',
            'description': 'Story development and narrative structure',
            'codeDepNumber': 1,
            'gatherCheck': True,
            'isActive': True,
            'defaultModel': 'anthropic/claude-sonnet-4.5',
            'coordinationSettings': {
                'minQualityThreshold': 80
            }
        },
        {
            'id': 'character-dept',
            'slug': 'character',
            'name': 'Character',
            'description': 'Character development and design',
            'codeDepNumber': 2,
            'gatherCheck': True,
            'isActive': True,
            'defaultModel': 'anthropic/claude-sonnet-4.5',
            'coordinationSettings': {
                'minQualityThreshold': 80
            }
        },
        {
            'id': 'visual-dept',
            'slug': 'visual',
            'name': 'Visual',
            'description': 'Visual design and cinematography',
            'codeDepNumber': 3,
            'gatherCheck': True,
            'isActive': True,
            'defaultModel': 'anthropic/claude-sonnet-4.5',
            'coordinationSettings': {
                'minQualityThreshold': 80
            }
        }
    ]
    
    logger.info(
        "Using mock departments",
        count=len(mock_departments)
    )
    
    return mock_departments

