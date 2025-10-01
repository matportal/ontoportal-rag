import logging
import base64
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from src.app.schemas.models import IngestionResponse
from src.app.tasks.ontology_processor import process_ontology_task

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post(
    "/ingest_ontology",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def ingest_ontology(
    ontology_file: UploadFile = File(..., description="The ontology file (e.g., in OWL/RDF format)."),
    ontology_id: str = Form(..., description="A unique identifier for the ontology."),
    version: str = Form(..., description="The version of the ontology."),
    is_update: bool = Form(False, description="Set to true to delete existing data for this ontology_id before ingestion."),
    # metadata is received as a string, we'll handle it in the task
    metadata_json: str = Form("{}", description="Optional JSON string for additional metadata.")
):
    """
    Asynchronously ingest and process an ontology file.

    This endpoint accepts an ontology file and its metadata, saves the file
    temporarily, and dispatches a background task to process and index it.
    """
    if not ontology_file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    try:
        file_bytes = await ontology_file.read()
        encoded_file = base64.b64encode(file_bytes).decode("utf-8")
        logger.info(f"Received ontology file '{ontology_file.filename}' for ontology_id: {ontology_id}")

        # Dispatch the background task
        task = process_ontology_task.delay(
            encoded_file=encoded_file,
            filename=ontology_file.filename,
            ontology_id=ontology_id,
            version=version,
            is_update=is_update,
            metadata_json=metadata_json # Pass metadata as a string
        )

        return IngestionResponse(
            task_id=task.id,
            message="Ontology ingestion has been successfully started."
        )

    except Exception as e:
        logger.error(f"Failed to start ingestion task for ontology {ontology_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while starting the ingestion process: {e}"
        )
