# Scripts Directory

## Overview

This directory contains scripts for distributed parallel processing of PDFs using AWS EC2 Spot instances, benchmarking tools, and development utilities.

## Directory Structure

```
scripts/
├── operations/        # Production/deployment scripts
├── benchmarking/      # Evaluation and reporting scripts
├── dev/              # Development and testing scripts
└── utils/            # Shared utility modules
```

## Your S3 Structure

```
s3://cs433-rag-project2/
├── raw_pdfs/                              # Input PDFs (4000 files)
│   ├── 00002_W2122361802_Navigating...pdf
│   ├── 00003_W2122361803_...pdf
│   └── ...
├── processed/                             # Output folders (one per PDF)
│   ├── 00002_W2122361802/
│   │   └── document.md
│   ├── 00003_W2122361803/
│   │   └── document.md
│   └── ...
├── raw_metadata/                          # Existing metadata
└── failures/                              # Failure reports (auto-created)
    ├── worker-0-failures.json
    └── ...
```

## Key Files

### Operations
- **`operations/distributed_worker.py`** - Main worker script that runs on each EC2 instance
- **`operations/process_pdfs_batch.py`** - Batch PDF processing
- **`operations/batch_chunk_markdown.py`** - Batch markdown chunking
- **`operations/chunk_all_documents.py`** - Document chunking operations
- **`operations/embed_and_index.py`** - Embedding and indexing operations
- **`operations/check_worker_status.py`** - Worker monitoring

### Benchmarking
- **`benchmarking/generate_chunking_report.py`** - Generate evaluation reports
- **`benchmarking/regenerate_plots.py`** - Regenerate visualization plots

### Development
- **`dev/test_local_processing.py`** - Test local PDF processing
- **`dev/test_markdown_chunking.py`** - Test chunking functionality
- **`dev/test_retriever.py`** - Test retrieval functionality

### Utilities
- **`utils/s3_utils.py`** - S3 helper functions (list, download, upload, exists)
- **`utils/worker_distribution.py`** - Work partitioning logic
- **`utils/markdown_s3_loader.py`** - S3 markdown loading utilities

### Configuration
- **`.env.example`** - Example configuration file

## Quick Start

### 1. Set Up Environment Variables

Copy the example and configure:

```bash
cp .env.example .env
# Edit .env with your settings
```

**Required variables:**
```bash
WORKER_ID=0                              # Unique ID: 0, 1, 2, 3, 4
TOTAL_WORKERS=5                          # Total parallel workers
S3_INPUT_BUCKET=cs433-rag-project2       # Your bucket
S3_INPUT_PREFIX=raw_pdfs/                # Input folder
S3_OUTPUT_BUCKET=cs433-rag-project2      # Output bucket
S3_OUTPUT_PREFIX=processed/              # Output folder
```

### 2. Test Locally (Optional)

Test with a single PDF before launching to AWS:

```bash
# Set environment variables
export WORKER_ID=0
export TOTAL_WORKERS=1
export S3_INPUT_BUCKET=cs433-rag-project2
export S3_INPUT_PREFIX=raw_pdfs/
export S3_OUTPUT_BUCKET=cs433-rag-project2
export S3_OUTPUT_PREFIX=processed/

# Run worker
python operations/distributed_worker.py
```

This will process ALL PDFs since TOTAL_WORKERS=1. For testing, you might want to manually filter in the code first.

### 3. Launch on AWS

See the main design document: `docs/plans/2025-11-09-distributed-pdf-processing-design.md`

## How Work Distribution Works

With 5 workers and 10 PDFs:

```python
# PDFs are sorted alphabetically first
all_pdfs = [
    'raw_pdfs/00002_W2122361802_...pdf',  # index 0 → Worker 0
    'raw_pdfs/00003_W2122361803_...pdf',  # index 1 → Worker 1
    'raw_pdfs/00004_W2122361804_...pdf',  # index 2 → Worker 2
    'raw_pdfs/00005_W2122361805_...pdf',  # index 3 → Worker 3
    'raw_pdfs/00006_W2122361806_...pdf',  # index 4 → Worker 4
    'raw_pdfs/00007_W2122361807_...pdf',  # index 5 → Worker 0
    'raw_pdfs/00008_W2122361808_...pdf',  # index 6 → Worker 1
    'raw_pdfs/00009_W2122361809_...pdf',  # index 7 → Worker 2
    'raw_pdfs/00010_W2122361810_...pdf',  # index 8 → Worker 3
    'raw_pdfs/00011_W2122361811_...pdf',  # index 9 → Worker 4
]

# Each worker processes: if (index % TOTAL_WORKERS == WORKER_ID)
```

**Result**: Each worker gets ~800 PDFs, no overlap, no coordination needed!

## Idempotent Processing

Workers automatically skip PDFs that have already been processed:

```python
# Before processing raw_pdfs/00002_W2122361802_...pdf
# Check if processed/00002_W2122361802_...md exists
# If yes → skip
# If no → process
```

This means you can:
- Re-run workers safely
- Resume after failures
- Add more workers mid-run

## Monitoring

### Check Progress

Count processed PDFs (counts folders):
```bash
# Count folders in processed/
aws s3 ls s3://cs433-rag-project2/processed/ | grep "PRE" | wc -l

# Or count document.md files
aws s3 ls s3://cs433-rag-project2/processed/ --recursive | grep "document.md" | wc -l
```

### View Failures

Check failure reports:
```bash
aws s3 cp s3://cs433-rag-project2/failures/worker-0-failures.json -
```

### CloudWatch Logs

When running on EC2, logs go to CloudWatch Logs:
- Log group: `/aws/ec2/pdf-workers/`
- Log streams: `worker-0`, `worker-1`, etc.

## Output Format

Input PDF:
```
raw_pdfs/00002_W2122361802_Navigating_the_Patent_Thicket_Cross_Licenses,_Patent_Pools,_and_Standard-Setting.pdf
```

Output structure:
```
processed/
  └── 00002_W2122361802/          ← Folder named by PDF ID
      └── document.md              ← Always "document.md"
```

The PDF ID (`00002_W2122361802`) is extracted from the filename, and a folder is created with that ID containing `document.md`.

## Cost Estimate

With 5 workers on g4dn.xlarge Spot instances:
- **Cost per hour**: 5 × $0.158 = $0.79/hour
- **Time to process 4000 PDFs**: ~33 hours (at 2.5 min/PDF)
- **Total cost**: ~$26

Well under your $100 budget! 💰

## Troubleshooting

**Worker doesn't find PDFs**
- Check `S3_INPUT_BUCKET` and `S3_INPUT_PREFIX` are correct
- Verify AWS credentials have S3 read permissions

**Output not uploading**
- Check AWS credentials have S3 write permissions
- Verify `S3_OUTPUT_BUCKET` exists

**Dolphin model errors**
- Check GPU is available: `nvidia-smi`
- Verify model weights are downloaded (should be in Docker image)

## Next Steps

1. ✅ **Phase 1 Complete**: Worker script and utilities
2. 🚧 **Phase 2**: Update Docker image
3. 📋 **Phase 3**: Create AWS launch script
4. 🚀 **Phase 4**: Launch and monitor

See design document for full implementation plan.
