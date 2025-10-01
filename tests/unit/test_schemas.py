import pytest
from pydantic import ValidationError
from src.app.schemas.models import QueryRequest, QueryResponse, SourceChunk

def test_query_request_valid():
    """Tests that a valid QueryRequest model is parsed correctly."""
    data = {"query": "What is an ontology?"}
    req = QueryRequest(**data)
    assert req.query == "What is an ontology?"

def test_query_request_invalid_missing_field():
    """Tests that QueryRequest raises a validation error for missing fields."""
    with pytest.raises(ValidationError):
        QueryRequest()

def test_query_request_invalid_empty_query():
    """Tests that QueryRequest raises a validation error for an empty query if we add such validation."""
    # Pydantic by default allows empty strings. If we added a validator(..., allow_blank=False)
    # this test would be useful. For now, it shows the default behavior.
    data = {"query": ""}
    req = QueryRequest(**data)
    assert req.query == ""

def test_query_response_valid():
    """Tests that a valid QueryResponse model is parsed correctly."""
    data = {
        "answer": "An ontology is a formal representation of knowledge.",
        "sources": [
            {
                "ontology_id": "test_onto",
                "version": "1.0",
                "content": "Some chunk content.",
                "metadata": {"header": "Introduction"}
            }
        ]
    }
    resp = QueryResponse(**data)
    assert resp.answer == "An ontology is a formal representation of knowledge."
    assert len(resp.sources) == 1
    assert isinstance(resp.sources[0], SourceChunk)
    assert resp.sources[0].ontology_id == "test_onto"
