import logging

from src.app.worker import celery_app
from src.app.services.ontology_sync_service import OntologySyncService

logger = logging.getLogger(__name__)


@celery_app.task(name="sync_ontologies_task")
def sync_ontologies_task():
    """
    Celery task orchestrating the ontology synchronisation workflow.
    """
    logger.info("Starting scheduled ontology synchronisation run.")
    service = OntologySyncService()
    result = service.sync()
    logger.info("Ontology synchronisation run finished: %s", result)
    return result

