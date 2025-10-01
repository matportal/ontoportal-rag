#!/bin/bash

# This script runs the unit and integration tests for the ONTO-RAG-V1 application.

# Exit immediately if a command exits with a non-zero status.
set -e

# Get the directory of this script to ensure we are in the project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/.."

# Change to the project root directory
cd "$PROJECT_ROOT"

echo "========================================"
echo "  Running ONTO-RAG-V1 Test Suite"
echo "========================================"

echo "--> Installing dependencies from requirements.txt..."
python -m pip install -q -r requirements.txt

echo "--> Running pytest with coverage..."
python -m pytest --cov

echo "--> Test suite execution finished."
echo "========================================"
