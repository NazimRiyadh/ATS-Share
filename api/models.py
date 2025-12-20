"""
Pydantic models for API request/response schemas.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============== Request Models ==============

class ResumeUploadRequest(BaseModel):
    """Request for single resume upload (metadata only, file sent separately)."""
    candidate_name: Optional[str] = Field(None, description="Optional candidate name override")
    tags: Optional[List[str]] = Field(default_factory=list, description="Optional tags for categorization")


class BatchIngestionRequest(BaseModel):
    """Request for batch resume ingestion."""
    directory: str = Field(..., description="Directory containing resume files")
    batch_size: int = Field(default=5, ge=1, le=20, description="Processing batch size")
    recursive: bool = Field(default=True, description="Search subdirectories")
    force: bool = Field(default=False, description="Force re-ingestion of all files")


class JobAnalysisRequest(BaseModel):
    """Request for job-based candidate analysis."""
    query: str = Field(..., min_length=10, description="Job description or requirements")
    job_id: str = Field(..., description="Unique job identifier")
    top_k: int = Field(default=20, ge=1, le=100, description="Number of candidates to shortlist")


class JobChatRequest(BaseModel):
    """Request for conversational chat about candidates."""
    job_id: str = Field(..., description="Job ID to query about")
    message: str = Field(..., min_length=1, description="User question or message")
    mode: str = Field(
        default="mix",
        description="Retrieval mode: naive, local, global, hybrid, mix"
    )


class DirectQueryRequest(BaseModel):
    """Request for direct RAG query without job context."""
    query: str = Field(..., min_length=1, description="Query text")
    mode: str = Field(default="mix", description="Retrieval mode")


# ============== Response Models ==============

class CandidatePreview(BaseModel):
    """Brief candidate information with matching evidence."""
    name: str = Field(..., description="Candidate name")
    score: float = Field(..., description="Match score (0-1)")
    match_reason: str = Field(default="", description="Why this candidate matches")
    skills_matched: List[str] = Field(default_factory=list, description="Skills matching JD")
    experience_summary: str = Field(default="", description="Brief experience summary")



class CandidateDetail(BaseModel):
    """Detailed candidate information."""
    name: str
    score: float
    content_preview: str
    skills: List[str] = Field(default_factory=list)
    experience_years: Optional[int] = None
    highlights: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IngestionResponse(BaseModel):
    """Response for single resume ingestion."""
    success: bool
    message: str
    file_path: str
    candidate_name: str
    processing_time: float


class BatchIngestionResponse(BaseModel):
    """Response for batch ingestion."""
    success: bool
    total_files: int
    successful: int
    failed: int
    skipped: int = 0
    total_time: float
    failed_files: List[str] = Field(default_factory=list)


class JobAnalysisResponse(BaseModel):
    """Response for job analysis."""
    job_id: str
    candidates_found: int
    candidates: List[CandidatePreview]
    processing_time: float


class ChatResponse(BaseModel):
    """Response for chat queries."""
    response: str
    mode_used: str
    fallback_used: bool = False
    sources: Dict[str, Any] = Field(default_factory=dict)
    processing_time: float


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    components: Dict[str, bool]
    timestamp: str


class StatsResponse(BaseModel):
    """System statistics response."""
    total_documents: int
    total_chunks: int
    last_ingestion: Optional[str] = None
    database_status: Dict[str, str]


# ============== Error Models ==============

class ErrorDetail(BaseModel):
    """Error detail information."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: ErrorDetail
