import logging
import sys
from pythonjsonlogger import jsonlogger
from src.app.core.config import settings

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        log_record['level'] = record.levelname
        log_record['name'] = record.name

def setup_logging():
    """
    Configures structured (JSON) logging for the entire application.

    This should be called once at application startup.
    """
    # Remove any existing handlers from the root logger
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Configure the root logger
    logging.basicConfig(
        level=settings.APP_ENV == "development" and "INFO" or "WARNING",
        handlers=[logging.StreamHandler(sys.stdout)],
        format='%(asctime)s %(name)s %(levelname)s %(message)s'
    )

    # Use JSON formatter for production-like environments
    if settings.APP_ENV != "development":
        logHandler = logging.StreamHandler(sys.stdout)
        formatter = CustomJsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s'
        )
        logHandler.setFormatter(formatter)

        # Get the root logger and remove existing handlers
        logger = logging.getLogger()
        logger.handlers.clear()
        logger.addHandler(logHandler)
        logger.setLevel(logging.INFO)

    logging.info("Logging configured successfully.")
