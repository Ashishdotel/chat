# Dockerfile — Nepali Chatbot Production Image
# -----------------------------------------------
# Multi-stage would reduce image size further, but single-stage
# is clearer for a thesis demonstration.

FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Environment: don't write .pyc files, don't buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies needed by some Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (Docker layer caching)
# This layer is only rebuilt when requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full project
COPY . .

# Create required data directories
RUN mkdir -p data/documents data/vector_store evaluation/eval_results

# Expose the port the app runs on
EXPOSE 8000

# Run the application
# --workers 1: single worker keeps SQLite safe (no concurrent writes)
# Use PostgreSQL + multiple workers in high-traffic production
CMD ["uvicorn", "backend.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info"]