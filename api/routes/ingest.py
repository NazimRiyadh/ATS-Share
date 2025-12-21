"""
Ingest endpoints for resume upload and batch processing.
"""

import os
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, BackgroundTasks

from api.models import (
    IngestionResponse,
    AsyncIngestionResponse,
    BatchIngestionRequest,
    BatchIngestionResponse
)
from src.services.ingestion_service import ingest_resumes_from_directory
from src.worker import ingest_resume_task
from celery.result import AsyncResult
from src.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/ingest", tags=["Ingestion"])

# Upload directory
UPLOAD_DIR = Path("./data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("", response_model=AsyncIngestionResponse)
async def ingest_single_resume(
    file: UploadFile = File(...),
    candidate_name: Optional[str] = Form(None)
):
    """
    Upload and ingest a single resume file asynchronously.
    Returns a task_id to track progress.
    """
    start_time = datetime.now()
    
    # Validate file type
    allowed_extensions = {'.pdf', '.docx', '.txt', '.text'}
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {allowed_extensions}"
        )
    
    # Save uploaded file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"Saved upload: {file_path}")
        
        # Dispatch Celery task
        task = ingest_resume_task.delay(str(file_path), metadata={"candidate_name": candidate_name})
        
        return AsyncIngestionResponse(
            task_id=task.id,
            status="processing",
            message="Resume ingestion task submitted"
        )
            
    except Exception as e:
        logger.error(f"Upload/ingestion error: {e}")
        # Cleanup on failure
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """
    Check status of an ingestion task.
    """
    try:
        task_result = AsyncResult(task_id)
        
        response = {
            "task_id": task_id,
            "status": task_result.status,
            "result": task_result.result if task_result.ready() else None
        }
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=BatchIngestionResponse)
async def ingest_batch_resumes(request: BatchIngestionRequest):
    """
    Ingest all resumes from a directory.
    
    Processes files in batches for efficiency.
    """
    start_time = datetime.now()
    
    # Validate directory exists
    directory = Path(request.directory)
    if not directory.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Directory not found: {request.directory}"
        )
    
    if not directory.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Path is not a directory: {request.directory}"
        )
    
    try:
        result = await ingest_resumes_from_directory(
            directory=str(directory),
            batch_size=request.batch_size,
            force=request.force
        )
        
        # Collect failed file paths
        failed_files = [
            r.file_path for r in result.results
            if not r.success
        ]
        
        return BatchIngestionResponse(
            success=result.failed == 0,
            total_files=result.total_files,
            successful=result.successful,
            failed=result.failed,
            skipped=result.skipped,
            total_time=result.total_time,
            failed_files=failed_files
        )
        
    except Exception as e:
        logger.error(f"Batch ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def clear_uploads():
    """
    Clear all uploaded files (for testing/cleanup).
    """
    try:
        count = 0
        for file in UPLOAD_DIR.iterdir():
            if file.is_file():
                file.unlink()
                count += 1
        
        return {"message": f"Cleared {count} files from upload directory"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
