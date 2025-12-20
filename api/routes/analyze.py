"""
Job analysis endpoint for candidate shortlisting.
Uses LightRAG with hybrid search (BM25 + Vector) for accurate candidate scoring.

PRODUCTION HARDENING:
- MIN_CONFIDENCE threshold rejects low-score candidates
- Word boundary skill matching prevents false positives
- Evidence required for candidate inclusion
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException

from api.models import (
    JobAnalysisRequest,
    JobAnalysisResponse,
    CandidatePreview
)
from src.rag_config import get_rag
from src.reranker import rerank_func
from src.bm25_search import hybrid_search
from lightrag import QueryParam

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["Analysis"])

# ==================== PRODUCTION CONSTANTS ====================
# AUDIT FIX 1: Minimum confidence threshold - reject low-score candidates
MIN_CONFIDENCE = 0.3  # Candidates below 30% relevance are rejected

# AUDIT FIX 5: Minimum evidence requirement
MIN_SKILLS_FOR_EVIDENCE = 1  # At least 1 matched skill required (or high score)
HIGH_SCORE_THRESHOLD = 0.6  # Above this score, evidence requirement is relaxed

# Performance limits
MAX_CANDIDATES = 50  # Cap to prevent O(N) cross-encoder slowdown
# ==============================================================

# In-memory job context storage (use Redis/DB in production)
_job_contexts: Dict[str, Dict[str, Any]] = {}


def get_job_context(job_id: str) -> Dict[str, Any]:
    """Get stored job context."""
    return _job_contexts.get(job_id, {})


def store_job_context(job_id: str, context: Dict[str, Any]) -> None:
    """Store job context for later chat queries."""
    _job_contexts[job_id] = context


@router.post("", response_model=JobAnalysisResponse)
async def analyze_job(request: JobAnalysisRequest):
    """
    Analyze a job description and find top matching candidates.
    
    IMPROVED FLOW:
    1. Get raw context from LightRAG (vector + graph via mix mode)
    2. Extract resume chunks from context
    3. Re-rank chunks using cross-encoder with JD
    4. Parse and return candidates with REAL reranker scores
    
    Results are cached for subsequent chat queries.
    """
    start_time = datetime.now()
    
    try:
        # Get RAG instance
        rag = await get_rag()
        
        logger.info(f"Analyzing job: {request.job_id}")
        logger.info(f"Query: {request.query[:100]}...")
        
        # STEP 1: Get raw context using MIX mode (vector + knowledge graph)
        # only_need_context=True bypasses LLM to get raw retrieved chunks
        raw_context = await rag.aquery(
            request.query,
            param=QueryParam(mode="mix", only_need_context=True)
        )
        
        if not raw_context:
            logger.warning("No context retrieved from LightRAG")
            return JobAnalysisResponse(
                job_id=request.job_id,
                candidates_found=0,
                candidates=[],
                processing_time=(datetime.now() - start_time).total_seconds()
            )
        
        logger.info(f"Retrieved {len(raw_context)} chars of raw context")
        
        # STEP 2: Extract resume chunks from context
        resume_chunks = extract_resume_chunks(raw_context)
        logger.info(f"Extracted {len(resume_chunks)} resume chunks")
        
        if not resume_chunks:
            # Fallback: treat entire sections as chunks
            resume_chunks = [s.strip() for s in raw_context.split("\n\n") if s.strip() and len(s) > 100]
            logger.info(f"Fallback: Using {len(resume_chunks)} text sections")
        
        # STEP 3: HYBRID SEARCH - Combine BM25 (keyword) + Position-decay + Cross-Encoder
        # AUDIT FIX 4: Position-decay scores from LightRAG ordering (not true semantic similarity)
        # The cross-encoder reranker provides the real semantic scores
        # Weights adjusted: BM25 40% (primary keyword signal), Position 30%, Graph 30%
        
        if resume_chunks:
            # Position-decay scores: LightRAG returns chunks in relevance order
            # This is a known limitation - cross-encoder provides true semantic scores
            position_scores = [max(0.5, 1.0 - (i * 0.03)) for i in range(len(resume_chunks))]
            
            logger.info(f"Running hybrid search on {min(MAX_CANDIDATES, len(resume_chunks))} chunks")
            
            try:
                hybrid_results = await hybrid_search(
                    query=request.query,
                    documents=resume_chunks[:MAX_CANDIDATES],
                    vector_scores=position_scores[:MAX_CANDIDATES],  # Position-decay, not true vector
                    top_k=min(MAX_CANDIDATES, request.top_k * 2),
                    bm25_weight=0.4,   # AUDIT FIX 4: BM25 is primary keyword signal
                    vector_weight=0.3,  # Position-decay (lower weight)
                    graph_weight=0.3    # Knowledge graph context
                )
                logger.info(f"Hybrid search returned {len(hybrid_results)} results")
            except ImportError:
                logger.warning("BM25 not available, falling back to reranker only")
                hybrid_results = None
            
            # Second, refine with cross-encoder reranker for final scores
            if hybrid_results:
                docs_to_rerank = [r['content'] for r in hybrid_results]
            else:
                docs_to_rerank = resume_chunks[:MAX_CANDIDATES]
            
            reranked = await rerank_func(
                query=request.query,
                documents=docs_to_rerank,
                top_n=min(MAX_CANDIDATES, request.top_k * 2)
            )
            logger.info(f"Reranked {len(reranked)} chunks (max: {MAX_CANDIDATES})")
        else:
            reranked = []
        
        # STEP 4: Parse reranked results into candidates with real scores
        candidates = parse_reranked_to_candidates(reranked, request.top_k, request.query)
        logger.info(f"Parsed {len(candidates)} candidates")
        
        # Store context for chat queries
        store_job_context(request.job_id, {
            "query": request.query,
            "candidates": [c.dict() for c in candidates],
            "raw_context": raw_context[:5000],  # Store preview for chat
            "created_at": datetime.now().isoformat(),
            "top_k": request.top_k
        })
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return JobAnalysisResponse(
            job_id=request.job_id,
            candidates_found=len(candidates),
            candidates=candidates,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Job analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def extract_resume_chunks(context: str) -> List[str]:
    """
    Extract individual resume sections from LightRAG context.
    Returns list of resume text chunks.
    """
    chunks = []
    
    # Pattern 1: Look for "Resume: Name" markers
    resume_pattern = r'Resume:\s*([^\n]+)'
    matches = list(re.finditer(resume_pattern, context))
    
    if matches:
        # Extract text between resume markers
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i+1].start() if i+1 < len(matches) else len(context)
            chunk = context[start:end].strip()
            if len(chunk) > 100:  # Only meaningful chunks
                chunks.append(chunk)
        return chunks
    
    # Pattern 2: Look for content blocks in JSON-like structure
    content_pattern = r'"content":\s*"([^"]+)"'
    content_matches = re.findall(content_pattern, context)
    if content_matches:
        chunks = [c for c in content_matches if len(c) > 100]
        return chunks
    
    # Pattern 3: Split by document markers
    if "Document Chunks" in context:
        sections = context.split("Document Chunks")[1] if "Document Chunks" in context else context
        chunks = [s.strip() for s in sections.split("\n\n") if len(s.strip()) > 100]
    
    return chunks


def parse_reranked_to_candidates(
    reranked: List[dict],
    top_k: int,
    job_query: str = ""
) -> List[CandidatePreview]:
    """
    Parse reranked results into CandidatePreview objects.
    
    PRODUCTION HARDENED:
    - AUDIT FIX 1: Rejects candidates below MIN_CONFIDENCE threshold
    - AUDIT FIX 5: Requires evidence (matched skills) or very high score
    """
    candidates = []
    seen_names = set()
    rejected_low_score = 0
    rejected_no_evidence = 0
    
    # Extract key skills from job query for matching
    job_skills = extract_skills_from_text(job_query.lower())
    logger.info(f"Job skills extracted: {job_skills}")
    
    for item in reranked:
        if len(candidates) >= top_k:
            break
        
        content = item.get("content", "")
        score = item.get("relevance_score", 0.5)
        
        # Extract candidate name from content
        name = extract_candidate_name(content)
        
        # Skip duplicates
        if name.lower() in seen_names:
            continue
        seen_names.add(name.lower())
        
        # Normalize score to 0-1 range
        normalized_score = (score + 10) / 20  # Map [-10, 10] to [0, 1]
        normalized_score = max(0.0, min(1.0, normalized_score))
        
        # AUDIT FIX 1: Reject candidates below minimum confidence threshold
        if normalized_score < MIN_CONFIDENCE:
            rejected_low_score += 1
            logger.debug(f"Rejected {name}: score {normalized_score:.2f} < {MIN_CONFIDENCE}")
            continue
        
        # Extract skills from resume
        resume_skills = extract_skills_from_text(content.lower())
        
        # Find matching skills (intersection of job skills and resume skills)
        skills_matched = list(set(resume_skills) & set(job_skills)) if job_skills else resume_skills[:5]
        
        # AUDIT FIX 5: Require evidence (matched skills) OR very high score
        has_sufficient_evidence = len(skills_matched) >= MIN_SKILLS_FOR_EVIDENCE
        has_high_score = normalized_score >= HIGH_SCORE_THRESHOLD
        
        if not has_sufficient_evidence and not has_high_score:
            rejected_no_evidence += 1
            logger.debug(f"Rejected {name}: no skill evidence and score {normalized_score:.2f} < {HIGH_SCORE_THRESHOLD}")
            continue
        
        # Create concise match reason with explicit evidence
        match_reason = create_match_reason(content, skills_matched, normalized_score)
        
        # Extract brief experience summary
        experience_summary = extract_experience_summary(content)
        
        candidates.append(CandidatePreview(
            name=name,
            score=round(normalized_score, 3),
            match_reason=match_reason,
            skills_matched=skills_matched[:5],  # Top 5 matched skills
            experience_summary=experience_summary
        ))
    
    # Log rejection stats
    if rejected_low_score > 0 or rejected_no_evidence > 0:
        logger.info(f"Candidates rejected: {rejected_low_score} low score, {rejected_no_evidence} no evidence")
    
    # Sort by score descending
    candidates.sort(key=lambda c: c.score, reverse=True)
    
    return candidates


def extract_skills_from_text(text: str) -> List[str]:
    """
    Extract skills mentioned in text using WORD BOUNDARY matching.
    
    AUDIT FIX 2: Uses regex word boundaries to prevent false positives.
    Example: 'java' will NOT match 'javascript'
    """
    # Expanded skill list with variations
    common_skills = [
        # Programming languages
        "python", "java", "javascript", "typescript", "sql", "c\\+\\+", "c#", "go", "rust", "ruby", "php", "swift", "kotlin",
        # Cloud
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
        # Frameworks
        "react", "angular", "vue", "node\\.js", "django", "flask", "fastapi", "spring", "express",
        # Databases
        "postgresql", "mongodb", "redis", "mysql", "elasticsearch", "cassandra",
        # ML/AI
        "machine learning", "deep learning", "nlp", "tensorflow", "pytorch", "scikit-learn",
        # Data
        "data analysis", "data science", "pandas", "spark", "hadoop", "tableau", "power bi",
        # DevOps
        "ci/cd", "jenkins", "git", "linux", "ansible", "prometheus", "grafana",
        # Methodologies
        "agile", "scrum", "kanban",
        # APIs
        "rest api", "graphql", "microservices", "grpc"
    ]
    
    found = []
    text_lower = text.lower()
    
    for skill in common_skills:
        # AUDIT FIX 2: Use word boundary regex - prevents 'java' matching 'javascript'
        pattern = rf'\b{skill}\b'
        if re.search(pattern, text_lower, re.IGNORECASE):
            # Normalize display name
            display_name = skill.replace("\\+\\+", "++").replace("\\.", ".").title()
            if len(skill) <= 3:
                display_name = display_name.upper()  # SQL, AWS, GCP
            found.append(display_name)
    
    return found


def create_match_reason(content: str, matched_skills: List[str], score: float) -> str:
    """Create a concise reason why this candidate matches."""
    if not matched_skills:
        return f"Relevance score: {score:.0%}"
    
    if len(matched_skills) >= 3:
        return f"Strong match: {', '.join(matched_skills[:3])} + {len(matched_skills)-3} more"
    else:
        return f"Matches: {', '.join(matched_skills)}"


def extract_experience_summary(content: str) -> str:
    """Extract a brief, clean experience summary."""
    # Look for job title patterns
    role_patterns = [
        r'(Senior |Junior |Lead |Staff )?(Developer|Engineer|Analyst|Manager|Designer|Scientist|Architect)',
        r'(Python|Java|Full Stack|Frontend|Backend|Data|ML|AI|Software)\s+(Developer|Engineer)',
    ]
    
    for pattern in role_patterns:
        role_match = re.search(pattern, content, re.IGNORECASE)
        if role_match:
            role = role_match.group(0).strip()
            # Look for company nearby
            company_match = re.search(r'(?:at|@|-)\s*([A-Z][a-zA-Z\s]{2,20})', content[role_match.end():role_match.end()+100])
            if company_match:
                return f"{role} at {company_match.group(1).strip()}"[:60]
            return role[:40]
    
    # Look for years of experience
    exp_match = re.search(r'(\d+)\+?\s*years?\s*(of\s*)?(experience)?', content, re.IGNORECASE)
    if exp_match:
        return f"{exp_match.group(1)} years experience"
    
    return ""


def extract_candidate_name(content: str) -> str:
    """Extract candidate name from resume content (clean, short name only)."""
    
    def clean_name(raw_name: str) -> str:
        """Helper to clean up extracted names."""
        # Remove common prefixes/suffixes captured by regex
        lower = raw_name.lower()
        
        # Stop words that start the suffix we don't want
        stop_words = ["applying", "seeking", "interested", "looking", "resume", "cv", "profile"]
        words = raw_name.split()
        
        cleaned_words = []
        for w in words:
            if w.lower() in stop_words:
                break
            cleaned_words.append(w)
            
        # Remove "Candidate" prefix if present
        if cleaned_words and cleaned_words[0].lower() == "candidate":
            cleaned_words.pop(0)
            
        # Join and Title Case
        return " ".join(cleaned_words).title()

    name = "Unknown Candidate"
    
    # Pattern 0: Specific "resume for [Name]" intro common in dataset
    intro_match = re.search(r"here's a .*?resume for\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})", content, re.IGNORECASE)
    if intro_match:
        name = clean_name(intro_match.group(1))
        if 2 <= len(name.split()) <= 4:
            return name

    # Pattern 1: "Name: John Doe"
    name_match = re.search(r'Name:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})', content, re.IGNORECASE)
    if name_match:
        matches = clean_name(name_match.group(1))
        if 3 <= len(matches) <= 50:
            return matches
    
    # Pattern 2: Start of file (Strict Capitalization)
    lines = content.strip().split('\n')
    for line in lines[:3]:
        clean_line = re.sub(r'[#*\-_:.]', '', line).strip()
        words = clean_line.split()
        # Allow 2-4 words to catch "Candidate Name" then clean it
        if 2 <= len(words) <= 4 and all(w[0].isupper() and w.isalpha() for w in words):
            curr_name = ' '.join(words)
            # Filter headers
            if curr_name.lower() not in ["resume", "curriculum vitae", "candidate profile", "professional summary"]:
                cleaned = clean_name(curr_name)
                if cleaned and cleaned.lower() != "unknown candidate":
                    return cleaned
    
    # Pattern 3: Resume: marker
    resume_match = re.search(r'Resume:\s*\w+\s+([A-Z][a-z]+\s+[A-Z][a-z]+)', content, re.IGNORECASE)
    if resume_match:
        return clean_name(resume_match.group(1))
    
    return "Unknown Candidate"



@router.get("/{job_id}")
async def get_job_analysis(job_id: str):
    """
    Get stored job analysis results.
    """
    context = get_job_context(job_id)
    
    if not context:
        raise HTTPException(
            status_code=404,
            detail=f"Job analysis not found: {job_id}"
        )
    
    return {
        "job_id": job_id,
        "query": context.get("query", ""),
        "candidates_found": len(context.get("candidates", [])),
        "candidates": context.get("candidates", []),
        "created_at": context.get("created_at")
    }


@router.delete("/{job_id}")
async def delete_job_analysis(job_id: str):
    """
    Delete stored job analysis.
    """
    if job_id in _job_contexts:
        del _job_contexts[job_id]
        return {"message": f"Job analysis deleted: {job_id}"}
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Job analysis not found: {job_id}"
        )
