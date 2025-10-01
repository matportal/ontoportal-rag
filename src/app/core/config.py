import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
        env_file = "app.env"
        env_file_encoding = 'utf-8'
        extra = "ignore"


# Create a single, reusable instance of the settings
settings = Settings()
