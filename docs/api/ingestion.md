# Ingestion API

This section provides a reference for the ontology ingestion endpoint.

## POST /api/v1/ingest_ontology

Asynchronously ingests and processes an ontology file.

This endpoint accepts a `multipart/form-data` request with the following fields:

| Field           | Type        | Description                                                                 | Required |
| --------------- | ----------- | --------------------------------------------------------------------------- | -------- |
| `ontology_file` | File        | The ontology file (e.g., in OWL/RDF format).                                | Yes      |
| `ontology_id`   | string      | A unique identifier for the ontology.                                       | Yes      |
| `version`       | string      | The version of the ontology.                                                | Yes      |
| `is_update`     | boolean     | Set to `true` to delete existing data for this `ontology_id` before ingestion. | No       |
| `metadata_json` | JSON string | Optional JSON string for additional metadata.                               | No       |

### Success Response

-   **Code:** `202 Accepted`
-   **Content:**
    ```json
    {
      "task_id": "string",
      "status": "processing",
      "message": "Ontology ingestion has been successfully started."
    }
    ```

### Error Responses

-   **Code:** `400 Bad Request` (e.g., if no file is provided)
-   **Code:** `500 Internal Server Error` (if the task dispatching fails)
