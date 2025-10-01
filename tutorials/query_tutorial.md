# Tutorial: Querying an Ontology

This tutorial demonstrates how to ask a question about an ingested ontology using the ONTO-RAG-V1 system's query API.

We will use `curl` to send a `POST` request with a JSON payload to the `/api/v1/query` endpoint.

## Prerequisites

1.  The ONTO-RAG-V1 application stack must be running.
2.  You must have already ingested at least one ontology (see the ingestion tutorial). For this example, we'll assume the `pizza.owl` ontology has been indexed.
3.  You need `curl` installed on your system.

## Query Command

The `curl` command sends a JSON object containing your natural language query.

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main ingredients of a Margherita pizza?"
  }'
```

### Command Breakdown

-   `-X POST`: Specifies the HTTP method.
-   `"http://localhost:8000/api/v1/query"`: The URL of the query endpoint.
-   `-H "Content-Type: application/json"`: This header is important. It tells the server that we are sending a JSON payload.
-   `-d '{...}'`: This flag provides the data for the request body. The data is a JSON object containing the `query` field.

## Expected Response

If the request is successful, the server will respond with a `200 OK` status code and a JSON body containing the answer and the sources used to generate it.

The response will look something like this:

```json
{
  "answer": "A Margherita pizza is traditionally made with Tomato, Mozzarella, and Basil.",
  "sources": [
    {
      "ontology_id": "pizza_ontology",
      "version": "1.0.0",
      "content": "### Margherita Pizza\n\nA classic Neapolitan pizza, the Margherita is made with San Marzano tomatoes, mozzarella cheese, fresh basil, salt, and extra-virgin olive oil.",
      "metadata": {
        "header": "Margherita Pizza"
      }
    },
    {
      "ontology_id": "pizza_ontology",
      "version": "1.0.0",
      "content": "#### Ingredients\n\n- hasIngredient: Tomato\n- hasIngredient: Mozzarella\n- hasIngredient: Basil",
      "metadata": {
        "header": "Ingredients"
      }
    }
  ]
}
```

-   **`answer`**: The LLM-generated answer to your question.
-   **`sources`**: A list of the actual text chunks from the ontology that the LLM used as context. This is extremely useful for verifying the source of the information and understanding the reasoning behind the answer.
