import asyncio
import logging
from typing import Dict, Any, Optional

from .celery_config import celery_app
from src.services.ingestion_service import ResumeIngestionService
from src.logging_config import get_logger

logger = get_logger(__name__)

@celery_app.task(bind=True, name="src.worker.ingest_resume_task")
def ingest_resume_task(self, file_path: str, metadata: Optional[Dict[str, Any]] = None):
    """
    Celery task to ingest a single resume asynchronously.
    """
    logger.info("task_received", task_id=self.request.id, file_path=file_path)
    
    async def run_ingestion():
        service = ResumeIngestionService()
        return await service.ingest_single(file_path, metadata)

    try:
        # Run async service in sync worker
        result = asyncio.run(run_ingestion())
        
        if result.success:
            logger.info("task_succeeded", task_id=self.request.id, candidate=result.candidate_name)
            return {
                "status": "success",
                "candidate_name": result.candidate_name,
                "processing_time": result.processing_time,
                "file_path": result.file_path
            }
        else:
            logger.error("task_failed_logic", task_id=self.request.id, error=result.error)
            raise Exception(f"Ingestion failed: {result.error}")
            
    except Exception as e:
        logger.error("task_failed_exception", task_id=self.request.id, error=str(e))
        # Retry logic could be added here
        raise self.retry(exc=e, countdown=10, max_retries=3)
