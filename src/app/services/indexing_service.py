import logging
import uuid
import weaviate
from typing import List
from langchain.docstore.document import Document

from src.app.core.config import settings

logger = logging.getLogger(__name__)

class IndexingService:
    """
    A service dedicated to all interactions with the Weaviate vector database.
    """
    def __init__(self):
        try:
            # v3 client expects the URL as a positional argument
            self.client = weaviate.Client(settings.WEAVIATE_URL)
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate client: {e}", exc_info=True)
            raise

    def create_schema_if_not_exists(self):
        """Creates the required class schema in Weaviate if it doesn't exist."""
        class_name = settings.WEAVIATE_CLASS_NAME
        if self.client.schema.exists(class_name):
            logger.info(f"Schema '{class_name}' already exists in Weaviate.")
            return

        schema = {
            "class": class_name,
            "description": "Chunks of ontology documentation.",
            "vectorizer": "none",
            "properties": [
                {"name": "content", "dataType": ["text"]},
                {"name": "ontology_id", "dataType": ["text"]},
                {"name": "version", "dataType": ["text"]},
                {"name": "header", "dataType": ["text"]},
                {"name": "metadata", "dataType": ["object"], "nestedProperties": [
                    {"name": "key", "dataType": ["text"]},
                    {"name": "value", "dataType": ["text"]}
                ]}
            ],
        }
        self.client.schema.create_class(schema)
        logger.info(f"Successfully created schema '{class_name}' in Weaviate.")

    def delete_by_ontology_id(self, ontology_id: str):
        """Deletes all objects in Weaviate for a given ontology_id."""
        logger.info(f"Deleting existing data for ontology_id: {ontology_id}")
        where_filter = {
            "path": ["ontology_id"],
            "operator": "Equal",
            "valueString": ontology_id,
        }
        # The delete_objects method has been deprecated, using batch.delete_objects
        result = self.client.batch.delete_objects(settings.WEAVIATE_CLASS_NAME, where=where_filter)
        logger.info(f"Successfully deleted existing data for {ontology_id}. Results: {result}")

    def batch_index_chunks(self, chunks: List[Document], ontology_id: str, version: str, metadata: dict, task_id: str):
        """
        Indexes a list of LangChain Document chunks into Weaviate in a batch.
        """
        logger.info(f"Starting batch indexing of {len(chunks)} chunks into Weaviate...")
        with self.client.batch as batch:
            batch.batch_size = 100
            for i, chunk in enumerate(chunks):
                data_object = {
                    "content": chunk.page_content,
                    "ontology_id": ontology_id,
                    "version": version,
                    "header": chunk.metadata.get("Header 1", "") or chunk.metadata.get("Header 2", "") or chunk.metadata.get("Header 3", ""),
                    "metadata": metadata
                }
                deterministic_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"{task_id}-{i}")
                batch.add_data_object(
                    data_object=data_object,
                    class_name=settings.WEAVIATE_CLASS_NAME,
                    uuid=str(deterministic_uuid)
                )
        logger.info("Batch indexing complete.")
        return len(chunks)
