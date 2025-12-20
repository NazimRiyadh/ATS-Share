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
    BatchIngestionRequest,
    BatchIngestionResponse
)
from src.ingestion import ingest_resume, ingest_resumes_from_directory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["Ingestion"])

# Upload directory
UPLOAD_DIR = Path("./data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("", response_model=IngestionResponse)
async def ingest_single_resume(
    file: UploadFile = File(...),
    candidate_name: Optional[str] = Form(None)
):
    """
    Upload and ingest a single resume file.
    
    Supports PDF, DOCX, and TXT formats.
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
        
        # Ingest the resume
        try:
            result = await ingest_resume(str(file_path))
        except Exception as e:
            logger.error(f"Ingestion exception: {e}", exc_info=True)
            # Cleanup on failure
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=500,
                detail=f"Ingestion failed with exception: {str(e)}"
            )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        if result.success:
            return IngestionResponse(
                success=True,
                message="Resume ingested successfully",
                file_path=str(file_path),
                candidate_name=candidate_name or result.candidate_name,
                processing_time=processing_time
            )
        else:
            # Cleanup on failure
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=500,
                detail=f"Ingestion failed: {result.error}"
            )
            
    except Exception as e:
        logger.error(f"Upload/ingestion error: {e}")
        # Cleanup on failure
        if file_path.exists():
            file_path.unlink()
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
