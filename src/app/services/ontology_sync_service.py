import base64
import json
import logging
from typing import Callable, List, Optional

import weaviate

from src.app.core.config import settings
from src.app.services.indexing_service import IndexingService
from src.app.services.ontoportal_client import OntoPortalClient, OntologyRecord

logger = logging.getLogger(__name__)


class OntologySyncService:
    """
    Periodically synchronises ontologies from OntoPortal into the local RAG index.
    Detects new ontologies and updated submissions, ensuring the latest content is indexed.
    """

    def __init__(
        self,
        *,
        ontoportal_client: Optional[OntoPortalClient] = None,
        indexing_service: Optional[IndexingService] = None,
        task_dispatcher: Optional[Callable[..., object]] = None
    ):
        self._ontoportal_client = ontoportal_client
        self._indexing_service = indexing_service
        self._task_dispatcher = task_dispatcher

    @property
    def ontoportal_client(self) -> OntoPortalClient:
        if self._ontoportal_client is None:
            self._ontoportal_client = OntoPortalClient()
        return self._ontoportal_client

    @property
    def indexing_service(self) -> IndexingService:
        if self._indexing_service is None:
            self._indexing_service = IndexingService()
        return self._indexing_service

    @property
    def weaviate_client(self) -> weaviate.Client:
        return self.indexing_service.client

    def sync(self) -> dict:
        """
        Execute a full synchronisation cycle.
        """
        if not settings.ONTOLOGY_SYNC_ENABLED:
            logger.info("Ontology sync disabled via configuration; skipping cycle.")
            return {"status": "skipped", "reason": "disabled"}

        if not settings.ONTOPORTAL_API_KEY:
            logger.warning("ONTOPORTAL_API_KEY is not configured; skipping ontology sync.")
            return {"status": "skipped", "reason": "missing_api_key"}

        try:
            ontologies = self.ontoportal_client.fetch_latest_submissions()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to fetch OntoPortal ontologies: %s", exc, exc_info=True)
            return {"status": "error", "reason": "fetch_failed"}

        if not ontologies:
            logger.info("No ontologies returned from OntoPortal.")
            return {"status": "ok", "queued": 0}

        self.indexing_service.create_schema_if_not_exists()

        queued_jobs: List[dict] = []
        for ontology in ontologies:
            try:
                queued = self._process_ontology(ontology)
                if queued:
                    queued_jobs.append(queued)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("Failed to queue ingestion for ontology '%s': %s", ontology.acronym, exc, exc_info=True)

        logger.info("Ontology sync completed. %d ingestion jobs queued.", len(queued_jobs))
        return {"status": "ok", "queued": len(queued_jobs), "jobs": queued_jobs}

    def _process_ontology(self, ontology: OntologyRecord) -> Optional[dict]:
        """
        Determine whether an ontology requires indexing and dispatch the ingestion task if needed.
        """
        existing_version = self._get_current_version(ontology.acronym)
        if existing_version == ontology.version:
            logger.debug("Ontology '%s' already at latest version '%s'.", ontology.acronym, ontology.version)
            return None

        is_update = existing_version is not None

        payload = self.ontoportal_client.download_submission(ontology.download_url)
        encoded_file = base64.b64encode(payload).decode("utf-8")

        metadata = {
            "name": ontology.name,
            "acronym": ontology.acronym,
            "submission_id": ontology.submission_id,
            "source": ontology.download_url,
        }

        dispatcher = self._resolve_dispatcher()
        task = dispatcher(
            encoded_file=encoded_file,
            filename=f"{ontology.acronym}.owl",
            ontology_id=ontology.acronym,
            version=ontology.version,
            is_update=is_update,
            metadata_json=json.dumps(metadata)
        )

        logger.info(
            "Queued ingestion task '%s' for ontology '%s' (version %s, update=%s).",
            getattr(task, "id", "unknown"),
            ontology.acronym,
            ontology.version,
            is_update
        )

        return {
            "ontology_id": ontology.acronym,
            "version": ontology.version,
            "is_update": is_update,
            "task_id": getattr(task, "id", None)
        }

    def _resolve_dispatcher(self) -> Callable[..., object]:
        if self._task_dispatcher:
            return self._task_dispatcher

        from src.app.tasks.ontology_processor import process_ontology_task

        self._task_dispatcher = process_ontology_task.delay
        return self._task_dispatcher

    def _get_current_version(self, ontology_id: str) -> Optional[str]:
        """
        Inspect Weaviate to determine the version currently indexed for the given ontology.
        """
        where_filter = {
            "path": ["ontology_id"],
            "operator": "Equal",
            "valueString": ontology_id,
        }

        try:
            response = (
                self.weaviate_client.query
                .get(settings.WEAVIATE_CLASS_NAME, ["version"])
                .with_where(where_filter)
                .with_limit(1)
                .do()
            )
        except Exception as exc:
            logger.error("Failed to query Weaviate for ontology '%s': %s", ontology_id, exc, exc_info=True)
            return None

        data_section = response.get("data", {}).get("Get", {})
        entries = data_section.get(settings.WEAVIATE_CLASS_NAME, [])
        if not entries:
            return None

        version = entries[0].get("version")
        logger.debug("Current Weaviate version for ontology '%s' is '%s'.", ontology_id, version)
        return version
