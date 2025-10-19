from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.app.core.config import settings
from src.app.services.ontoportal_client import OntologyRecord
from src.app.services.ontology_sync_service import OntologySyncService


@pytest.fixture(autouse=True)
def restore_settings():
    original_enabled = settings.ONTOLOGY_SYNC_ENABLED
    original_key = settings.ONTOPORTAL_API_KEY
    original_interval = settings.ONTOLOGY_SYNC_INTERVAL_MINUTES
    try:
        yield
    finally:
        settings.ONTOLOGY_SYNC_ENABLED = original_enabled
        settings.ONTOPORTAL_API_KEY = original_key
        settings.ONTOLOGY_SYNC_INTERVAL_MINUTES = original_interval


def make_weaviate_client(response_payload):
    query_builder = MagicMock()
    query_builder.with_where.return_value = query_builder
    query_builder.with_limit.return_value = query_builder
    query_builder.do.return_value = response_payload

    query = MagicMock()
    query.get.return_value = query_builder

    client = MagicMock()
    client.query = query
    return client


def test_sync_skips_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "ONTOLOGY_SYNC_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "ONTOPORTAL_API_KEY", "test-key", raising=False)

    service = OntologySyncService(
        ontoportal_client=MagicMock(),
        indexing_service=MagicMock()
    )

    result = service.sync()

    assert result == {"status": "skipped", "reason": "disabled"}


def test_sync_queues_new_ontology(monkeypatch):
    monkeypatch.setattr(settings, "ONTOLOGY_SYNC_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "ONTOPORTAL_API_KEY", "test-key", raising=False)

    record = OntologyRecord(
        acronym="TEST",
        name="Test Ontology",
        submission_id=1,
        version="1.0",
        download_url="https://rest.matportal.org/ontologies/TEST/submissions/1/download"
    )

    ontoportal_client = MagicMock()
    ontoportal_client.fetch_latest_submissions.return_value = [record]
    ontoportal_client.download_submission.return_value = b"dummy data"

    indexing_service = MagicMock()
    indexing_service.create_schema_if_not_exists.return_value = None
    indexing_service.client = make_weaviate_client({
        "data": {"Get": {settings.WEAVIATE_CLASS_NAME: []}}
    })

    dispatched_calls = []

    def dispatcher(**kwargs):
        dispatched_calls.append(kwargs)
        return SimpleNamespace(id="task-1")

    service = OntologySyncService(
        ontoportal_client=ontoportal_client,
        indexing_service=indexing_service,
        task_dispatcher=dispatcher
    )

    result = service.sync()

    assert result["status"] == "ok"
    assert result["queued"] == 1
    assert dispatched_calls[0]["ontology_id"] == "TEST"
    assert dispatched_calls[0]["is_update"] is False


def test_sync_marks_updates(monkeypatch):
    monkeypatch.setattr(settings, "ONTOLOGY_SYNC_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "ONTOPORTAL_API_KEY", "test-key", raising=False)

    record = OntologyRecord(
        acronym="TEST",
        name="Test Ontology",
        submission_id=2,
        version="2.0",
        download_url="https://rest.matportal.org/ontologies/TEST/submissions/2/download"
    )

    ontoportal_client = MagicMock()
    ontoportal_client.fetch_latest_submissions.return_value = [record]
    ontoportal_client.download_submission.return_value = b"dummy data"

    existing_payload = {
        "data": {
            "Get": {
                settings.WEAVIATE_CLASS_NAME: [
                    {"version": "1.0"}
                ]
            }
        }
    }

    indexing_service = MagicMock()
    indexing_service.create_schema_if_not_exists.return_value = None
    indexing_service.client = make_weaviate_client(existing_payload)

    dispatched_calls = []

    def dispatcher(**kwargs):
        dispatched_calls.append(kwargs)
        return SimpleNamespace(id="task-2")

    service = OntologySyncService(
        ontoportal_client=ontoportal_client,
        indexing_service=indexing_service,
        task_dispatcher=dispatcher
    )

    result = service.sync()

    assert result["status"] == "ok"
    assert result["queued"] == 1
    assert dispatched_calls[0]["ontology_id"] == "TEST"
    assert dispatched_calls[0]["is_update"] is True
