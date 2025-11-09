# Vast.ai PDF Processing Pipeline Design

**Date:** 2025-11-09
**Status:** Approved for Implementation
**Scope:** Bulk PDF parsing on vast.ai using Dolphin model

## Overview

Deploy PDF parsing pipeline to vast.ai for GPU-accelerated processing of academic papers. PDFs stored in S3, processing happens on vast.ai GPU instances, results uploaded back to S3.

## Architecture

### Data Flow
```
Local Machine → S3 (upload PDFs) → Vast.ai (parse) → S3 (results)
```

### S3 Bucket Structure
```
cs433-rag-project2/
├── raw_pdfs/
│   └── {index}_{work_id}_{title}.pdf
├── raw_metadata/
│   └── {index}_{work_id}.json
├── processed/
│   └── {doc_id}/
│       ├── metadata.json          (parsing results + OpenAlex metadata)
│       ├── document.md            (parsed markdown)
│       └── figures/               (extracted figures)
│           ├── fig_001.png
│           └── fig_002.png
└── processing_logs/
    └── failed_docs.json          (list of failed documents)
```

## Design Decisions

### 1. Processing Location
**Decision:** Process on vast.ai GPU instances
**Rationale:** Dolphin model requires GPU; vast.ai provides affordable GPU compute

### 2. S3 Organization
**Decision:** Per-document folders under `processed/{doc_id}/`
**Rationale:**
- Clear processing status (folder exists = processed)
- All outputs grouped together
- Easy to resume if job crashes
- Parallel-friendly (multiple workers don't conflict)

### 3. Model Distribution
**Decision:** Bake Dolphin model weights into Docker image
**Rationale:**
- Fast startup (no download needed per run)
- Model downloaded once during image build
- Worth the larger image size (~8-10GB) vs downloading 2GB every run

### 4. Credentials
**Decision:** Pass AWS credentials as environment variables
**Rationale:**
- Standard practice
- Vast.ai supports env vars
- More secure than baking into image

### 5. Error Handling
**Decision:** Skip failures, log them to `failed_docs.json`
**Rationale:**
- Maximize throughput (don't let one bad PDF kill entire batch)
- Can retry failures later
- GPU time is expensive, process as many as possible

### 6. Processing Discovery
**Decision:** Check S3 for missing `processed/{doc_id}/` folders
**Rationale:**
- Idempotent (safe to restart)
- No state file to manage
- Natural resume behavior

### 7. Parallelism Strategy
**Decision:** Pipeline parallelism (download → GPU → upload overlap)
**Rationale:**
- GPU never waits for S3 I/O
- Doesn't overload GPU memory
- Simple threading model
- Maximizes throughput

## Implementation Components

### 1. Dockerfile
- Base: `nvidia/cuda:11.8.0-runtime-ubuntu22.04`
- Install: Python 3.11, uv, git
- Bake in: Dolphin model from HuggingFace
- Entrypoint: `scripts/process_pdfs_batch.py`

### 2. Processing Script (`scripts/process_pdfs_batch.py`)
**Three-stage pipeline:**
1. **Download thread:** Fetch PDFs from S3 to `/tmp`
2. **GPU processing (main thread):** Run Dolphin model
3. **Upload thread:** Push results to S3

**Features:**
- Queues with size limits (prevent memory bloat)
- Download/upload overlap with GPU processing
- Error tracking and logging
- Cleanup of temporary files

### 3. Dependencies
- `boto3` for S3 operations
- Existing: `rag_pipeline` package with Dolphin wrapper

### 4. Environment Variables (runtime)
```bash
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET=cs433-rag-project2
```

## Deployment Workflow

### Build and Push
```bash
podman build -t ravinala/pdf-parser:latest .
podman push ravinala/pdf-parser:latest
```

### Launch on Vast.ai
1. Search for GPU instance (RTX 3090/4090, 16GB+ VRAM)
2. Docker image: `ravinala/pdf-parser:latest`
3. Set environment variables
4. Launch and monitor logs

### Monitor
```bash
# Check processed documents
aws s3 ls s3://cs433-rag-project2/processed/

# Download failure log
aws s3 cp s3://cs433-rag-project2/processing_logs/failed_docs.json .
```

## Performance Estimates

- **Cost:** ~$0.20-0.40/hour (RTX 3090 on vast.ai)
- **Speed:** ~30 seconds per PDF
- **1000 PDFs:** ~8 hours processing time

## Out of Scope (Future Work)

- Chunking strategy
- Embedding generation
- Vector database integration
- RAG implementation
- Reranking

**Next phase:** After successful parsing, design chunking + embedding pipeline
