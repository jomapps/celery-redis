"""
Monitoring and metrics configuration for Celery task queue
Provides metrics collection, logging, and alerting capabilities
"""
import structlog
from typing import Dict, Any, Optional
from datetime import datetime
from celery.signals import (
    task_prerun,
    task_postrun,
    task_failure,
    task_retry,
    task_revoked,
    worker_ready,
    worker_shutdown
)

logger = structlog.get_logger(__name__)


# Task metrics storage (in-memory for now, can be replaced with Redis/Prometheus)
task_metrics = {
    "total_tasks": 0,
    "completed_tasks": 0,
    "failed_tasks": 0,
    "retried_tasks": 0,
    "cancelled_tasks": 0,
    "task_durations": {},
    "task_start_times": {},
}


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **extra):
    """
    Called before task execution
    Records task start time and logs task start
    """
    task_metrics["total_tasks"] += 1
    task_metrics["task_start_times"][task_id] = datetime.utcnow()
    
    logger.info(
        "Task started",
        task_id=task_id,
        task_name=task.name if task else sender,
        args=args,
        kwargs=kwargs
    )


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, 
                        retval=None, state=None, **extra):
    """
    Called after task execution (success or failure)
    Records task duration and completion metrics
    """
    if task_id in task_metrics["task_start_times"]:
        start_time = task_metrics["task_start_times"][task_id]
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        task_name = task.name if task else sender
        if task_name not in task_metrics["task_durations"]:
            task_metrics["task_durations"][task_name] = []
        
        task_metrics["task_durations"][task_name].append(duration)
        
        # Clean up start time
        del task_metrics["task_start_times"][task_id]
        
        logger.info(
            "Task completed",
            task_id=task_id,
            task_name=task_name,
            duration=duration,
            state=state
        )
    
    if state == 'SUCCESS':
        task_metrics["completed_tasks"] += 1


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, 
                        kwargs=None, traceback=None, einfo=None, **extra):
    """
    Called when task fails
    Records failure metrics and logs error details
    """
    task_metrics["failed_tasks"] += 1
    
    logger.error(
        "Task failed",
        task_id=task_id,
        task_name=sender.name if sender else "unknown",
        exception=str(exception),
        traceback=str(traceback) if traceback else None,
        args=args,
        kwargs=kwargs
    )
    
    # Check if this is automated_gather_creation task for special alerting
    if sender and hasattr(sender, 'name') and sender.name == 'automated_gather_creation':
        logger.critical(
            "ALERT: automated_gather_creation task failed",
            task_id=task_id,
            exception=str(exception),
            requires_attention=True
        )


@task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **extra):
    """
    Called when task is retried
    Records retry metrics and logs retry reason
    """
    task_metrics["retried_tasks"] += 1
    
    logger.warning(
        "Task retry scheduled",
        task_id=task_id,
        task_name=sender.name if sender else "unknown",
        reason=str(reason),
        retry_count=task_metrics["retried_tasks"]
    )


@task_revoked.connect
def task_revoked_handler(sender=None, request=None, terminated=None, 
                        signum=None, expired=None, **extra):
    """
    Called when task is revoked/cancelled
    Records cancellation metrics
    """
    task_metrics["cancelled_tasks"] += 1
    
    task_id = request.id if request else "unknown"
    
    logger.warning(
        "Task revoked",
        task_id=task_id,
        task_name=sender.name if sender else "unknown",
        terminated=terminated,
        expired=expired,
        signal=signum
    )


@worker_ready.connect
def worker_ready_handler(sender=None, **extra):
    """
    Called when worker is ready to accept tasks
    """
    logger.info(
        "Worker ready",
        hostname=sender.hostname if sender else "unknown",
        concurrency=sender.concurrency if sender else None
    )


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **extra):
    """
    Called when worker is shutting down
    """
    logger.info(
        "Worker shutting down",
        hostname=sender.hostname if sender else "unknown"
    )


def get_task_metrics() -> Dict[str, Any]:
    """
    Get current task metrics
    
    Returns:
        Dictionary containing task metrics
    """
    # Calculate average durations
    avg_durations = {}
    for task_name, durations in task_metrics["task_durations"].items():
        if durations:
            avg_durations[task_name] = sum(durations) / len(durations)
    
    return {
        "total_tasks": task_metrics["total_tasks"],
        "completed_tasks": task_metrics["completed_tasks"],
        "failed_tasks": task_metrics["failed_tasks"],
        "retried_tasks": task_metrics["retried_tasks"],
        "cancelled_tasks": task_metrics["cancelled_tasks"],
        "success_rate": (
            task_metrics["completed_tasks"] / task_metrics["total_tasks"] * 100
            if task_metrics["total_tasks"] > 0 else 0
        ),
        "failure_rate": (
            task_metrics["failed_tasks"] / task_metrics["total_tasks"] * 100
            if task_metrics["total_tasks"] > 0 else 0
        ),
        "average_durations": avg_durations,
        "currently_running": len(task_metrics["task_start_times"])
    }


def reset_task_metrics():
    """
    Reset task metrics (useful for testing)
    """
    task_metrics["total_tasks"] = 0
    task_metrics["completed_tasks"] = 0
    task_metrics["failed_tasks"] = 0
    task_metrics["retried_tasks"] = 0
    task_metrics["cancelled_tasks"] = 0
    task_metrics["task_durations"] = {}
    task_metrics["task_start_times"] = {}


def check_task_health() -> Dict[str, Any]:
    """
    Check task queue health and return status
    
    Returns:
        Dictionary containing health status and alerts
    """
    metrics = get_task_metrics()
    alerts = []
    
    # Check failure rate
    if metrics["failure_rate"] > 20:
        alerts.append({
            "severity": "critical",
            "message": f"High failure rate: {metrics['failure_rate']:.2f}%",
            "metric": "failure_rate",
            "value": metrics["failure_rate"]
        })
    elif metrics["failure_rate"] > 10:
        alerts.append({
            "severity": "warning",
            "message": f"Elevated failure rate: {metrics['failure_rate']:.2f}%",
            "metric": "failure_rate",
            "value": metrics["failure_rate"]
        })
    
    # Check for long-running tasks (> 8 minutes for automated_gather_creation)
    for task_id, start_time in task_metrics["task_start_times"].items():
        duration = (datetime.utcnow() - start_time).total_seconds()
        if duration > 480:  # 8 minutes
            alerts.append({
                "severity": "warning",
                "message": f"Task {task_id} running for {duration:.0f} seconds",
                "metric": "task_duration",
                "value": duration,
                "task_id": task_id
            })
    
    # Determine overall health status
    if any(alert["severity"] == "critical" for alert in alerts):
        health_status = "critical"
    elif any(alert["severity"] == "warning" for alert in alerts):
        health_status = "warning"
    else:
        health_status = "healthy"
    
    return {
        "status": health_status,
        "metrics": metrics,
        "alerts": alerts,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

