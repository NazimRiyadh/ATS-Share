"""
Resume ingestion pipeline with batch processing and progress tracking.
"""

import os
import logging
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from tqdm import tqdm

from .resume_parser import parse_resume, get_resume_files, extract_candidate_name
from .rag_config import get_rag

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result of ingesting a single resume."""
    file_path: str
    candidate_name: str
    success: bool
    error: Optional[str] = None
    processing_time: float = 0.0


import hashlib
import json

@dataclass
class BatchIngestionResult:
    """Result of batch ingestion."""
    total_files: int
    successful: int
    failed: int
    skipped: int = 0  # Added skipped count
    results: List[IngestionResult] = field(default_factory=list)
    total_time: float = 0.0


class ResumeIngestion:
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
                logger.warning(f"Failed to load ingestion state: {e}")
        return {}
        
    def _save_state(self):
        """Save ingestion state to file."""
        self.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.STATE_FILE, "w") as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save ingestion state: {e}")
            
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
                if not hasattr(self._rag, '_storage_lock') or self._rag._storage_lock is None:
                    logger.warning("RAG storages may not be initialized, re-initializing...")
                    await self._rag.initialize_storages()
                logger.debug("RAG instance verified and ready")
            except Exception as e:
                logger.error(f"Failed to initialize RAG: {e}")
                raise RuntimeError(f"RAG initialization failed: {e}") from e
        return self._rag
    
    async def ingest_single(
        self,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IngestionResult:
        """
        Ingest a single resume file.
        
        Args:
            file_path: Path to resume file
            metadata: Optional metadata to attach
            
        Returns:
            IngestionResult with status
        """
        start_time = datetime.now()
        
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
            
            # Verify RAG is ready
            if rag is None:
                raise RuntimeError("RAG instance is None")
            
            logger.debug(f"Ingesting document for {candidate_name} (length: {len(doc_content)} chars)")
            
            # Ingest into LightRAG (just pass the text content)
            try:
                await rag.ainsert(doc_content)
                logger.debug(f"Successfully called ainsert for {candidate_name}")
            except KeyError as e:
                if 'history_messages' in str(e):
                    logger.error("LightRAG history_messages KeyError - pipeline status not initialized")
                    raise RuntimeError(
                        "LightRAG pipeline status not properly initialized. "
                        "This may indicate a bug in LightRAG or missing initialization step."
                    ) from e
                raise
            except Exception as e:
                logger.error(f"Error during ainsert: {type(e).__name__}: {e}")
                raise
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"✅ Ingested: {candidate_name} ({file_type}) in {processing_time:.2f}s")
            
            return IngestionResult(
                file_path=file_path,
                candidate_name=candidate_name,
                success=True,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ Failed to ingest {file_path}: {e}")
            
            return IngestionResult(
                file_path=file_path,
                candidate_name="Unknown",
                success=False,
                error=str(e),
                processing_time=processing_time
            )
    
    async def ingest_batch(
        self,
        directory: str,
        batch_size: int = 5,
        show_progress: bool = True,
        force: bool = False
    ) -> BatchIngestionResult:
        """
        Ingest all resumes from a directory in batches.
        
        Args:
            directory: Directory containing resume files
            batch_size: Number of files to process concurrently
            show_progress: Show progress bar
            force: Force re-ingestion of all files
            
        Returns:
            BatchIngestionResult with summary
        """
        start_time = datetime.now()
        
        # Get all resume files
        files = get_resume_files(directory)
        
        if not files:
            return BatchIngestionResult(
                total_files=0,
                successful=0,
                failed=0,
                skipped=0
            )
            
        # Filter files based on state if not forced
        files_to_process = []
        skipped_count = 0
        
        # Pre-calculate hashes/check state for all files
        # This might take a moment for many files but saves expensive ingestion
        if not force:
            logger.info("Checking file states for incremental ingestion...")
            for f in files:
                try:
                    file_hash = self._calculate_file_hash(f)
                    file_key = str(Path(f).name) # Use filename as key
                    
                    if file_key in self._state:
                        last_state = self._state[file_key]
                        if last_state.get('hash') == file_hash and last_state.get('success', False):
                            skipped_count += 1
                            continue
                            
                    files_to_process.append((f, file_hash))
                except Exception as e:
                    logger.warning(f"Error checking state for {f}: {e}")
                    files_to_process.append((f, None))
        else:
            files_to_process = [(f, None) for f in files]
            
        if not files_to_process and skipped_count > 0:
            logger.info(f"All {skipped_count} files already up to date. Nothing to ingest.")
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
        
        # Create progress bar
        pbar = tqdm(total=len(files_to_process), desc="Ingesting resumes", disable=not show_progress)
        
        # Process in batches
        for i in range(0, len(files_to_process), batch_size):
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
                
                # If we didn't calculate hash earlier (force mode), do it now for saving state
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
                    # Update state as failed
                    self._state[file_key] = {
                        'hash': current_hash,
                        'success': False,
                        'last_ingested': datetime.now().isoformat(),
                        'error': err_msg
                    }
                elif result.success:
                    successful += 1
                    results.append(result)
                    # Update state as success
                    self._state[file_key] = {
                        'hash': current_hash,
                        'success': True,
                        'last_ingested': datetime.now().isoformat(),
                        'candidate_name': result.candidate_name
                    }
                else:
                    failed += 1
                    results.append(result)
                    # Update state as failed
                    self._state[file_key] = {
                        'hash': current_hash,
                        'success': False,
                        'last_ingested': datetime.now().isoformat(),
                        'error': result.error or "Unknown error"
                    }
                
                pbar.update(1)
            
            # Save state periodically
            self._save_state()
        
        pbar.close()
        
        total_time = (datetime.now() - start_time).total_seconds()
        
        # Log summary
        logger.info(
            f"\n📊 Ingestion Summary:\n"
            f"  Total: {len(files)}\n"
            f"  ⏭️ Skipped: {skipped_count}\n"
            f"  ✅ Successful: {successful}\n"
            f"  ❌ Failed: {failed}\n"
            f"  ⏱️ Time: {total_time:.2f}s\n"
        )
        if successful + failed > 0:
             logger.info(f"  📈 Rate: {(successful + failed)/total_time:.2f} files/sec")
        
        return BatchIngestionResult(
            total_files=len(files),
            successful=successful,
            failed=failed,
            skipped=skipped_count,
            results=results,
            total_time=total_time
        )


# Convenience functions
async def ingest_resume(file_path: str) -> IngestionResult:
    """Ingest a single resume file."""
    ingestion = ResumeIngestion()
    return await ingestion.ingest_single(file_path)


async def ingest_resumes_from_directory(
    directory: str,
    batch_size: int = 5,
    force: bool = False
) -> BatchIngestionResult:
    """Ingest all resumes from a directory."""
    ingestion = ResumeIngestion()
    return await ingestion.ingest_batch(directory, batch_size, force=force)

