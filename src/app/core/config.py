from typing import Optional
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(".env")

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    # Core Application Settings
    APP_ENV: str = "development"

    # Weaviate Configuration
    WEAVIATE_URL: str
    WEAVIATE_API_KEY: str = "your-weaviate-api-key" # Default for local, override for cloud
    WEAVIATE_CLASS_NAME: str = "OntologyChunk"

    # Cohere API Key and Base URL
    COHERE_API_KEY: str
    # Optional: Cohere API base URL to target non-default endpoints
    COHERE_BASE_URL: Optional[str] = None

    # OpenAI API Key and Base URL
    OPENAI_API_KEY: str
    # Optional: OpenAI API base URL (for LangChain ChatOpenAI)
    OPENAI_BASE_URL: Optional[str] = None

    # OpenAI LLM-specific credentials (used by ChatOpenAI)
    OPENAI_LLM_API_KEY: Optional[str] = None
    OPENAI_LLM_BASE_URL: Optional[str] = None

    # OpenAI Embeddings-specific credentials (used by Weaviate text2vec-openai)
    OPENAI_EMBEDDINGS_API_KEY: Optional[str] = None
    OPENAI_EMBEDDINGS_BASE_URL: Optional[str] = None

    # OntoPortal REST API Configuration
    ONTOPORTAL_API_BASE_URL: str = Field(
        "https://rest.matportal.org",
        validation_alias=AliasChoices("ONTOPORTAL_API_BASE_URL", "MATPORTAL_API_BASE_URL")
    )
    ONTOPORTAL_API_KEY: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("ONTOPORTAL_API_KEY", "MATPORTAL_API_KEY")
    )

    # ROBOT (Ontology repair/conversion)
    ROBOT_ENABLED: bool = False
    ROBOT_JAR_PATH: Optional[str] = None

    # Ontology Synchronisation
    ONTOLOGY_SYNC_ENABLED: bool = False
    ONTOLOGY_SYNC_INTERVAL_MINUTES: int = 1440

    # Celery and Redis Configuration
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # Model Configuration
    DEFAULT_LLM_MODEL: str = "gpt-4o"
    DEFAULT_RERANKING_MODEL: str = "rerank-english-v2.0"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    class Config:
        # This makes Pydantic load variables from a .env file if it exists
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = "ignore"

    @staticmethod
    def _validate_sync_interval(value: int) -> int:
        if value < 60 or value > 1440:
            raise ValueError("ONTOLOGY_SYNC_INTERVAL_MINUTES must be between 60 and 1440 (inclusive).")
        return value

    @property
    def validated_sync_interval(self) -> int:
        """
        Return the validated sync interval (in minutes) ensuring it is within the supported bounds.
        """
        return self._validate_sync_interval(self.ONTOLOGY_SYNC_INTERVAL_MINUTES)


# Create a single, reusable instance of the settings
settings = Settings()
