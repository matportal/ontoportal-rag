import pytest
from unittest.mock import MagicMock, patch
from io import BytesIO

from src.app.schemas.models import QueryResponse, SourceChunk

# Fixture to mock the celery task
@pytest.fixture
def mock_celery_task(monkeypatch):
    """Mocks the .delay method of the celery task."""
    mock_delay = MagicMock()
    # Configure the mock to return an object that has an 'id' attribute
    mock_delay.return_value.id = "mock-task-id-12345"
    monkeypatch.setattr("src.app.tasks.ontology_processor.process_ontology_task.delay", mock_delay)
    return mock_delay

# Fixture to mock the retrieval service
@pytest.fixture
def mock_retrieval_service(monkeypatch):
    mock = MagicMock()
    mock.answer_query.return_value = QueryResponse(
        answer="This is a mocked answer.",
        sources=[
            SourceChunk(
                ontology_id="mock_id",
                version="1.0",
                content="mock content",
                metadata={"header": "mock header"}
            )
        ]
    )
    # Patch the entire class
    monkeypatch.setattr("src.app.api.endpoints.query.RetrievalService", lambda: mock)
    return mock


def test_health_check(test_client):
    """Tests the root health check endpoint."""
    response = test_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Welcome to ONTO-RAG-V1"}

def test_ingest_ontology_endpoint(test_client, mock_celery_task):
    """Tests the /ingest_ontology endpoint."""
    # Create an in-memory "file"
    ontology_content = b"<rdf:RDF>some ontology data</rdf:RDF>"
    file_data = {"ontology_file": ("test.owl", BytesIO(ontology_content), "application/rdf+xml")}

    form_data = {
        "ontology_id": "test-ontology",
        "version": "1.1",
        "is_update": "false",
        "metadata_json": '{"domain": "test"}'
    }

    response = test_client.post("/api/v1/ingest_ontology", data=form_data, files=file_data)

    assert response.status_code == 202
    json_response = response.json()
    assert "task_id" in json_response
    assert json_response["message"] == "Ontology ingestion has been successfully started."

    # Assert that our mocked celery task was called
    mock_celery_task.assert_called_once()
    # We can also inspect the arguments it was called with
    args, kwargs = mock_celery_task.call_args
    assert kwargs['ontology_id'] == "test-ontology"
    assert kwargs['version'] == "1.1"
    assert not kwargs['is_update']
    assert '"domain": "test"' in kwargs['metadata']

def test_query_endpoint(test_client, mock_retrieval_service):
    """Tests the /query endpoint with a mocked retrieval service."""
    query_data = {"query": "What is a test?"}

    response = test_client.post("/api/v1/query", json=query_data)

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["answer"] == "This is a mocked answer."
    assert len(json_response["sources"]) == 1
    assert json_response["sources"][0]["ontology_id"] == "mock_id"

    # Assert that the service's answer_query method was called with the correct query
    mock_retrieval_service.answer_query.assert_called_once_with("What is a test?")
