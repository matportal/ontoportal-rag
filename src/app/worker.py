from celery import Celery
import logging
from src.app.core.config import settings

# Set up logging for the worker
logger = logging.getLogger(__name__)

# Create the Celery application instance
# The first argument is the name of the current module.
# The `broker` and `backend` arguments are the URLs to our Redis instance.
celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "src.app.tasks.ontology_processor",
        "src.app.tasks.ontology_sync",
    ] # List of modules to import when the worker starts
)

# Optional Celery configuration
celery_app.conf.update(
    task_track_started=True,
    result_expires=3600, # Expire results after 1 hour
)

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    logger.info("Celery worker configured.")
    if not settings.ONTOLOGY_SYNC_ENABLED:
        logger.info("Ontology sync disabled; periodic job not scheduled.")
        return
    if not settings.ONTOPORTAL_API_KEY:
        logger.warning("ONTOPORTAL_API_KEY missing; ontology sync periodic job not scheduled.")
        return

    interval_minutes = settings.validated_sync_interval
    interval_seconds = interval_minutes * 60
    from src.app.tasks.ontology_sync import sync_ontologies_task

    sender.add_periodic_task(
        interval_seconds,
        sync_ontologies_task.s(),
        name=f"ontology_sync_every_{interval_minutes}_minutes"
    )
    logger.info(
        "Scheduled ontology sync task to run every %d minutes.",
        interval_minutes
    )

# The actual task logic will be in src/app/tasks/ontology_processor.py
# and will be auto-discovered because of the `include` argument above.
