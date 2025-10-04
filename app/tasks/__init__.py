"""
Task modules for AI Movie processing with brain service integration
"""
from .base_task import BaseTaskWithBrain
from .video_tasks import process_video_generation
from .image_tasks import process_image_generation
from .audio_tasks import process_audio_generation
from .evaluation_tasks import evaluate_department
from .automated_gather_tasks import automated_gather_creation

__all__ = [
    "BaseTaskWithBrain",
    "process_video_generation",
    "process_image_generation",
    "process_audio_generation",
    "evaluate_department",
    "automated_gather_creation"
]