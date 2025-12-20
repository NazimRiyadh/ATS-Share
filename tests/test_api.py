"""
API endpoint tests using FastAPI TestClient.
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile


# Skip tests if dependencies not available
pytest.importorskip("fastapi")


@pytest.fixture
def client():
    """Create test client."""
    from api.main import app
    return TestClient(app)


class TestRootEndpoints:
    """Test root and health endpoints."""
    
    def test_root(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
    
    def test_health(self, client):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data
    
    def test_stats(self, client):
        """Test stats endpoint."""
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_documents" in data


class TestChatEndpoints:
    """Test chat endpoints."""
    
    def test_get_modes(self, client):
        """Test retrieval modes endpoint."""
        response = client.get("/chat/modes")
        assert response.status_code == 200
        data = response.json()
        assert "modes" in data
        assert "naive" in data["modes"]
        assert "mix" in data["modes"]


class TestIngestEndpoints:
    """Test ingestion endpoints."""
    
    def test_ingest_invalid_file_type(self, client):
        """Test ingestion rejects invalid file types."""
        # Create a temp file with invalid extension
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"test content")
            temp_path = f.name
        
        try:
            with open(temp_path, "rb") as f:
                response = client.post(
                    "/ingest",
                    files={"file": ("test.xyz", f, "application/octet-stream")}
                )
            assert response.status_code == 400
        finally:
            Path(temp_path).unlink()
    
    def test_batch_ingest_missing_directory(self, client):
        """Test batch ingest with non-existent directory."""
        response = client.post(
            "/ingest/batch",
            json={"directory": "/nonexistent/path"}
        )
        assert response.status_code == 400


class TestAnalyzeEndpoints:
    """Test analysis endpoints."""
    
    def test_get_nonexistent_job(self, client):
        """Test getting analysis for non-existent job."""
        response = client.get("/analyze/nonexistent-job-id")
        assert response.status_code == 404
    
    def test_delete_nonexistent_job(self, client):
        """Test deleting analysis for non-existent job."""
        response = client.delete("/analyze/nonexistent-job-id")
        assert response.status_code == 404
