FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY rag_pipeline/ ./rag_pipeline/

# Install dependencies
RUN uv sync --frozen

# Download Dolphin model (~2GB)
RUN git clone https://huggingface.co/ByteDance/Dolphin-1.5 /app/models/dolphin

# Copy processing script
COPY scripts/process_pdfs_batch.py ./scripts/

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Entrypoint
ENTRYPOINT ["uv", "run", "python", "scripts/process_pdfs_batch.py"]
