#!/bin/bash

# This script runs the end-to-end (E2E) tests for the ONTO-RAG-V1 application.
# It starts the full application stack using Docker, runs the tests against it,
# and then tears it down.

# Exit immediately if a command exits with a non-zero status.
set -e

# Get the directory of this script to ensure we are in the project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/.."

# Change to the project root directory
cd "$PROJECT_ROOT"

echo "========================================"
echo "  Running ONTO-RAG-V1 E2E Test Suite"
echo "========================================"

# --- Check for API Keys ---
if ! grep -q "OPENAI_API_KEY=sk-" app.env || ! grep -q "COHERE_API_KEY=" app.env; then
    echo "Error: API keys for OpenAI and Cohere are not found in app.env."
    echo "Please add your keys to the app.env file before running the E2E tests."
    exit 1
fi

# --- Docker Compose Teardown (cleanup before start) ---
cleanup() {
    echo "--> Shutting down Docker services..."
    sudo docker compose down -v --remove-orphans
    echo "--> Teardown complete."
}
# Register the cleanup function to be called on script exit
trap cleanup EXIT

echo "--> Performing initial cleanup..."
cleanup

# --- Docker Compose Startup ---
echo "--> Starting application stack with Docker Compose..."
sudo docker compose up --build -d
echo "--> Waiting for services to start..."
sleep 10 # Initial wait for containers to initialize

# --- Health Check ---
HEALTH_CHECK_URL="http://localhost:8000/"
MAX_RETRIES=15
RETRY_COUNT=0

echo "--> Waiting for API to be healthy at $HEALTH_CHECK_URL..."
until $(curl --output /dev/null --silent --head --fail "$HEALTH_CHECK_URL"); do
    if [ ${RETRY_COUNT} -ge ${MAX_RETRIES} ]; then
        echo "Error: API did not become healthy in time."
        exit 1
    fi
    printf '.'
    RETRY_COUNT=$(($RETRY_COUNT + 1))
    sleep 2
done
echo ""
echo "--> API is healthy!"

# --- Run E2E Tests ---
echo "--> Installing test dependencies..."
# We need to install requests for the e2e test script
python -m pip install -q requests pytest

echo "--> Running E2E tests..."
# We specifically target the e2e test directory
python -m pytest tests/e2e/

echo "--> E2E test suite finished."
echo "========================================"

# The 'trap cleanup EXIT' will handle the teardown automatically.
