from pydantic import BaseModel, Field
from typing import List, Dict, Any

# ============================================================================
# Ingestion Models
# ============================================================================

class IngestionResponse(BaseModel):
    """
    Response model for the /ingest_ontology endpoint.
    Confirms that the task has been received and is being processed.
    """
    task_id: str = Field(..., description="The ID of the background task processing the ontology.")
    status: str = Field("processing", description="The status of the ingestion task.")
    message: str = Field("Ontology ingestion started.", description="A confirmation message.")


# ============================================================================
# Query Models
# ============================================================================

class SourceChunk(BaseModel):
    """
    Represents a source chunk that was used to generate the answer.
    """
    ontology_id: str
    version: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class QueryRequest(BaseModel):
    """
    Request model for the /query endpoint.
    """
    query: str = Field(..., description="The natural language query about the ontology.")
    # Optional filters can be added here in the future
    # e.g., filter_by_ontology_id: str = None

class QueryResponse(BaseModel):
    """
    Response model for the /query endpoint.
    """
    answer: str = Field(..., description="The generated answer to the query.")
    sources: List[SourceChunk] = Field(..., description="A list of source chunks used to generate the answer.")
