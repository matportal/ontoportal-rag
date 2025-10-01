import os
import time
import requests
import pytest

# The base URL for the running API service
BASE_URL = "http://localhost:8000/api/v1"
# Path to the sample ontology file
ONTOLOGY_FILE_PATH = os.path.join(os.path.dirname(__file__), "data", "pizza.owl")

def test_e2e_ingestion_and_query():
    """
    Performs a full end-to-end test of the ingestion and query pipelines.
    """
    # --- Step 1: Ingest the Ontology ---
    print("\n--- Step 1: Ingesting sample ontology ---")

    with open(ONTOLOGY_FILE_PATH, "rb") as f:
        files = {"ontology_file": ("pizza.owl", f, "application/rdf+xml")}
        data = {
            "ontology_id": "e2e_pizza_ontology",
            "version": "1.0",
            "is_update": "true", # Use true to ensure a clean slate for this test
        }

        ingest_response = requests.post(f"{BASE_URL}/ingest_ontology", files=files, data=data)

    print(f"Ingestion response: {ingest_response.status_code} {ingest_response.text}")
    assert ingest_response.status_code == 202
    ingest_data = ingest_response.json()
    assert "task_id" in ingest_data

    # --- Step 2: Wait for Ingestion ---
    # In a real-world scenario, we might poll a task status endpoint.
    # For this test, a simple sleep is sufficient.
    wait_time = 15
    print(f"--- Step 2: Waiting {wait_time} seconds for ingestion to complete ---")
    time.sleep(wait_time)

    # --- Step 3: Query the Ontology ---
    print("--- Step 3: Querying the ingested ontology ---")
    query_payload = {
        "query": "What are the main ingredients of a Margherita pizza?"
    }

    query_response = requests.post(f"{BASE_URL}/query", json=query_payload)

    print(f"Query response: {query_response.status_code}")
    assert query_response.status_code == 200

    query_data = query_response.json()
    print(f"Answer received: {query_data['answer']}")

    # --- Step 4: Assert the Response ---
    print("--- Step 4: Asserting the response ---")
    assert "answer" in query_data
    assert "sources" in query_data
    assert len(query_data["sources"]) > 0

    # Check for plausible keywords in the answer
    answer_lower = query_data["answer"].lower()
    assert "margherita" in answer_lower or "tomato" in answer_lower or "mozzarella" in answer_lower

    print("\nE2E test completed successfully!")

# Note: This test requires a live, running application stack.
# It should be run by the `run_e2e_tests.sh` script.
