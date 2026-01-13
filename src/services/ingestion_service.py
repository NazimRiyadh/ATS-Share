"""
Resume ingestion service layer.
Handles batch processing, state management, and RAG interaction.
Decoupled from UI/CLI (uses callbacks for progress).
"""

import os
import asyncio
import hashlib
import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime

from src.logging_config import get_logger
from src.resume_parser import parse_resume, get_resume_files, extract_candidate_name
from src.rag_config import get_rag

logger = get_logger(__name__)


@dataclass
class IngestionResult:
    """Result of ingesting a single resume."""
    file_path: str
    candidate_name: str
    success: bool
    error: Optional[str] = None
    processing_time: float = 0.0


@dataclass
class BatchIngestionResult:
    """Result of batch ingestion."""
    total_files: int
    successful: int
    failed: int
    skipped: int = 0
    results: List[IngestionResult] = field(default_factory=list)
    total_time: float = 0.0


class ResumeIngestionService:
    """Handles resume ingestion into LightRAG."""
    
    STATE_FILE = Path("data/ingestion_state.json")
    
    def __init__(self):
        self._rag = None
        self._state = self._load_state()
        
    def _load_state(self) -> Dict[str, Any]:
        """Load ingestion state from file."""
        if self.STATE_FILE.exists():
            try:
                with open(self.STATE_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("failed_load_state", error=str(e))
        return {}
        
    def _save_state(self):
        """Save ingestion state to file."""
        self.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.STATE_FILE, "w") as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            logger.warning("failed_save_state", error=str(e))
            
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read and update hash string value in blocks of 4K
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    async def _ensure_rag(self):
        """Ensure RAG is initialized."""
        if self._rag is None:
            try:
                self._rag = await get_rag()
                # Verify RAG is properly initialized
                if self._rag is None:
                    raise RuntimeError("RAG instance is None after initialization")
                # Verify storages are initialized
                # Accessing private member for verification is acceptable in service layer
                if not hasattr(self._rag, '_storage_lock') or self._rag._storage_lock is None:
                    logger.warning("rag_storages_not_initialized", action="re-initializing")
                    await self._rag.initialize_storages()
                logger.debug("rag_instance_verified")
            except Exception as e:
                logger.error("rag_initialization_failed", error=str(e))
                raise RuntimeError(f"RAG initialization failed: {e}") from e
        return self._rag
    
    async def ingest_single(
        self,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IngestionResult:
        """
        Ingest a single resume file.
        """
        start_time = datetime.now()
        candidate_name = "Unknown"
        
        try:
            # Parse resume
            content, file_type = parse_resume(file_path)
            
            if not content.strip():
                return IngestionResult(
                    file_path=file_path,
                    candidate_name="Unknown",
                    success=False,
                    error="Empty content after parsing"
                )
            
            # Extract candidate name
            candidate_name = extract_candidate_name(content, file_path)
            
            # Prepare document with metadata
            doc_content = f"# Resume: {candidate_name}\n\n{content}"
            
            # Get RAG instance
            rag = await self._ensure_rag()
            
            logger.debug("ingesting_document", candidate=candidate_name, length=len(doc_content))
            
            # Ingest into LightRAG
            try:
                # Pass file_path explicitly for source tracking
                await rag.ainsert(doc_content, file_paths=file_path)
                logger.debug("ainsert_success", candidate=candidate_name)
            except KeyError as e:
                if 'history_messages' in str(e):
                    logger.error("lightrag_pipeline_error", error="KeyError: history_messages")
                    raise RuntimeError(
                        "LightRAG pipeline status not properly initialized. "
                        "This may indicate a bug in LightRAG or missing initialization step."
                    ) from e
                raise
            except Exception as e:
                logger.error("ainsert_failed", error=str(e), type=type(e).__name__)
                raise
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info("ingestion_success", candidate=candidate_name, file_type=file_type, duration=processing_time)
            
            return IngestionResult(
                file_path=file_path,
                candidate_name=candidate_name,
                success=True,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error("ingestion_failed", file=file_path, error=str(e))
            
            return IngestionResult(
                file_path=file_path,
                candidate_name=candidate_name,
                success=False,
                error=str(e),
                processing_time=processing_time
            )
    
    async def ingest_batch(
        self,
        directory: str,
        batch_size: int = 5,
        force: bool = False,
        on_progress: Optional[Callable[[int], None]] = None
    ) -> BatchIngestionResult:
        """
        Ingest all resumes from a directory in batches.
        
        Args:
            directory: Directory containing resume files
            batch_size: Number of files to process concurrently
            force: Force re-ingestion of all files
            on_progress: Callback function(increment) called after each file
        """
        start_time = datetime.now()
        
        # Get all resume files
        files = get_resume_files(directory)
        
        if not files:
            return BatchIngestionResult(0, 0, 0, 0)
            
        # Filter files based on state if not forced
        files_to_process = []
        skipped_count = 0
        
        # Pre-calculate hashes/check state
        if not force:
            logger.info("checking_file_states", count=len(files))
            for f in files:
                try:
                    file_hash = self._calculate_file_hash(f)
                    file_key = str(Path(f).name)
                    
                    if file_key in self._state:
                        last_state = self._state[file_key]
                        if last_state.get('hash') == file_hash and last_state.get('success', False):
                            skipped_count += 1
                            continue
                            
                    files_to_process.append((f, file_hash))
                except Exception as e:
                    logger.warning("state_check_error", file=f, error=str(e))
                    files_to_process.append((f, None))
        else:
            files_to_process = [(f, None) for f in files]
            
        if not files_to_process and skipped_count > 0:
            logger.info("all_files_up_to_date", skipped=skipped_count)
            return BatchIngestionResult(
                total_files=len(files),
                successful=0,
                failed=0,
                skipped=skipped_count,
                total_time=(datetime.now() - start_time).total_seconds()
            )
        
        results = []
        successful = 0
        failed = 0
        
        # Process in batches
        total_to_process = len(files_to_process)
        logger.info("starting_batch_ingestion", count=total_to_process, batch_size=batch_size)
        
        for i in range(0, total_to_process, batch_size):
            batch_items = files_to_process[i:i + batch_size]
            batch_files = [item[0] for item in batch_items]
            
            # Process batch concurrently
            batch_results = await asyncio.gather(
                *[self.ingest_single(f) for f in batch_files],
                return_exceptions=True
            )
            
            for j, result in enumerate(batch_results):
                current_file, current_hash = batch_items[j]
                file_key = str(Path(current_file).name)
                
                # Update hash if needed
                if current_hash is None:
                    try:
                        current_hash = self._calculate_file_hash(current_file)
                    except:
                        pass

                if isinstance(result, Exception):
                    failed += 1
                    err_msg = str(result)
                    results.append(IngestionResult(
                        file_path=current_file,
                        candidate_name="Unknown",
                        success=False,
                        error=err_msg
                    ))
                    self._state[file_key] = {
                        'hash': current_hash,
                        'success': False,
                        'last_ingested': datetime.now().isoformat(),
                        'error': err_msg
                    }
                elif result.success:
                    successful += 1
                    results.append(result)
                    self._state[file_key] = {
                        'hash': current_hash,
                        'success': True,
                        'last_ingested': datetime.now().isoformat(),
                        'candidate_name': result.candidate_name
                    }
                else:
                    failed += 1
                    results.append(result)
                    self._state[file_key] = {
                        'hash': current_hash,
                        'success': False,
                        'last_ingested': datetime.now().isoformat(),
                        'error': result.error or "Unknown error"
                    }
                
                if on_progress:
                    on_progress(1)
            
            # Save state periodically
            self._save_state()
        
        total_time = (datetime.now() - start_time).total_seconds()
        
        logger.info("batch_ingestion_complete", 
                   total=len(files), 
                   skipped=skipped_count, 
                   successful=successful, 
                   failed=failed, 
                   duration=total_time)
        
        return BatchIngestionResult(
            total_files=len(files),
            successful=successful,
            failed=failed,
            skipped=skipped_count,
            results=results,
            total_time=total_time
        )


# Convenience functions (Facades)
async def ingest_resume(file_path: str) -> IngestionResult:
    """Ingest a single resume file."""
    service = ResumeIngestionService()
    return await service.ingest_single(file_path)


async def ingest_resumes_from_directory(
    directory: str,
    batch_size: int = 5,
    force: bool = False,
    on_progress: Optional[Callable[[int], None]] = None
) -> BatchIngestionResult:
    """Ingest all resumes from a directory."""
    service = ResumeIngestionService()
    return await service.ingest_batch(directory, batch_size, force=force, on_progress=on_progress)
