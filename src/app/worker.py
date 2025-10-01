from celery import Celery
from src.app.core.config import settings
import logging

# Set up logging for the worker
logger = logging.getLogger(__name__)

# Create the Celery application instance
# The first argument is the name of the current module.
# The `broker` and `backend` arguments are the URLs to our Redis instance.
celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["src.app.tasks.ontology_processor"] # List of modules to import when the worker starts
)

# Optional Celery configuration
celery_app.conf.update(
    task_track_started=True,
    result_expires=3600, # Expire results after 1 hour
)

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    logger.info("Celery worker configured.")

# The actual task logic will be in src/app/tasks/ontology_processor.py
# and will be auto-discovered because of the `include` argument above.
