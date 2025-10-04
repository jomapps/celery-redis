"""
Automated Gather Creation Task
Dynamically processes all departments with gatherCheck=true
"""
import structlog
from typing import Dict, Any, List
from datetime import datetime
from celery.exceptions import SoftTimeLimitExceeded

from ..celery_app import celery_app
from ..agents.gather_content_generator import generate_content_batch
from ..agents.duplicate_detector import deduplicate_items
from ..agents.quality_analyzer import analyze_department_quality
from ..clients.mongodb_client import (
    read_gather_items,
    save_to_gather_db,
    get_gather_collection
)
from ..clients.brain_client import (
    get_brain_context,
    index_in_brain,
    get_department_context
)
from ..clients.payload_client import (
    query_departments_for_automation,
    trigger_department_evaluation
)
from ..clients.websocket_client import send_websocket_event

logger = structlog.get_logger(__name__)


@celery_app.task(
    bind=True,
    name='automated_gather_creation',
    soft_time_limit=540,  # 9 minutes
    time_limit=600,  # 10 minutes
    max_retries=3,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def automated_gather_creation(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main task for automated gather creation
    IMPORTANT: Handles dynamic departments (no hardcoded list)
    
    Args:
        task_data: {
            'project_id': str,
            'user_id': str,
            'max_iterations': int (default 50),
            'callback_url': str (optional)
        }
    
    Returns:
        {
            'status': 'completed',
            'iterations': int,
            'departments_processed': int,
            'items_created': int,
            'summary': List[Dict]
        }
    """
    project_id = task_data['project_id']
    user_id = task_data['user_id']
    max_iterations = task_data.get('max_iterations', 50)
    task_id = self.request.id
    
    logger.info(
        "Starting automated gather creation",
        project_id=project_id,
        user_id=user_id,
        task_id=task_id,
        max_iterations=max_iterations
    )
    
    try:
        # 1. Read existing gather items from MongoDB
        gather_items = read_gather_items(project_id)
        logger.info(
            "Loaded existing gather items",
            project_id=project_id,
            count=len(gather_items)
        )
        
        # 2. Get Brain context (semantic search)
        brain_context = get_brain_context(project_id)
        logger.info(
            "Loaded brain context",
            project_id=project_id,
            context_items=len(brain_context)
        )
        
        # 3. DYNAMIC: Query departments with gatherCheck=true, sorted by codeDepNumber
        departments = query_departments_for_automation(project_id)
        logger.info(
            "Loaded departments for automation",
            project_id=project_id,
            department_count=len(departments)
        )
        
        if not departments:
            logger.warning(
                "No departments with gatherCheck=true found",
                project_id=project_id
            )
            return {
                'status': 'completed',
                'iterations': 0,
                'departments_processed': 0,
                'items_created': 0,
                'message': 'No departments configured for automation'
            }
        
        # Send initial event
        send_websocket_event(project_id, {
            'type': 'automation_started',
            'task_id': task_id,
            'departments_count': len(departments),
            'max_iterations': max_iterations
        })
        
        total_iterations = 0
        processed_departments = []
        total_items_created = 0
        
        # Process each department sequentially
        for dept_index, dept in enumerate(departments):
            # Skip if gatherCheck is false (defensive check)
            if not dept.get('gatherCheck', False):
                logger.warning(
                    "Skipping department without gatherCheck",
                    department=dept.get('slug')
                )
                continue
            
            dept_slug = dept['slug']
            dept_name = dept.get('name', dept_slug)
            dept_number = dept.get('codeDepNumber', dept_index + 1)
            
            logger.info(
                "Processing department",
                department=dept_slug,
                department_name=dept_name,
                department_number=dept_number
            )
            
            dept_iterations = 0
            quality_score = 0
            dept_items_created = 0
            
            # Use department-specific threshold (default 80)
            threshold = dept.get('coordinationSettings', {}).get('minQualityThreshold', 80)
            
            # Use department-specific model
            model = dept.get('defaultModel', 'anthropic/claude-sonnet-4.5')
            
            # Send department started event
            send_websocket_event(project_id, {
                'type': 'department_started',
                'department': dept_slug,
                'department_name': dept_name,
                'department_number': dept_number,
                'threshold': threshold,
                'model': model,
                'total_iterations': total_iterations
            })
            
            # Iteration loop for this department
            while quality_score < threshold and total_iterations < max_iterations:
                try:
                    # Check for soft timeout
                    iteration_start = datetime.utcnow()
                    
                    logger.info(
                        "Starting iteration",
                        department=dept_slug,
                        iteration=dept_iterations + 1,
                        total_iterations=total_iterations + 1,
                        quality_score=quality_score,
                        threshold=threshold
                    )
                    
                    # Get context from ALL previously processed departments (cascading)
                    previous_dept_context = processed_departments.copy()
                    
                    # Get department-specific context from Brain
                    dept_brain_context = get_department_context(project_id, dept_slug)
                    
                    # Generate content batch using @codebuff/sdk
                    new_items = generate_content_batch(
                        project_id=project_id,
                        department=dept,
                        existing_context=gather_items + brain_context + dept_brain_context,
                        previous_departments=previous_dept_context,
                        model=model
                    )
                    
                    logger.info(
                        "Generated content batch",
                        department=dept_slug,
                        new_items_count=len(new_items)
                    )
                    
                    if not new_items:
                        logger.warning(
                            "No new items generated",
                            department=dept_slug,
                            iteration=dept_iterations + 1
                        )
                        break
                    
                    # Deduplicate (LLM-based, 90% similarity, keep newer)
                    send_websocket_event(project_id, {
                        'type': 'deduplicating',
                        'department': dept_slug,
                        'department_name': dept_name,
                        'items_to_check': len(new_items)
                    })
                    
                    deduplicated = deduplicate_items(new_items, gather_items, dept_slug)
                    
                    logger.info(
                        "Deduplicated items",
                        department=dept_slug,
                        original_count=len(new_items),
                        deduplicated_count=len(deduplicated),
                        duplicates_removed=len(new_items) - len(deduplicated)
                    )
                    
                    if not deduplicated:
                        logger.info(
                            "All items were duplicates, stopping iteration",
                            department=dept_slug
                        )
                        break
                    
                    # Save to MongoDB
                    saved_items = save_to_gather_db(
                        project_id=project_id,
                        items=deduplicated,
                        user_id=user_id,
                        automation_metadata={
                            'taskId': task_id,
                            'department': dept_slug,
                            'departmentName': dept_name,
                            'departmentNumber': dept_number,
                            'iteration': dept_iterations + 1,
                            'qualityScore': quality_score,
                            'model': model
                        }
                    )
                    
                    # Index in Brain (Neo4j with projectId isolation)
                    index_in_brain(project_id, saved_items, dept)
                    
                    # Update gather items list
                    gather_items.extend(saved_items)
                    dept_items_created += len(saved_items)
                    total_items_created += len(saved_items)
                    
                    # Check quality (department-specific scoring)
                    quality_score = analyze_department_quality(
                        project_id, dept, gather_items
                    )
                    
                    total_iterations += 1
                    dept_iterations += 1
                    
                    # Send iteration complete event
                    send_websocket_event(project_id, {
                        'type': 'iteration_complete',
                        'department': dept_slug,
                        'department_name': dept_name,
                        'iteration': dept_iterations,
                        'total_iterations': total_iterations,
                        'quality_score': quality_score,
                        'items_created': len(saved_items),
                        'threshold': threshold,
                        'max_iterations': max_iterations
                    })
                    
                    logger.info(
                        "Iteration complete",
                        department=dept_slug,
                        iteration=dept_iterations,
                        quality_score=quality_score,
                        items_created=len(saved_items)
                    )
                    
                except SoftTimeLimitExceeded:
                    logger.warning(
                        "Soft time limit exceeded, stopping gracefully",
                        department=dept_slug,
                        total_iterations=total_iterations
                    )
                    break
                except Exception as e:
                    logger.error(
                        "Error in iteration",
                        department=dept_slug,
                        iteration=dept_iterations + 1,
                        error=str(e),
                        exc_info=True
                    )
                    # Continue to next iteration
                    continue
            
            # Department complete - trigger evaluation
            try:
                trigger_department_evaluation(project_id, dept_number)
            except Exception as e:
                logger.error(
                    "Failed to trigger department evaluation",
                    department=dept_slug,
                    error=str(e)
                )
            
            # Store department results for next department's context
            processed_departments.append({
                'department': dept_slug,
                'name': dept_name,
                'number': dept_number,
                'quality_score': quality_score,
                'iterations': dept_iterations,
                'items_created': dept_items_created,
                'threshold': threshold,
                'model': model
            })
            
            # Send department complete event
            send_websocket_event(project_id, {
                'type': 'department_complete',
                'department': dept_slug,
                'department_name': dept_name,
                'quality_score': quality_score,
                'iterations_used': dept_iterations,
                'items_created': dept_items_created,
                'threshold': threshold
            })
            
            logger.info(
                "Department processing complete",
                department=dept_slug,
                quality_score=quality_score,
                iterations=dept_iterations,
                items_created=dept_items_created
            )
        
        # Final completion event
        send_websocket_event(project_id, {
            'type': 'automation_complete',
            'task_id': task_id,
            'total_iterations': total_iterations,
            'departments_processed': len(processed_departments),
            'items_created': total_items_created,
            'summary': processed_departments
        })
        
        logger.info(
            "Automated gather creation complete",
            project_id=project_id,
            task_id=task_id,
            total_iterations=total_iterations,
            departments_processed=len(processed_departments),
            items_created=total_items_created
        )
        
        return {
            'status': 'completed',
            'iterations': total_iterations,
            'departments_processed': len(processed_departments),
            'items_created': total_items_created,
            'summary': processed_departments
        }
        
    except SoftTimeLimitExceeded:
        logger.warning(
            "Task soft time limit exceeded",
            project_id=project_id,
            task_id=task_id
        )
        send_websocket_event(project_id, {
            'type': 'automation_timeout',
            'task_id': task_id,
            'message': 'Task exceeded time limit, partial results saved'
        })
        raise
        
    except Exception as e:
        logger.error(
            "Automated gather creation failed",
            project_id=project_id,
            task_id=task_id,
            error=str(e),
            exc_info=True
        )
        send_websocket_event(project_id, {
            'type': 'automation_error',
            'task_id': task_id,
            'error': str(e)
        })
        raise

