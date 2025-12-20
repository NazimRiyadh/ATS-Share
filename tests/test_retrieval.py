"""
Retrieval system tests.
"""

import pytest


class TestResumeParser:
    """Test resume parsing functionality."""
    
    def test_extract_candidate_name_from_content(self):
        """Test name extraction from resume content."""
        from src.resume_parser import extract_candidate_name
        
        content = "John Smith\nSoftware Engineer\nExperience..."
        name = extract_candidate_name(content, "resume.pdf")
        
        assert name == "John Smith"
    
    def test_extract_candidate_name_fallback(self):
        """Test name extraction falls back to filename."""
        from src.resume_parser import extract_candidate_name
        
        content = "## Experience\n- Company A\n- Company B"
        name = extract_candidate_name(content, "john_doe_resume.pdf")
        
        assert "John Doe" in name or "john" in name.lower()


class TestDualRetrieval:
    """Test dual-level retrieval components."""
    
    def test_fallback_chain_order(self):
        """Test fallback chain is in correct order."""
        from src.dual_retrieval import DualLevelRetrieval
        
        expected_chain = ["mix", "hybrid", "local", "naive"]
        assert DualLevelRetrieval.FALLBACK_CHAIN == expected_chain
    
    def test_candidate_context_creation(self):
        """Test CandidateContext dataclass."""
        from src.dual_retrieval import CandidateContext
        
        candidate = CandidateContext(
            name="John Smith",
            content="Python developer with 5 years experience",
            score=0.95,
            metadata={"source": "resume.pdf"}
        )
        
        assert candidate.name == "John Smith"
        assert candidate.score == 0.95
        assert "Python" in candidate.content


class TestReranker:
    """Test reranking functionality."""
    
    def test_rerank_returns_sorted_results(self):
        """Test that reranker returns sorted results."""
        from src.reranker import rerank_func_sync
        
        query = "Python developer"
        documents = [
            "Chef specializing in French cuisine",
            "Senior Python developer with 10 years experience",
            "JavaScript frontend developer"
        ]
        
        results = rerank_func_sync(query, documents, top_k=3)
        
        # Should return list of tuples
        assert len(results) == 3
        assert all(len(r) == 3 for r in results)  # (index, score, doc)
        
        # Results should be sorted by score descending
        scores = [r[1] for r in results]
        assert scores == sorted(scores, reverse=True)
        
        # Python developer should rank higher than chef
        python_rank = next(i for i, r in enumerate(results) if "Python" in r[2])
        chef_rank = next(i for i, r in enumerate(results) if "Chef" in r[2])
        assert python_rank < chef_rank
