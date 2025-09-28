"""
Image processing tasks with brain service integration
Handles image generation, editing, and processing workflows
"""
from typing import Dict, Any, List
import structlog
from ..celery_app import celery_app
from .base_task import BaseTaskWithBrain

logger = structlog.get_logger(__name__)


class ImageGenerationTask(BaseTaskWithBrain):
    """Image generation task with brain service integration"""

    def execute_task(self, project_id: str, image_prompt: str,
                    image_params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute image generation with brain service context"""

        logger.info("Starting image generation",
                   project_id=project_id,
                   prompt_length=len(image_prompt))

        try:
            # Search for similar image generations in brain service
            similar_images = self.run_async_in_sync(
                self.search_similar_tasks_in_brain(
                    task_description=f"image generation {image_prompt}",
                    task_type="ImageGenerationTask",
                    limit=5
                )
            )

            # Get successful image generation patterns
            image_history = self.run_async_in_sync(
                self.get_task_history_from_brain("ImageGenerationTask", limit=10)
            )

            # Store execution context in brain service
            context = {
                "project_id": project_id,
                "image_prompt": image_prompt,
                "image_params": image_params,
                "similar_images_found": len(similar_images),
                "history_patterns": len(image_history)
            }

            self.run_async_in_sync(
                self.store_task_context_in_brain(self.request.id, context)
            )

            # Simulate image generation process
            result = {
                "task_id": self.request.id,
                "project_id": project_id,
                "image_url": f"https://media.ft.tc/images/{project_id}/{self.request.id}.jpg",
                "thumbnail_url": f"https://media.ft.tc/thumbnails/{project_id}/{self.request.id}_thumb.jpg",
                "prompt": image_prompt,
                "width": image_params.get('width', 1024),
                "height": image_params.get('height', 1024),
                "format": "jpg",
                "size_bytes": 2560000,  # ~2.5MB example
                "generation_time": 15,  # 15 seconds example
                "status": "completed",
                "quality_score": 0.94,
                "similar_images_used": len(similar_images),
                "generation_metadata": {
                    "model_version": "image-gen-v3.0",
                    "style": image_params.get('style', 'photorealistic'),
                    "guidance_scale": image_params.get('guidance_scale', 7.5),
                    "steps": image_params.get('steps', 50)
                }
            }

            logger.info("Image generation completed",
                       task_id=self.request.id,
                       image_url=result["image_url"])

            return result

        except Exception as e:
            logger.error("Image generation failed",
                        task_id=self.request.id,
                        error=str(e))
            raise


class ImageEditingTask(BaseTaskWithBrain):
    """Image editing task with brain service integration"""

    def execute_task(self, project_id: str, source_image_url: str,
                    edit_instructions: Dict[str, Any]) -> Dict[str, Any]:
        """Execute image editing with brain service context"""

        logger.info("Starting image editing",
                   project_id=project_id,
                   source_url=source_image_url)

        try:
            # Get editing patterns from brain service
            editing_patterns = self.run_async_in_sync(
                self.search_similar_tasks_in_brain(
                    task_description=f"image editing {edit_instructions.get('operation', '')}",
                    task_type="ImageEditingTask",
                    limit=3
                )
            )

            # Store execution context
            context = {
                "project_id": project_id,
                "source_image_url": source_image_url,
                "edit_instructions": edit_instructions,
                "editing_patterns_found": len(editing_patterns)
            }

            self.run_async_in_sync(
                self.store_task_context_in_brain(self.request.id, context)
            )

            # Simulate image editing process
            result = {
                "task_id": self.request.id,
                "project_id": project_id,
                "original_url": source_image_url,
                "edited_url": f"https://media.ft.tc/edited/{project_id}/{self.request.id}.jpg",
                "thumbnail_url": f"https://media.ft.tc/thumbnails/{project_id}/{self.request.id}_edited.jpg",
                "operations": edit_instructions.get('operations', []),
                "processing_time": 8,  # 8 seconds example
                "status": "completed",
                "quality_score": 0.91,
                "editing_metadata": {
                    "operations_count": len(edit_instructions.get('operations', [])),
                    "enhancement_level": edit_instructions.get('enhancement_level', 'medium'),
                    "patterns_used": len(editing_patterns)
                }
            }

            logger.info("Image editing completed",
                       task_id=self.request.id,
                       edited_url=result["edited_url"])

            return result

        except Exception as e:
            logger.error("Image editing failed",
                        task_id=self.request.id,
                        error=str(e))
            raise


class ImageBatchTask(BaseTaskWithBrain):
    """Batch image processing task with brain service integration"""

    def execute_task(self, project_id: str, image_requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute batch image processing with brain service optimization"""

        logger.info("Starting batch image processing",
                   project_id=project_id,
                   batch_size=len(image_requests))

        try:
            # Check for cached results for each image request
            cached_results = []
            pending_requests = []

            for i, request in enumerate(image_requests):
                cache_key = f"image_batch:{hash(str(request))}"
                cached_result = self.run_async_in_sync(
                    self.get_cached_result_from_brain(cache_key)
                )

                if cached_result:
                    cached_results.append((i, cached_result))
                else:
                    pending_requests.append((i, request))

            # Store batch execution context
            context = {
                "project_id": project_id,
                "total_requests": len(image_requests),
                "cached_results": len(cached_results),
                "pending_requests": len(pending_requests)
            }

            self.run_async_in_sync(
                self.store_task_context_in_brain(self.request.id, context)
            )

            # Process pending requests
            processed_results = []
            for i, request in pending_requests:
                # Simulate individual image processing
                processed_result = {
                    "index": i,
                    "image_url": f"https://media.ft.tc/batch/{project_id}/{self.request.id}_{i}.jpg",
                    "thumbnail_url": f"https://media.ft.tc/thumbnails/{project_id}/{self.request.id}_{i}.jpg",
                    "status": "completed",
                    "processing_time": 5,
                    "quality_score": 0.89
                }
                processed_results.append((i, processed_result))

                # Cache the result
                cache_key = f"image_batch:{hash(str(request))}"
                self.run_async_in_sync(
                    self.cache_result_in_brain(cache_key, processed_result, ttl_seconds=3600)
                )

            # Combine cached and processed results
            all_results = {}
            for i, result in cached_results + processed_results:
                all_results[i] = result

            result = {
                "task_id": self.request.id,
                "project_id": project_id,
                "batch_size": len(image_requests),
                "processed_count": len(processed_results),
                "cached_count": len(cached_results),
                "total_processing_time": len(processed_results) * 5,
                "status": "completed",
                "results": all_results,
                "batch_metadata": {
                    "cache_hit_rate": len(cached_results) / len(image_requests),
                    "processing_optimization": f"Saved {len(cached_results) * 5} seconds via caching"
                }
            }

            logger.info("Batch image processing completed",
                       task_id=self.request.id,
                       processed=len(processed_results),
                       cached=len(cached_results))

            return result

        except Exception as e:
            logger.error("Batch image processing failed",
                        task_id=self.request.id,
                        error=str(e))
            raise


# Create Celery task instances using the concrete classes
@celery_app.task(bind=True, base=ImageGenerationTask, queue='gpu_medium')
def process_image_generation(self, project_id: str, image_prompt: str,
                           image_params: Dict[str, Any]) -> Dict[str, Any]:
    """Generate images with brain service knowledge integration"""
    return self.execute_task(project_id, image_prompt, image_params)


@celery_app.task(bind=True, base=ImageEditingTask, queue='cpu_intensive')
def process_image_editing(self, project_id: str, source_image_url: str,
                        edit_instructions: Dict[str, Any]) -> Dict[str, Any]:
    """Edit and enhance existing images"""
    return self.execute_task(project_id, source_image_url, edit_instructions)


@celery_app.task(bind=True, base=ImageBatchTask, queue='cpu_intensive')
def process_image_batch(self, project_id: str, image_requests: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Process multiple images in batch with brain service optimization"""
    return self.execute_task(project_id, image_requests)