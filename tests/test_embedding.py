"""
Embedding model tests.
"""

import pytest
import numpy as np


class TestEmbeddingModel:
    """Test embedding functionality."""
    
    def test_embedding_single_text(self):
        """Test embedding a single text."""
        from src.embedding import embedding_func_sync
        
        text = "Python developer with 5 years experience"
        embeddings = embedding_func_sync(text)
        
        assert isinstance(embeddings, np.ndarray)
        assert len(embeddings.shape) == 2
        assert embeddings.shape[0] == 1  # Single text
        assert embeddings.shape[1] == 1024  # BGE-M3 dimension
    
    def test_embedding_multiple_texts(self):
        """Test embedding multiple texts."""
        from src.embedding import embedding_func_sync
        
        texts = [
            "Python developer",
            "JavaScript engineer",
            "Data scientist"
        ]
        embeddings = embedding_func_sync(texts)
        
        assert embeddings.shape[0] == 3
        assert embeddings.shape[1] == 1024
    
    def test_embedding_similarity(self):
        """Test that similar texts have higher similarity."""
        from src.embedding import embedding_func_sync
        
        texts = [
            "Python software developer",
            "Python programming engineer",
            "Chef at restaurant"
        ]
        embeddings = embedding_func_sync(texts)
        
        # Compute cosine similarities
        python_sim = np.dot(embeddings[0], embeddings[1])
        unrelated_sim = np.dot(embeddings[0], embeddings[2])
        
        # Similar texts should have higher similarity
        assert python_sim > unrelated_sim
