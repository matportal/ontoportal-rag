# Query API

This section provides a reference for the ontology querying endpoint.

## POST /api/v1/query

Receives a natural language query and returns a generated answer based on the content of the indexed ontologies.

This endpoint accepts a JSON request body.

### Request Body

```json
{
  "query": "string"
}
```

| Field   | Type   | Description                                | Required |
| ------- | ------ | ------------------------------------------ | -------- |
| `query` | string | The natural language query about the ontology. | Yes      |

### Success Response

-   **Code:** `200 OK`
-   **Content:**
    ```json
    {
      "answer": "string",
      "sources": [
        {
          "ontology_id": "string",
          "version": "string",
          "content": "string",
          "metadata": {}
        }
      ]
    }
    ```
    -   `answer`: The generated answer to the query.
    -   `sources`: A list of the source chunks that were used as context to generate the answer.

### Error Responses

-   **Code:** `500 Internal Server Error` (if an unexpected error occurs during processing)
-   **Code:** `503 Service Unavailable` (if a required external service like Cohere or OpenAI is not available)
