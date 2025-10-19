#!/bin/bash

# This script provides a way to run the ONTO-RAG-V1 application locally
# for development, without using Docker.

# Exit immediately if a command exits with a non-zero status and fail on pipe errors.
set -euo pipefail

# Get the directory of this script to ensure we are in the project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/.."

# Change to the project root directory
cd "$PROJECT_ROOT"

echo "========================================"
echo "  Starting ONTO-RAG-V1 Locally"
echo "========================================"

# --- Prerequisite Checks ---
echo "--> Checking for prerequisites..."
if ! command -v python &> /dev/null || ! command -v pip &> /dev/null; then
    echo "Error: python and pip are not found. Please install Python 3.8+."
    exit 1
fi
echo "Python and pip found."

# --- Virtual Environment Setup ---
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "--> Creating Python virtual environment in '$VENV_DIR'..."
    python -m venv "$VENV_DIR"
else
    echo "--> Virtual environment '$VENV_DIR' already exists."
fi

echo "--> Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# --- Install Dependencies ---
echo "--> Installing dependencies from requirements.txt..."
pip install -q -r requirements.txt
echo "Dependencies are up to date."

# --- Important Note ---
echo ""
echo "!!! IMPORTANT !!!"
echo "This script only starts the FastAPI API server and the Celery worker."
echo "You MUST have Redis and Weaviate running separately for the application to work."
echo "The recommended way to run the full stack is with 'docker-compose up'."
echo "Default connections:"
echo "  - Redis: redis://localhost:6379"
echo "  - Weaviate: http://localhost:8080"
echo "Ensure your '.env' file is configured correctly for your local setup."
echo "!!!!!!!!!!!!!!!!!!!"
echo ""

# --- Launch Services ---
echo "--> Launching services..."

# Allow overriding host/port/pool via environment variables for restricted environments
API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
CELERY_POOL="${CELERY_POOL:-solo}"

# Optionally force Celery to use an in-memory broker/backend when external Redis isn't available.
if [[ "${USE_IN_MEMORY_BROKER:-0}" == "1" ]]; then
    export REDIS_URL="memory://"
    export CELERY_BROKER_URL="memory://"
    export CELERY_RESULT_BACKEND="cache+memory://"
    echo "--> Using in-memory Celery broker/backend. Persistent task queues are disabled."
fi

# A trap to kill background processes when the script exits (e.g., via Ctrl+C)
cleanup() {
    local exit_status=$?
    echo ""
    echo "--> Shutting down services..."
    if [ -n "${UVICORN_PID:-}" ] && kill -0 "$UVICORN_PID" 2>/dev/null; then
        kill -- -"$UVICORN_PID" 2>/dev/null || true
    fi
    if [ -n "${CELERY_PID:-}" ] && kill -0 "$CELERY_PID" 2>/dev/null; then
        kill -- -"$CELERY_PID" 2>/dev/null || true
    fi
    echo "Services stopped."
    exit $exit_status
}
trap cleanup EXIT INT TERM

# Launch Uvicorn server for the API
echo "Starting FastAPI server on http://$API_HOST:$API_PORT"
stdbuf -oL -eL uvicorn src.app.main:app --host "$API_HOST" --port "$API_PORT" --reload &
UVICORN_PID=$!

# Launch Celery worker
echo "Starting Celery worker with pool '$CELERY_POOL'..."
stdbuf -oL -eL celery -A src.app.worker.celery_app worker -l INFO --pool "$CELERY_POOL" &
CELERY_PID=$!

# Wait for the first process to exit and propagate its status.
set +e
if ! wait -n "$UVICORN_PID" "$CELERY_PID"; then
    STATUS=$?
    echo ""
    echo "--> One of the services exited with status $STATUS."
    exit "$STATUS"
fi
