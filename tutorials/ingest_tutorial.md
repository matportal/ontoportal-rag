# Tutorial: Ingesting an Ontology

This tutorial will walk you through the process of ingesting a new ontology into the ONTO-RAG-V1 system using the API.

We will use `curl` to send a `multipart/form-data` request to the `/api/v1/ingest_ontology` endpoint.

## Prerequisites

1.  The ONTO-RAG-V1 application stack must be running. See the main `README.md` for instructions.
2.  You need a sample ontology file. For this example, let's assume you have a file named `pizza.owl` in your current directory.
3.  You need `curl` installed on your system.

## Ingestion Command

The `curl` command below sends the ontology file along with its metadata. Each piece of metadata is sent as a separate form field using the `-F` flag.

```bash
curl -X POST "http://localhost:8000/api/v1/ingest_ontology" \
  -F "ontology_file=@pizza.owl;type=application/rdf+xml" \
  -F "ontology_id=pizza_ontology" \
  -F "version=1.0.0" \
  -F "is_update=false" \
  -F 'metadata_json={"domain": "food", "author": "Jules"}'
```

### Command Breakdown

-   `-X POST`: Specifies the HTTP method.
-   `"http://localhost:8000/api/v1/ingest_ontology"`: The URL of the ingestion endpoint.
-   `-F "ontology_file=@pizza.owl;type=application/rdf+xml"`: This attaches the `pizza.owl` file. The `@` symbol tells `curl` to read the content from the file. We also specify the `type` (MIME type).
-   `-F "ontology_id=pizza_ontology"`: Sets the unique ID for this ontology.
-   `-F "version=1.0.0"`: Sets the version.
-   `-F "is_update=false"`: Indicates that this is a new ingestion, not an update.
-   `-F 'metadata_json={...}'`: Provides optional metadata as a JSON string. Note the use of single quotes to prevent shell expansion issues with the double quotes inside the JSON.

## Expected Response

If the request is successful, the server will immediately respond with a `202 Accepted` status code and a JSON body confirming that the task has been queued.

```json
{
  "task_id": "a-unique-task-id-will-be-here",
  "status": "processing",
  "message": "Ontology ingestion has been successfully started."
}
```

This response confirms that your ontology is now being processed in the background. You can use the `task_id` in the future to check the status of the ingestion (note: a task status endpoint is not implemented in this version).
