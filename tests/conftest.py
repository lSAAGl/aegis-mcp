import pytest
from fastapi.testclient import TestClient
from src.app.main import app

@pytest.fixture
def app_client():
    """Test client for FastAPI app"""
    return TestClient(app)