import logging
from fastapi import APIRouter, Depends, HTTPException, status
from src.app.schemas.models import QueryRequest, QueryResponse
from src.app.services.retrieval_service import RetrievalService

router = APIRouter()
logger = logging.getLogger(__name__)

# Dependency to get an instance of the retrieval service
# This helps with testing and managing the lifecycle of the service.
def get_retrieval_service():
    try:
        return RetrievalService()
    except Exception as e:
        logger.critical(f"Could not create RetrievalService: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="External services required for querying are not available."
        )

@router.post(
    "/query",
    response_model=QueryResponse
)
async def query_ontology(
    request: QueryRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service)
):
    """
    Receives a natural language query and returns a generated answer
    based on the content of the indexed ontologies.
    """
    try:
        logger.info(f"Received query: '{request.query}'")
        response = retrieval_service.answer_query(request.query)
        return response
    except Exception as e:
        logger.error(f"An error occurred during query processing: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while processing the query."
        )
