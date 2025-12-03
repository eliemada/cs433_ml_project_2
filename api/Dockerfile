# Multi-stage build using UV for fast dependency management
FROM python:3.11-slim AS builder

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set up working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install ONLY API dependencies (exclude heavy ML packages)
# Create minimal requirements for API-only deployment
RUN uv pip install --system \
    fastapi \
    uvicorn[standard] \
    python-multipart \
    openai \
    litellm \
    tiktoken \
    faiss-cpu \
    boto3 \
    weaviate-client \
    pydantic \
    pydantic-settings \
    python-dotenv \
    requests \
    tenacity \
    loguru

# Production stage
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY rag_pipeline/ ./rag_pipeline/
COPY api/ ./api/
COPY scripts/utils/ ./scripts/utils/

# Set environment variables
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the API
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
