import logging
from dataclasses import dataclass
from typing import Iterator, List, Optional

import requests
from requests import Response

from src.app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class OntologyRecord:
    """
    Lightweight representation of an OntoPortal ontology and its latest submission.
    """
    acronym: str
    name: str
    submission_id: int
    version: str
    download_url: str
    ontology_iri: Optional[str] = None


class OntoPortalClient:
    """
    Thin REST client tailored to the OntoPortal REST API.
    Handles authentication, pagination, and extraction of the latest ontology submissions.
    """

    def __init__(self, session: Optional[requests.Session] = None):
        self.base_url = settings.ONTOPORTAL_API_BASE_URL.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = 60

        # Configure authentication headers when an API key is available.
        if settings.ONTOPORTAL_API_KEY:
            self.session.headers.update({
                "Authorization": f"apikey token={settings.ONTOPORTAL_API_KEY}"
            })
        self.session.headers.setdefault("Accept", "application/json")

    def fetch_latest_submissions(self) -> List[OntologyRecord]:
        """
        Retrieve all ontologies and resolve their latest submissions.

        Returns:
            List[OntologyRecord]: A list with the essential data required for downstream processing.
        """
        records: List[OntologyRecord] = []
        for ontology in self._iterate_ontologies():
            if ontology.get("viewOf"):
                continue  # Skip ontology views; they mirror a primary ontology.

            acronym = ontology.get("acronym")
            name = ontology.get("name") or acronym
            if not acronym:
                logger.debug("Skipping ontology without an acronym: %s", ontology)
                continue

            latest_submission_url = self._extract_link(ontology, "latest_submission")
            if not latest_submission_url:
                logger.debug("No latest submission link for ontology '%s'", acronym)
                continue

            submission = self._get_latest_submission(latest_submission_url)
            if not submission:
                continue

            download_url = self._extract_link(submission, "download")
            if not download_url:
                logger.debug("No download link for ontology '%s' submission '%s'", acronym, submission)
                continue

            submission_id = submission.get("submissionId")
            if submission_id is None:
                logger.debug("Submission for ontology '%s' missing submissionId: %s", acronym, submission)
                continue

            version = submission.get("version") or str(submission_id)

            record = OntologyRecord(
                acronym=acronym,
                name=name,
                submission_id=submission_id,
                version=version,
                download_url=download_url,
                ontology_iri=ontology.get("@id")
            )
            records.append(record)

        logger.info("Discovered %d ontologies with downloadable submissions.", len(records))
        return records

    def download_submission(self, download_url: str) -> bytes:
        """
        Download the ontology file associated with a submission.
        """
        response = self._request("GET", download_url, stream=True)
        content = response.content
        logger.debug("Downloaded %d bytes from %s", len(content), download_url)
        return content

    def _iterate_ontologies(self) -> Iterator[dict]:
        """
        Iterate through all ontologies using OntoPortal pagination semantics.
        """
        page = 1
        page_size = 200

        while True:
            params = {
                "page": page,
                "pagesize": page_size,
                "include": "acronym,name,viewOf,links"
            }
            try:
                response = self._request("GET", "/ontologies", params=params)
            except requests.HTTPError as exc:
                logger.error("Failed to fetch ontologies (page %s): %s", page, exc, exc_info=True)
                break

            payload = self._parse_json(response)
            items = self._extract_collection(payload)
            if not items:
                break

            for ontology in items:
                yield ontology

            if len(items) < page_size:
                break
            page += 1

    def _get_latest_submission(self, latest_submission_url: str) -> Optional[dict]:
        """
        Resolve the JSON payload of the latest submission for an ontology.
        """
        try:
            response = self._request("GET", latest_submission_url)
        except requests.HTTPError as exc:
            logger.error("Failed to fetch latest submission from %s: %s", latest_submission_url, exc, exc_info=True)
            return None

        return self._parse_json(response)

    def _request(self, method: str, url: str, params: Optional[dict] = None, stream: bool = False) -> Response:
        """
        Issue an HTTP request, resolving relative paths against the configured base URL.
        """
        target_url = url if url.startswith("http") else f"{self.base_url}{url}"
        response = self.session.request(
            method=method,
            url=target_url,
            params=params,
            timeout=self.timeout,
            stream=stream
        )
        response.raise_for_status()
        return response

    @staticmethod
    def _parse_json(response: Response) -> dict:
        try:
            return response.json()
        except ValueError:
            logger.error("Response from %s was not valid JSON.", response.url, exc_info=True)
            raise

    @staticmethod
    def _extract_collection(payload: dict) -> List[dict]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            if "collection" in payload and isinstance(payload["collection"], list):
                return payload["collection"]
            if "ontologies" in payload and isinstance(payload["ontologies"], list):
                return payload["ontologies"]
        logger.debug("Unexpected payload format when extracting ontology collection: %s", payload)
        return []

    @staticmethod
    def _extract_link(payload: dict, rel: str) -> Optional[str]:
        links = payload.get("links") or {}
        url = links.get(rel)
        if url:
            return url
        payload_id = payload.get("@id")
        if payload_id:
            candidate = f"{payload_id.rstrip('/')}/{rel}"
            return candidate
        return None
