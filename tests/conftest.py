import pytest
from fastapi.testclient import TestClient
from src.app.main import app

@pytest.fixture(scope="module")
def test_client():
    """
    Creates a FastAPI TestClient instance for the duration of the tests.
    """
    with TestClient(app) as client:
        yield client
