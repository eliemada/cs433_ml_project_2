# Usage Guide

Complete guide for using the RAG Pipeline for Academic Papers.

## Table of Contents

1. [Setup](#setup)
2. [Processing PDFs](#processing-pdfs)
3. [Distributed Processing](#distributed-processing)
4. [Monitoring Progress](#monitoring-progress)
5. [Working with Output](#working-with-output)
6. [Troubleshooting](#troubleshooting)

## Setup

### Prerequisites

- Python 3.10+
- CUDA-capable GPU (for local processing)
- AWS account with S3 access (for distributed processing)
- 50+ GB free disk space

### Installation

```bash
# Clone repository
git clone <repository-url>
cd project-2-rag

# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

### Configuration

Create a `.env` file in the project root:

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=eu-north-1

# S3 Buckets
S3_INPUT_BUCKET=cs433-rag-project2
S3_OUTPUT_BUCKET=cs433-rag-project2

# Worker Configuration (for distributed processing)
WORKER_ID=0
TOTAL_WORKERS=3
CONCURRENT_PDFS=3
```

## Processing PDFs

### Local Processing

Test processing a single PDF locally:

```bash
uv run python scripts/test_local_processing.py --pdf path/to/paper.pdf --output output/test_local
```

This will create:
```
output/test_local/
├── markdown/
│   ├── document.md
│   └── figures/
│       ├── figure_001.png
│       └── ...
└── recognition_json/
    └── document.json
```

### Batch Processing

Process multiple PDFs from S3:

```bash
uv run python scripts/process_pdfs_batch.py --bucket cs433-rag-project2 --prefix raw_pdfs/ --limit 50
```

## Distributed Processing

### On AWS EC2

**Step 1: Launch EC2 Instances**

Launch 3-5 GPU instances:
- Instance type: `g4dn.xlarge` (NVIDIA T4 GPU)
- AMI: Deep Learning Base AMI (Ubuntu 22.04)
- Storage: 125 GB
- Security group: Allow SSH

**Step 2: Deploy Workers**

On each instance:

```bash
# Instance 1 (Worker 0)
docker run --gpus all --rm \
  --env-file .env \
  -e WORKER_ID=0 \
  -e TOTAL_WORKERS=3 \
  ravinala/pdf-parser:v2-distributed

# Instance 2 (Worker 1)
docker run --gpus all --rm \
  --env-file .env \
  -e WORKER_ID=1 \
  -e TOTAL_WORKERS=3 \
  ravinala/pdf-parser:v2-distributed

# Instance 3 (Worker 2)
docker run --gpus all --rm \
  --env-file .env \
  -e WORKER_ID=2 \
  -e TOTAL_WORKERS=3 \
  ravinala/pdf-parser:v2-distributed
```

**Worker Distribution:**
- Worker 0: Processes PDFs at indices 0, 3, 6, 9, ...
- Worker 1: Processes PDFs at indices 1, 4, 7, 10, ...
- Worker 2: Processes PDFs at indices 2, 5, 8, 11, ...

### Running in Background

To keep workers running after disconnecting:

```bash
nohup docker run --gpus all --rm \
  --env-file .env \
  -e WORKER_ID=0 \
  -e TOTAL_WORKERS=3 \
  ravinala/pdf-parser:v2-distributed > worker.log 2>&1 &
```

View logs:
```bash
tail -f worker.log
```

### Manual S3 Check

Count processed PDFs:
```bash
aws s3 ls s3://cs433-rag-project2/processed/ | grep "PRE" | wc -l
```

List recent outputs:
```bash
aws s3 ls s3://cs433-rag-project2/processed/ --recursive | tail -20
```

### GPU Monitoring

On EC2 instance:
```bash
# Watch GPU utilization
nvidia-smi -l 1

# Check GPU memory
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

## Working with Output

### Output Structure

Each processed PDF creates:

```
s3://bucket/processed/{PDF_ID}/
├── document.md          # Markdown content with sections and citations
├── metadata.json        # Processing metadata (page count, figures, etc.)
└── figures/             # Extracted figures
    ├── figure_001.png
    ├── figure_002.png
    └── ...
```

### Download Processed Documents

Download a specific document:
```bash
aws s3 sync s3://cs433-rag-project2/processed/00002_W2122361802/ ./output/downloaded/
```

Download all processed documents:
```bash
aws s3 sync s3://cs433-rag-project2/processed/ ./output/all_processed/
```

### Parse Metadata

```python
import json
import boto3

s3 = boto3.client('s3')

# Get metadata for a document
response = s3.get_object(
    Bucket='cs433-rag-project2',
    Key='processed/00002_W2122361802/metadata.json'
)
metadata = json.loads(response['Body'].read())

print(f"Pages: {metadata['page_count']}")
print(f"Figures: {metadata['figure_count']}")
print(f"Processing time: {metadata['processing_time_seconds']}s")
```

## Troubleshooting

### GPU Out of Memory

If you see CUDA OOM errors:

1. Reduce batch size in `rag_pipeline/pdf_parsing/config.py`:
```python
BATCH_SIZE = 2  # Down from 4
```

2. Reduce concurrent PDFs:
```bash
export CONCURRENT_PDFS=2  # Down from 3
```

### Worker Not Processing

Check if worker is running:
```bash
docker ps
```

View worker logs:
```bash
docker logs <container-id>
```

Restart worker:
```bash
docker restart <container-id>
```

### S3 Permission Errors

Verify IAM permissions:
```bash
aws sts get-caller-identity
aws s3 ls s3://cs433-rag-project2/
```

Required S3 permissions:
- `s3:GetObject` (read)
- `s3:PutObject` (write)
- `s3:ListBucket` (list)

### Processing Failures

Check failure logs on worker instance:
```bash
cat failures/worker-0-failures.json
```

Re-process failed PDFs:
```bash
uv run python scripts/retry_failures.py --worker-id 0
```

### Connection Timeout

If downloads timeout, increase timeout in code:

```python
# In scripts/distributed_worker.py
s3_client = boto3.client('s3', config=Config(
    connect_timeout=300,
    read_timeout=300
))
```

## Next Steps

### RAG Pipeline

Once PDFs are processed, set up the RAG pipeline:

1. **Chunk documents:**
```bash
uv run python scripts/chunking_worker.py --bucket cs433-rag-project2
```

2. **Generate embeddings:**
```bash
uv run python scripts/embedding_worker.py --bucket cs433-rag-project2
```

3. **Index in vector database:**
```bash
uv run python scripts/vectordb_indexer.py --weaviate-url http://localhost:8080
```

4. **Query system:**
```bash
uv run python scripts/rag_query.py --query "What are the main findings about X?"
```

## Performance Tips

### Optimize Processing Speed

1. **Increase workers:** Use 5+ instances for faster processing
2. **Use larger GPUs:** g4dn.2xlarge or p3.2xlarge for 1.5-2x speedup
3. **Batch processing:** Increase `CONCURRENT_PDFS` to 5-10 (if GPU memory allows)

### Cost Optimization

1. **Use Spot Instances:** 50-70% cheaper than on-demand
2. **Auto-shutdown:** Set EC2 instances to auto-terminate when idle
3. **S3 Lifecycle:** Move old outputs to Glacier after 90 days

### Quality Improvements

1. **Higher resolution:** Increase DPI for better OCR accuracy
2. **Post-processing:** Add citation extraction and cleanup
3. **Validation:** Check outputs for completeness

## Additional Resources

- **Deployment Guide:** `docs/deployment.md`
- **Project Checkpoint:** `docs/checkpoint_2025-11-10.md`
- **System Architecture:** See `DISTRIBUTED_SYSTEM_EXPLAINED.md` (if available)

---

**Need Help?** Check existing issues or open a new one on GitHub.
