# =============================================================================
# Backend Dockerfile (Django REST API)
# =============================================================================
# Multi-stage build:
#   - Stage 1 (builder): Installs all dependencies including dev
#   - Stage 2 (production): Copies only source code, runs as non-root user
#
# Usage:
#   Development: docker compose up backend
#   Production:  docker build -t eel-backend:prod ./backend
#
# In development, source code is mounted as a volume for hot reload.
# In production, the image contains only source code and runs with Gunicorn.
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder — install dependencies
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --upgrade pip && \
    pip install -e ".[dev]"

# -----------------------------------------------------------------------------
# Stage 2: Production — minimal image with non-root user
# -----------------------------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

WORKDIR /app

# Install runtime-only system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages and source from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app/src /app/src
COPY --from=builder /app/pyproject.toml /app/pyproject.toml

# Create non-root user
RUN groupadd --system django && \
    useradd --system --gid django --create-home django && \
    chown -R django:django /app

USER django

EXPOSE 8000

# Production: Gunicorn WSGI server
# Development: Overridden in docker-compose.yml to use Django's runserver
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]
