# Configuration Guide

The ONTO-RAG-V1 application is configured using environment variables. The system loads these variables from a file named `app.env` in the project root.

Below is a complete list of all environment variables used by the application.

| Variable                  | Description                                                                                             | Default Value                  |
| ------------------------- | ------------------------------------------------------------------------------------------------------- | ------------------------------ |
| `APP_ENV`                 | The application environment. Set to `development` for more verbose logging.                             | `development`                  |
| `WEAVIATE_URL`            | The full URL to the Weaviate instance.                                                                  | `http://weaviate:8080`         |
| `WEAVIATE_API_KEY`        | The API key for Weaviate Cloud Service (WCS). Not required for local Docker instances.                  | `your-weaviate-api-key`        |
| `WEAVIATE_CLASS_NAME`     | The name of the class (schema) used in Weaviate to store ontology chunks.                               | `OntologyChunk`                |
| `COHERE_API_KEY`          | Your API key for the Cohere service, used for the re-ranking step.                                      | `your-cohere-api-key`          |
| `OPENAI_API_KEY`          | Your API key for OpenAI, used for the LLM generation step.                                              | `your-openai-api-key`          |
| `REDIS_URL`               | The URL for the Redis instance used by Celery.                                                          | `redis://redis:6379/0`         |
| `CELERY_BROKER_URL`       | The broker URL for Celery. Should be the same as `REDIS_URL`.                                           | `redis://redis:6379/0`         |
| `CELERY_RESULT_BACKEND`   | The result backend URL for Celery. Should be the same as `REDIS_URL`.                                   | `redis://redis:6379/0`         |
| `DEFAULT_LLM_MODEL`       | The name of the OpenAI model to use for answer generation.                                              | `gpt-4o`                       |
| `DEFAULT_RERANKING_MODEL` | The name of the Cohere model to use for re-ranking.                                                     | `rerank-english-v2.0`          |
| `EMBEDDING_MODEL`         | The name of the OpenAI model to use for generating embeddings (configured in Weaviate).                 | `text-embedding-3-small`       |
