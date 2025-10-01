import logging
from fastapi import FastAPI
from src.app.core.logging import setup_logging
from src.app.core.config import settings
from src.app.api.endpoints import ingest, query

# Configure logging before initializing the app
setup_logging()

# Create the FastAPI application instance
app = FastAPI(
    title="ONTO-RAG-V1 - Ontology RAG System",
    description="A sophisticated RAG system for querying ontologies using natural language.",
    version="1.0.0"
)

# Include the API routers
app.include_router(ingest.router, prefix="/api/v1", tags=["Ingestion"])
app.include_router(query.router, prefix="/api/v1", tags=["Query"])

# Create a logger instance for this module
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """
    Log application startup event.
    """
    logger.info("Application startup complete.")
    logger.info(f"Application environment: {settings.APP_ENV}")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Log application shutdown event.
    """
    logger.info("Application shutdown.")

@app.get("/", tags=["Health Check"])
async def read_root():
    """
    Root endpoint providing a health check.
    """
    return {"status": "ok", "message": "Welcome to ONTO-RAG-V1"}
