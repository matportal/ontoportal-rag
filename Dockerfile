# Stage 1: Builder - Install dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Set up a virtual environment
ENV VIRTUAL_ENV=/app/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final - Create the production image
FROM python:3.11-slim

WORKDIR /app

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy virtual environment from the builder stage
COPY --from=builder /app/venv /app/venv

# Copy application source code
COPY ./src /app/src

# Set the path to include the virtual environment's binaries
ENV PATH="/app/venv/bin:$PATH"
# Set PYTHONPATH to find the application modules
ENV PYTHONPATH="/app"

# Change ownership of the app directory
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# The command to run the application will be specified in docker-compose.yml
# This allows the same image to be used for both the API and the worker.
# Example CMD for API: CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# Example CMD for Worker: CMD ["celery", "-A", "src.app.worker.celery_app", "worker", "--loglevel=info"]
