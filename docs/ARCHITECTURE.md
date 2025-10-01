# Architecture and Design

This document provides a detailed overview of the ONTO-RAG-V1 system architecture, its components, and the design decisions behind them.

## 1. Guiding Principles

The system was designed with the following principles in mind:

-   **Scalability:** The architecture must handle both large volumes of data (many ontologies) and a high number of user queries. The separation of the ingestion and retrieval pipelines is a direct result of this principle.
-   **Responsiveness:** The user-facing query pipeline must be fast and provide answers in real-time.
-   **Modularity:** Each component of the system is designed to be independent and replaceable. For example, the LLM, the re-ranker, or the vector database could be swapped out with minimal changes to the overall architecture.
-   **Reproducibility:** The entire application stack is containerized using Docker, ensuring a consistent environment for development, testing, and production.

## 2. System Components

The system consists of four primary services orchestrated by Docker Compose:

-   **`api`**: A FastAPI application that exposes the REST API for ingestion and querying.
-   **`worker`**: A Celery worker that consumes tasks from the message queue and performs the heavy, time-consuming data processing for the ingestion pipeline.
-   **`weaviate`**: The core data persistence layer. It acts as a hybrid vector and keyword database, storing the processed ontology chunks.
-   **`redis`**: A message broker that facilitates communication between the `api` and `worker` services. It is used by Celery to manage the task queue.

## 3. Data Flow: Asynchronous Ingestion Pipeline

The ingestion pipeline is designed to be asynchronous to prevent blocking the API with long-running processing tasks.

```
+---------------+   1. POST /ingest_ontology   +---------+   2. Dispatch Task   +---------+
|   End User    | ---------------------------> |   API   | ------------------> |  Redis  |
+---------------+                            +---------+                     +----+----+
                                                                                  | 3. Consume Task
                                                                                  |
                                                                            +-----v-----+
                                                                            |  Worker   |
                                                                            +-----+-----+
                                                                                  | 4. Process
                                                                                  |
        +-------------------------------------------------------------------------+
        |
        v
+-----------------+   5. Convert to MD   +-------------------+   6. Chunk Text   +----------------+   7. Batch Index   +----------+
|  Ontology File  | -------------------> |      pylode       | ----------------> |   LangChain    | ----------------> | Weaviate |
+-----------------+                      +-------------------+                   +----------------+                   +----------+

```

**Flow Description:**

1.  **HTTP Request:** A user sends a `POST` request to the `/api/v1/ingest_ontology` endpoint with the ontology file and metadata.
2.  **Task Dispatch:** The API service receives the request, saves the file to a temporary location, and immediately dispatches a `process_ontology_task` to the Celery queue (managed by Redis). It returns a `202 Accepted` response to the user with a task ID.
3.  **Task Consumption:** The Celery `worker` is constantly monitoring the Redis queue. It picks up the task.
4.  **Processing:** The worker executes the task, which involves the following sub-steps:
5.  **Convert to Markdown:** The worker uses `pylode` (v2) to convert the raw, machine-readable ontology file into a structured, human-readable Markdown document. This step is crucial for making the ontology's structure understandable to an LLM.
6.  **Chunk Text:** The Markdown document is then split into smaller, semantically coherent chunks using LangChain's `MarkdownHeaderTextSplitter`. This ensures that related pieces of information (like a class and its attributes) remain together.
7.  **Batch Index:** The worker connects to Weaviate and indexes the chunks in a batch operation for efficiency. Weaviate's configured `text2vec-openai` module automatically generates vector embeddings for each chunk's content upon insertion.

## 4. Data Flow: Synchronous Retrieval Pipeline

The retrieval pipeline executes in real-time when a user submits a query. It is optimized for precision and speed.

```
+----------+   1. POST /query   +---------+   2. Call Service    +-------------------+
| End User | -----------------> |   API   | -------------------> | RetrievalService  |
+----------+                    +---------+                      +--------+----------+
                                                                         |
                                                                         | 3. Hybrid Search
                                                                         v
+------------------------------------------------------------------+----------+
|                                                                  | Weaviate |
| 8. Return Final Answer                                           +----+-----+
|                                                                       | 4. Return ~25 Candidates
+-----------------------------------------------------------------------+
        |                                                               |
        v                                                               |
+-------------------+   5. Re-rank Candidates   +--------+   6. Select Top 5   +-------------+   7. Generate Answer   +-----+
| RetrievalService  | -----------------------> | Cohere | ----------------> | Prompt + LLM| ----------------------> | API |
+-------------------+                          +--------+                   +-------------+                         +-----+

```

**Flow Description:**

1.  **HTTP Request:** A user sends a `POST` request to the `/api/v1/query` endpoint with a natural language query.
2.  **Service Call:** The API endpoint calls the `answer_query` method of the `RetrievalService`.
3.  **Hybrid Search:** The service sends the query to Weaviate, performing a hybrid search that combines vector similarity (semantic search) and BM25 keyword matching. This retrieves a broad set of ~25 potentially relevant chunks.
4.  **Candidate Retrieval:** Weaviate returns the candidate chunks to the service.
5.  **Re-ranking:** The service passes the user's query and the candidate chunks to the Cohere Rerank API. The re-ranker uses a more sophisticated model to precisely re-order the chunks from most to least relevant.
6.  **Context Selection:** The service selects the top 3-5 re-ranked chunks to use as context.
7.  **Generation:** The selected chunks are formatted into a carefully crafted prompt along with the original query. This enriched prompt is sent to the configured Large Language Model (e.g., GPT-4) via LangChain to generate a final answer.
8.  **HTTP Response:** The API returns a `200 OK` response to the user, containing the generated answer and a list of the source chunks that were used to create it.
