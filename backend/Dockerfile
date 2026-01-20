# =============================================================================
# Backend Dockerfile (Django REST API)
# =============================================================================
# This Dockerfile builds the Django backend application image.
#
# Usage:
#   Development: docker compose up backend
#   Production:  docker build -t eel-backend:prod ./backend
#
# In development, source code is mounted as a volume for hot reload.
# In production, the image contains all code and runs with Gunicorn.
# =============================================================================

FROM python:3.12-slim

# -----------------------------------------------------------------------------
# Environment configuration
# -----------------------------------------------------------------------------
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files
# PYTHONUNBUFFERED: Ensures stdout/stderr are sent straight to terminal
# PYTHONPATH: Adds src directory to Python's module search path
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

WORKDIR /app

# -----------------------------------------------------------------------------
# Install system dependencies
# -----------------------------------------------------------------------------
# build-essential: Required for compiling Python packages with C extensions
# libpq-dev: PostgreSQL client library headers for psycopg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------------
# Install Python dependencies
# -----------------------------------------------------------------------------
# Copy pyproject.toml first to leverage Docker layer caching.
# Dependencies are only reinstalled when pyproject.toml changes.
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --upgrade pip && \
    pip install -e ".[dev]"

# -----------------------------------------------------------------------------
# Copy test suite
# -----------------------------------------------------------------------------
COPY tests/ ./tests/

EXPOSE 8000

# -----------------------------------------------------------------------------
# Default command
# -----------------------------------------------------------------------------
# Production: Gunicorn WSGI server with sensible defaults
# Development: Overridden in docker-compose.yml to use Django's runserver
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]
