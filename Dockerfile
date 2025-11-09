FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    git \
    git-lfs \
    curl \
    ca-certificates \
    # OpenCV dependencies
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
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
# Initialize Git LFS and clone with LFS files
RUN git lfs install && \
    git clone https://huggingface.co/ByteDance/Dolphin-1.5 /app/models/dolphin && \
    cd /app/models/dolphin && \
    git lfs pull

# Copy all scripts (including distributed worker)
COPY scripts/ ./scripts/
COPY tests/ ./tests/

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default environment variables for distributed worker
ENV WORKER_ID=0
ENV TOTAL_WORKERS=1
ENV S3_INPUT_PREFIX=raw_pdfs/
ENV S3_OUTPUT_PREFIX=processed/
ENV MAX_RETRIES=2

# Copy entrypoint script
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

# Entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]
