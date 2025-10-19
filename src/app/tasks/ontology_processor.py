import base64
import logging
import json
import pathlib
import shutil
import subprocess
import tempfile
from langchain.text_splitter import MarkdownHeaderTextSplitter
try:
    from pylode2 import OntDoc
except ImportError:  # pragma: no cover - fallback for environments still using pylode v2 package name
    from pylode import OntDoc
from rdflib import Graph
from rdflib.util import guess_format

from src.app.worker import celery_app
from src.app.services.indexing_service import IndexingService
from src.app.services.ontology_sanitizer import OntologySanitizer


def _load_graph_with_fallbacks(path: pathlib.Path) -> Graph:
    """Attempt to parse an ontology file using multiple RDF serializations."""
    sanitizer = OntologySanitizer()
    try:
        candidate_paths = sanitizer.sanitize(path)
        last_exception = None

        for candidate_path in candidate_paths:
            suffixes = [s.lower() for s in candidate_path.suffixes]
            if ".ttl" in suffixes:
                g = Graph()
                try:
                    logger.info("Attempting to parse %s as turtle (ttl fast-path)", candidate_path)
                    g.parse(str(candidate_path), format="turtle")
                    logger.info("Successfully parsed ontology using 'turtle' format (file: %s).", candidate_path.name)
                    return g
                except Exception as exc:
                    last_exception = exc
                    logger.debug("Fast-path turtle parse failed for %s: %s", candidate_path, exc)

            candidate_formats = _detect_candidate_formats(candidate_path)

            for fmt in candidate_formats:
                g = Graph()
                try:
                    logger.info("Attempting to parse %s as %s", candidate_path, fmt)
                    g.parse(str(candidate_path), format=fmt)
                    logger.info("Successfully parsed ontology using '%s' format (file: %s).", fmt, candidate_path.name)
                    return g
                except Exception as exc:
                    last_exception = exc
                    logger.debug("Failed to parse %s as %s: %s", candidate_path, fmt, exc)

        if last_exception:
            logger.error(
                "Unable to parse ontology file %s even after sanitation pipeline. Last error: %s",
                path,
                last_exception
            )
            raise last_exception

        raise ValueError(f"Unable to determine format for ontology file {path}")
    finally:
        sanitizer.cleanup()


def _detect_candidate_formats(path: pathlib.Path) -> list[str]:
    candidate_formats: list[str] = []

    guessed = guess_format(path.name)
    if guessed:
        candidate_formats.append(guessed)

    try:
        head = path.read_text(encoding="utf-8", errors="ignore")[:500].lower()
    except Exception:  # pragma: no cover
        head = ""

    if head.lstrip().startswith("<?xml"):
        candidate_formats.append("xml")
    if "@prefix" in head or head.lstrip().startswith("prefix"):
        candidate_formats.append("turtle")
    if head.lstrip().startswith("{\"@context\""):
        candidate_formats.append("json-ld")

    candidate_formats.extend(["xml", "turtle", "n3", "nt", "trig"])

    seen = set()
    ordered_formats = []
    for fmt in candidate_formats:
        if fmt and fmt not in seen:
            seen.add(fmt)
            ordered_formats.append(fmt)
    suffixes = [s.lower() for s in path.suffixes]
    if "turtle" in ordered_formats and ".ttl" in suffixes and "xml" in ordered_formats:
        ordered_formats = [fmt for fmt in ordered_formats if fmt != "xml"]

    return ordered_formats


logger = logging.getLogger(__name__)

@celery_app.task(name="process_ontology_task", bind=True)
def process_ontology_task(
    self,
    encoded_file: str,
    filename: str,
    ontology_id: str,
    version: str,
    is_update: bool,
    metadata_json: str
):
    """
    Celery task to process and index an ontology file.
    This task orchestrates the ingestion process by using dedicated services.
    """
    logger.info(f"Starting processing for ontology_id: {ontology_id}, task_id: {self.request.id}")
    temp_dir_path = pathlib.Path(tempfile.mkdtemp())
    temp_file_path = temp_dir_path / (filename or "ontology.owl")

    try:
        # Recreate the uploaded file from the encoded payload
        file_bytes = base64.b64decode(encoded_file)
        temp_file_path.write_bytes(file_bytes)

        # 1. Initialize the Indexing Service
        indexing_service = IndexingService()
        indexing_service.create_schema_if_not_exists()

        # 2. Handle updates by deleting existing data
        if is_update:
            indexing_service.delete_by_ontology_id(ontology_id)

        # 3. Convert ontology to Markdown using pylode
        logger.info("Converting ontology to Markdown with pylode...")
        logger.info("Loading ontology into RDF graph...")
        g = _load_graph_with_fallbacks(temp_file_path)
        doc = OntDoc(g=g, source_info=str(temp_file_path), outputformat="md")
        markdown_content = doc.generate_document()
        logger.info("Conversion to Markdown successful.")

        # 4. Chunk the Markdown document
        logger.info("Chunking Markdown document with LangChain...")
        headers_to_split_on = [("#", "Header 1"), ("##", "Header 2"), ("###", "Header 3")]
        splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        chunks = splitter.split_text(markdown_content)
        logger.info(f"Split document into {len(chunks)} chunks.")

        # 5. Batch index chunks using the IndexingService
        parsed_metadata = json.loads(metadata_json)
        chunks_indexed = indexing_service.batch_index_chunks(
            chunks=chunks,
            ontology_id=ontology_id,
            version=version,
            metadata=parsed_metadata,
            task_id=self.request.id
        )

        return {"status": "success", "chunks_indexed": chunks_indexed}

    except Exception as e:
        logger.error(f"Error processing ontology {ontology_id}: {e}", exc_info=True)
        self.update_state(state='FAILURE', meta={'exc_type': type(e).__name__, 'exc_message': str(e)})
        raise e
    finally:
        # 6. Clean up the temporary directory and file
        logger.info(f"Cleaning up temporary directory: {temp_dir_path}")
        if temp_dir_path.exists():
            shutil.rmtree(temp_dir_path)
        logger.info("Cleanup complete.")
