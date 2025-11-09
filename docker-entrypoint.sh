#!/bin/bash
set -e

# Docker entrypoint for PDF processing
# Supports two modes:
#   1. Distributed worker mode (default) - runs distributed_worker.py
#   2. Legacy batch mode - runs process_pdfs_batch.py

# Check if S3 bucket variables are set (indicates distributed mode)
if [ -n "$S3_INPUT_BUCKET" ] && [ -n "$S3_OUTPUT_BUCKET" ]; then
    echo "=========================================="
    echo "Starting DISTRIBUTED WORKER MODE"
    echo "=========================================="
    echo "Worker ID: $WORKER_ID"
    echo "Total Workers: $TOTAL_WORKERS"
    echo "Concurrent PDFs: $CONCURRENT_PDFS"
    echo "Input: s3://$S3_INPUT_BUCKET/$S3_INPUT_PREFIX"
    echo "Output: s3://$S3_OUTPUT_BUCKET/$S3_OUTPUT_PREFIX"
    echo "=========================================="
    echo ""

    # Run distributed worker
    exec uv run python scripts/distributed_worker.py
else
    echo "=========================================="
    echo "Starting LEGACY BATCH MODE"
    echo "=========================================="
    echo "Note: For distributed processing, set:"
    echo "  - S3_INPUT_BUCKET"
    echo "  - S3_OUTPUT_BUCKET"
    echo "=========================================="
    echo ""

    # Run legacy batch processor
    exec uv run python scripts/process_pdfs_batch.py "$@"
fi
