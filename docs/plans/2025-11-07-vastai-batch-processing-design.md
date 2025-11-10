# Vast.ai Batch PDF Processing with S3 Storage

**Date**: 2025-11-07
**Status**: Approved
**Type**: Deployment Architecture

## Overview

A simple, stateless batch processing system for converting large volumes of PDFs to structured Markdown using the Dolphin model on Vast.ai GPU instances, with inputs and outputs stored in S3-compatible cloud storage.

### Key Characteristics
- **Simple**: Single Python script, no external dependencies beyond S3
- **Stateless**: Each run is independent, resumable by checking S3
- **Cost-effective**: ~$12-25 for 1,000 PDFs on Vast.ai
- **Flexible**: Works with AWS S3 or Infomaniak Swift (S3-compatible)

## Architecture

### High-Level Data Flow

```
┌─────────────────┐
│  Local Machine  │
│  (PDFs on disk) │
└────────┬────────┘
         │ 1. Upload PDFs
         ▼
┌─────────────────────────────┐
│     S3 Input Bucket         │
│  s3://bucket/pdf-input/     │
│  - 00347_W3004748802.pdf    │
│  - 01449_W2019676265.pdf    │
│  - ...                      │
└────────┬────────────────────┘
         │ 2. List & Download
         ▼
┌─────────────────────────────┐
│    Vast.ai GPU Instance     │
│  - RTX 4090 / A6000         │
│  - Dolphin Model (GPU)      │
│  - Processing Script        │
│                             │
│  Process:                   │
│  PDF → Images → Layout →    │
│  Elements → Markdown        │
└────────┬────────────────────┘
         │ 3. Upload Results
         ▼
┌─────────────────────────────┐
│    S3 Output Bucket         │
│ s3://bucket/pdf-output/     │
│  ├── 00347_W3004748802/     │
│  │   ├── document.json      │
│  │   ├── document.md        │
│  │   └── figures/           │
│  │       ├── figure_001.png │
│  │       └── figure_002.png │
│  └── 01449_W2019676265/     │
│      └── ...                │
└─────────────────────────────┘
```

### Storage Structure

```
s3://your-bucket/
├── pdf-input/                    # Raw PDFs uploaded from local machine
│   ├── 00347_W3004748802_Small_firms_and_patenting_revisited.pdf
│   ├── 01449_W2019676265_Appropriability_Mechanism.pdf
│   ├── 02961_W2267349102_Reflecting_on_Acquisition.pdf
│   └── ... (1000s of PDFs)
│
├── pdf-output/                   # Processed outputs (one folder per PDF)
│   ├── 00347_W3004748802/
│   │   ├── document.json        # Full parsing results with metadata
│   │   ├── document.md          # Structured markdown
│   │   └── figures/             # Extracted figures
│   │       ├── figure_001.png
│   │       ├── figure_002.png
│   │       └── ...
│   ├── 01449_W2019676265/
│   │   └── ...
│   └── ...
│
└── processing-logs/              # Processing metadata
    ├── batch-2025-11-07.log     # Detailed processing log
    ├── errors.json              # Failed PDFs with error details
    └── summary.json             # Batch statistics
```

## Components

### 1. Processing Script (`vast_batch_process.py`)

**Purpose**: Main orchestration script that runs on Vast.ai

**Key Functions**:
- Initialize S3 client and Dolphin model
- Discover PDFs to process (skip already-completed)
- Download → Process → Upload loop
- Error handling and logging
- Generate processing summary

**Configuration via Environment Variables**:
```bash
# S3 Credentials (AWS S3)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=secret...
AWS_REGION=eu-north-1
S3_BUCKET=my-pdf-bucket

# OR for Infomaniak Swift (S3-compatible)
AWS_ACCESS_KEY_ID=infomaniak_key
AWS_SECRET_ACCESS_KEY=infomaniak_secret
S3_ENDPOINT_URL=https://s3.pub1.infomaniak.cloud
S3_BUCKET=my-pdf-bucket

# Optional Configuration
INPUT_PREFIX=pdf-input/          # Default: pdf-input/
OUTPUT_PREFIX=pdf-output/        # Default: pdf-output/
BATCH_SIZE=16                    # Dolphin batch size (default: 16)
TEMP_DIR=/tmp                    # Temporary storage
```

**Command Line Arguments**:
```bash
python vast_batch_process.py \
  --input-prefix pdf-input/ \
  --output-prefix pdf-output/ \
  --batch-size 16 \
  --max-pdfs 1000                # Optional: process only N PDFs
  --start-from 100               # Optional: skip first N PDFs
```

### 2. Docker Container

**Dockerfile**:
```dockerfile
FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy project code
COPY rag_pipeline /workspace/rag_pipeline
COPY vast_batch_process.py /workspace/
COPY requirements.txt /workspace/

# Install Python dependencies
RUN uv pip install --system -r requirements.txt

# Model weights already included in rag_pipeline/pdf_parsing/models/
# (copied during build - 796MB safetensors file)

# Set working directory
WORKDIR /workspace

# Default command
CMD ["python", "vast_batch_process.py"]
```

**Build and Push**:
```bash
docker build -t yourusername/pdf-parser:latest .
docker push yourusername/pdf-parser:latest
```

### 3. S3 Storage Backend

**Supported Providers**:
- **AWS S3**: Standard S3 service (use boto3 defaults)
- **Infomaniak Swiss Backup**: S3-compatible (set custom endpoint)
- **Any S3-compatible**: MinIO, DigitalOcean Spaces, etc.

**Access Configuration**:

For AWS S3:
```python
import boto3

s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'eu-north-1')
)
```

For Infomaniak or other S3-compatible:
```python
import boto3

s3_client = boto3.client(
    's3',
    endpoint_url=os.getenv('S3_ENDPOINT_URL'),  # e.g., https://s3.pub1.infomaniak.cloud
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name='eu-north-1'  # Required but not used by custom endpoints
)
```

### 4. Vast.ai GPU Instance

**Recommended Instance Specs**:
- **GPU**: RTX 4090 (preferred), RTX 3090, or A6000
- **VRAM**: 24GB minimum (Dolphin model uses ~8-12GB)
- **RAM**: 32GB+ system RAM
- **Disk**: 100GB+ for temporary PDF storage
- **Network**: Good upload speed for S3 transfers
- **Reliability Score**: >0.95 (choose stable providers)

**Pricing** (as of 2025-11):
- RTX 4090: $0.30-0.50/hour
- RTX 3090: $0.20-0.40/hour
- A6000: $0.40-0.70/hour

**Selection Command**:
```bash
vastai search offers 'reliability > 0.95 gpu_name=RTX_4090 disk_space >= 100 num_gpus=1'
```

## Processing Workflow

### Script Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. INITIALIZATION                                           │
├─────────────────────────────────────────────────────────────┤
│ • Parse command line arguments                              │
│ • Load environment variables (S3 credentials)               │
│ • Initialize S3 client (boto3)                              │
│ • Test S3 connection (list bucket)                          │
│ • Load Dolphin model into GPU memory (~30 seconds)          │
│ • Create temporary directory for downloads                  │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. DISCOVERY PHASE                                          │
├─────────────────────────────────────────────────────────────┤
│ • List all PDFs in S3 input prefix                          │
│   → s3.list_objects_v2(Bucket, Prefix='pdf-input/')         │
│ • List already-processed outputs in S3 output prefix        │
│   → s3.list_objects_v2(Bucket, Prefix='pdf-output/')        │
│ • Calculate: to_process = input_pdfs - completed_pdfs       │
│ • Print summary:                                            │
│   "Found 1,234 PDFs in input"                               │
│   "234 already processed (skipping)"                        │
│   "1,000 remaining to process"                              │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. PROCESSING LOOP (for each PDF)                           │
├─────────────────────────────────────────────────────────────┤
│ FOR pdf in to_process:                                      │
│                                                             │
│   A. Download PDF from S3                                  │
│      → s3.download_file(bucket, key, '/tmp/current.pdf')   │
│      → Log: "[45/1000] Downloading 00347_W3004748802.pdf"  │
│                                                             │
│   B. Process with Dolphin Pipeline                         │
│      → config = PDFParsingConfig(output_dir='/tmp/output') │
│      → pipeline = PDFParsingPipeline(config)               │
│      → result = pipeline.parse_document('/tmp/current.pdf')│
│      → Outputs: JSON, Markdown, Figures                    │
│      → Time: ~2-3 minutes per 18-page PDF on RTX 4090      │
│                                                             │
│   C. Upload Results to S3                                  │
│      → Create output folder: pdf-output/{pdf_name}/        │
│      → Upload document.json                                │
│      → Upload document.md                                  │
│      → Upload all figures/ to figures/ subfolder           │
│      → Log: "[45/1000] ✓ Uploaded to s3://bucket/..."     │
│                                                             │
│   D. Cleanup                                               │
│      → Delete /tmp/current.pdf                             │
│      → Delete /tmp/output/* (free disk space)              │
│                                                             │
│   E. Progress Tracking                                     │
│      → Calculate: progress = (processed / total) * 100     │
│      → Estimate time remaining                             │
│      → Log: "Progress: 4.5% | Est. remaining: 47.2 hours"  │
│                                                             │
│   F. Error Handling (try/except around entire loop)        │
│      → If PDF fails: Log error, save to errors.json, SKIP  │
│      → If S3 upload fails: Retry 3x with backoff           │
│      → If critical error: Exit gracefully, save state      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. COMPLETION & CLEANUP                                     │
├─────────────────────────────────────────────────────────────┤
│ • Generate processing summary:                              │
│   - Total PDFs processed: 1,000                             │
│   - Successful: 987                                         │
│   - Failed: 13 (see errors.json)                            │
│   - Total time: 48.5 hours                                  │
│   - Average time per PDF: 2.9 minutes                       │
│   - Total cost: ~$24.25                                     │
│ • Upload summary.json to S3                                 │
│ • Upload processing.log to S3                               │
│ • Upload errors.json to S3                                  │
│ • Unload Dolphin model from GPU                             │
│ • Exit with status code 0 (success) or 1 (errors)           │
└─────────────────────────────────────────────────────────────┘
```

### Error Handling Strategy

**Three Tiers of Errors**:

1. **PDF-Level Errors** (non-fatal, skip and continue)
   - Corrupted PDF file
   - Dolphin model timeout on specific PDF
   - S3 upload fails after retries
   - **Action**: Log to `errors.json`, skip PDF, continue batch

2. **Transient Errors** (retry with backoff)
   - S3 connection timeout
   - Rate limiting from S3
   - Temporary network issues
   - **Action**: Retry 3x with exponential backoff (1s, 2s, 4s)

3. **Fatal Errors** (exit immediately)
   - Dolphin model crashes (CUDA out of memory)
   - S3 credentials invalid
   - Vast.ai instance out of disk space
   - **Action**: Save state, upload logs, exit with error code

**Resume Capability**:
Since the script checks S3 for already-completed outputs, it's automatically resumable:
- If Vast.ai crashes mid-batch → Just restart script
- Script re-scans S3, skips completed PDFs, resumes from where it left off
- No additional state management needed

## Deployment Guide

### Step 1: Prepare Local PDFs

Upload your PDFs from `data/openalex/pdfs/` to S3:

**For AWS S3**:
```bash
# Install AWS CLI
uv pip install awscli

# Configure credentials
aws configure

# Upload PDFs
aws s3 sync data/openalex/pdfs/ s3://your-bucket/pdf-input/ \
  --storage-class STANDARD_IA  # Cheaper storage for infrequent access
```

**For Infomaniak Swift**:
```bash
# Configure with custom endpoint
aws configure set aws_access_key_id YOUR_INFOMANIAK_KEY
aws configure set aws_secret_access_key YOUR_INFOMANIAK_SECRET

# Upload with custom endpoint
aws s3 sync data/openalex/pdfs/ s3://your-bucket/pdf-input/ \
  --endpoint-url https://s3.pub1.infomaniak.cloud
```

Verify upload:
```bash
aws s3 ls s3://your-bucket/pdf-input/ --recursive | wc -l
# Should show number of PDFs uploaded
```

### Step 2: Build and Push Docker Image

```bash
# Build Docker image
docker build -t yourusername/pdf-parser:latest .

# Test locally (optional)
docker run --rm \
  -e AWS_ACCESS_KEY_ID=xxx \
  -e AWS_SECRET_ACCESS_KEY=xxx \
  -e S3_BUCKET=your-bucket \
  yourusername/pdf-parser:latest \
  python vast_batch_process.py --max-pdfs 1  # Process just 1 PDF to test

# Push to Docker Hub
docker login
docker push yourusername/pdf-parser:latest
```

### Step 3: Launch Vast.ai Instance

**Option A: Via Vast.ai CLI**

```bash
# Install Vast.ai CLI
uv pip install vast

# Login
vastai set api-key YOUR_VASTAI_API_KEY

# Search for suitable GPU
vastai search offers 'reliability > 0.95 gpu_name=RTX_4090 disk_space >= 100 num_gpus=1' \
  --order 'dph_total+'  # Sort by price (cheapest first)

# Create instance (replace OFFER_ID from search results)
vastai create instance OFFER_ID \
  --image yourusername/pdf-parser:latest \
  --disk 100 \
  --env AWS_ACCESS_KEY_ID=xxx \
  --env AWS_SECRET_ACCESS_KEY=xxx \
  --env S3_BUCKET=your-bucket \
  --env S3_ENDPOINT_URL=https://s3.pub1.infomaniak.cloud  # Only if using Infomaniak

# Note the INSTANCE_ID returned
```

**Option B: Via Vast.ai Web UI**

1. Go to https://cloud.vast.ai/
2. Click "Create" → "Custom Instance"
3. Search for GPU: RTX 4090, reliability >0.95
4. Set image: `yourusername/pdf-parser:latest`
5. Set environment variables in "Environment" tab
6. Set disk space: 100GB
7. Launch instance

### Step 4: Start Processing

SSH into the instance:
```bash
# Get SSH command
vastai ssh-url INSTANCE_ID

# Or directly
vastai ssh INSTANCE_ID
```

Inside the instance:
```bash
# Verify environment
echo $S3_BUCKET
echo $AWS_ACCESS_KEY_ID

# Test S3 connection
python -c "import boto3; s3=boto3.client('s3'); print(s3.list_buckets())"

# Start processing
python vast_batch_process.py \
  --input-prefix pdf-input/ \
  --output-prefix pdf-output/ \
  --batch-size 16 \
  > processing.log 2>&1 &

# Monitor progress
tail -f processing.log
```

**Run in Background (tmux)**:
```bash
# Start tmux session
tmux new -s pdf-processing

# Run script
python vast_batch_process.py

# Detach: Ctrl+B then D
# Reattach: tmux attach -t pdf-processing
```

### Step 5: Monitor Progress

**From Vast.ai Instance**:
```bash
# Watch logs
tail -f processing.log

# Check GPU usage
nvidia-smi

# Check disk usage
df -h /tmp
```

**From Local Machine**:
```bash
# Count completed PDFs in S3
aws s3 ls s3://your-bucket/pdf-output/ \
  --recursive \
  --endpoint-url https://s3.pub1.infomaniak.cloud \
  | grep "document.json" \
  | wc -l

# Check latest log
aws s3 cp s3://your-bucket/processing-logs/batch-2025-11-07.log - \
  | tail -20
```

**Vast.ai Dashboard**:
- Monitor instance status
- Check GPU utilization
- Track costs in real-time

### Step 6: Retrieve Results

When processing completes:

```bash
# Download all processed files
aws s3 sync s3://your-bucket/pdf-output/ ./processed_pdfs/ \
  --endpoint-url https://s3.pub1.infomaniak.cloud

# Download summary and logs
aws s3 cp s3://your-bucket/processing-logs/summary.json ./
aws s3 cp s3://your-bucket/processing-logs/errors.json ./

# Destroy Vast.ai instance (stop paying)
vastai destroy instance INSTANCE_ID
```

## Cost Estimates

### Vast.ai GPU Rental

**Processing Speed** (RTX 4090):
- Average PDF (18 pages): ~2-3 minutes
- 1,000 PDFs: ~40-50 hours

**Cost Calculation**:
- RTX 4090: $0.35/hour (typical price)
- 50 hours × $0.35/hour = **$17.50**

**Alternative GPUs**:
- RTX 3090 (slower): ~60 hours × $0.30/hour = $18.00
- A6000 (faster): ~35 hours × $0.45/hour = $15.75

### S3 Storage Costs

**Input Storage** (1,000 PDFs @ 5MB average):
- Total: 5GB
- AWS S3 Standard: $0.023/GB/month = **$0.12/month**
- Infomaniak Swiss Backup: €0.0065/GB/month = **$0.04/month**

**Output Storage** (JSON + Markdown + Figures):
- Estimate: 3× input size = 15GB
- AWS S3: $0.35/month
- Infomaniak: $0.10/month

**Transfer Costs**:
- Upload to S3: Free
- Download from S3: AWS charges $0.09/GB after 100GB free tier
- Infomaniak: First 1TB free per month

### Total Estimated Cost (1,000 PDFs)

| Component | Cost |
|-----------|------|
| Vast.ai GPU (50 hours) | $17.50 |
| S3 Storage (1 month) | $0.35 |
| S3 Transfer | $1.35 |
| **Total** | **~$19.20** |

**Cheaper with Infomaniak**: ~$17.60 total

**Per-PDF Cost**: ~$0.02 per PDF

## Monitoring & Logging

### Log Levels

The script outputs structured logs:

```
[2025-11-07 20:30:15] INFO: Initializing S3 client...
[2025-11-07 20:30:16] INFO: S3 connection successful (bucket: my-bucket)
[2025-11-07 20:30:16] INFO: Loading Dolphin model from ./models/...
[2025-11-07 20:30:45] INFO: Model loaded on cuda:0 (23.5GB VRAM used)
[2025-11-07 20:30:46] INFO: Scanning S3 for input PDFs...
[2025-11-07 20:30:50] INFO: Found 1,234 PDFs in s3://bucket/pdf-input/
[2025-11-07 20:30:51] INFO: Found 234 already processed in s3://bucket/pdf-output/
[2025-11-07 20:30:51] INFO: *** Starting processing of 1,000 remaining PDFs ***
[2025-11-07 20:32:15] INFO: [1/1000] Downloading 00347_W3004748802.pdf (4.2MB)...
[2025-11-07 20:32:18] INFO: [1/1000] Processing 18 pages...
[2025-11-07 20:34:35] INFO: [1/1000] Extracted 268 elements
[2025-11-07 20:34:38] INFO: [1/1000] Uploading results to S3...
[2025-11-07 20:34:42] INFO: [1/1000] ✓ Complete (2m 27s) | Upload: s3://bucket/pdf-output/00347/
[2025-11-07 20:34:43] INFO: Progress: 0.1% (1/1000) | Avg: 2.45 min/PDF | Est. remaining: 40.8 hours
[2025-11-07 20:36:20] ERROR: [2/1000] Failed to download 01449_W2019676265.pdf: Connection timeout
[2025-11-07 20:36:20] WARNING: [2/1000] Retrying (attempt 2/3)...
[2025-11-07 20:36:25] INFO: [2/1000] ✓ Download successful on retry
[2025-11-07 20:39:45] INFO: [2/1000] ✓ Complete (3m 22s)
```

### Summary Report (`summary.json`)

Generated at completion:
```json
{
  "batch_id": "batch-2025-11-07-203015",
  "start_time": "2025-11-07T20:30:15Z",
  "end_time": "2025-11-09T21:45:32Z",
  "duration_hours": 49.25,
  "total_pdfs": 1000,
  "successful": 987,
  "failed": 13,
  "average_time_per_pdf_seconds": 178,
  "total_elements_extracted": 264580,
  "total_pages_processed": 18234,
  "s3_bucket": "my-bucket",
  "input_prefix": "pdf-input/",
  "output_prefix": "pdf-output/",
  "gpu_used": "RTX 4090",
  "estimated_cost_usd": 17.24
}
```

### Error Report (`errors.json`)

Lists all failed PDFs:
```json
{
  "errors": [
    {
      "pdf": "01449_W2019676265.pdf",
      "error": "ConnectionTimeout: Failed to download from S3 after 3 retries",
      "timestamp": "2025-11-07T20:36:20Z"
    },
    {
      "pdf": "05234_W3847562123.pdf",
      "error": "LayoutParsingError: Dolphin model timeout (>300s)",
      "timestamp": "2025-11-08T08:15:42Z"
    }
  ],
  "total_errors": 13,
  "error_rate": 0.013
}
```

## Troubleshooting

### Common Issues

**1. Model Loading Fails**
```
Error: CUDA out of memory
```
**Solution**: Choose GPU with more VRAM (24GB+ required) or reduce batch size

**2. S3 Connection Fails**
```
Error: botocore.exceptions.NoCredentialsError
```
**Solution**: Verify environment variables are set correctly in Vast.ai

**3. Slow Processing**
```
Processing takes >10 minutes per PDF
```
**Solution**: Check if running on CPU instead of GPU. Run `nvidia-smi` to verify

**4. Disk Full**
```
Error: No space left on device
```
**Solution**: Increase disk allocation in Vast.ai or ensure cleanup is working

**5. Instance Disconnects**
```
SSH connection lost
```
**Solution**: Use `tmux` to run in background. Process continues even if SSH drops.

### Reprocessing Failed PDFs

To reprocess only the PDFs that failed:

```bash
# Download error list
aws s3 cp s3://bucket/processing-logs/errors.json ./

# Delete failed outputs from S3 (so script sees them as unprocessed)
python delete_failed_outputs.py errors.json

# Re-run script (it will only process the failed ones)
python vast_batch_process.py
```

## Security Considerations

### S3 Credentials
- **Never commit credentials to Git**
- Use environment variables or AWS IAM roles
- Create S3 user with minimal permissions:
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
        "Resource": [
          "arn:aws:s3:::your-bucket",
          "arn:aws:s3:::your-bucket/*"
        ]
      }
    ]
  }
  ```

### Vast.ai Instance
- Use SSH key authentication (not passwords)
- Don't expose ports publicly
- Destroy instance immediately after processing completes
- Monitor for unauthorized access in Vast.ai dashboard

## Future Enhancements

### Potential Improvements (Not Implemented)

1. **Progress Tracking Database**
   - Use SQLite or JSON file to track each PDF's state
   - Enables better resume capability and progress queries

2. **Parallel Processing**
   - Run multiple Dolphin models on multi-GPU instances
   - Could process 2-4 PDFs simultaneously
   - Requires careful GPU memory management

3. **Smart Retry Logic**
   - Exponentially back off on transient errors
   - Skip PDFs that consistently fail
   - Separate queue for retry attempts

4. **Cost Optimization**
   - Use Vast.ai spot instances (cheaper but less reliable)
   - Automatically switch to cheaper GPU if available
   - Compress outputs before uploading to S3

5. **Real-time Dashboard**
   - Web UI showing live progress
   - Deployed on separate server
   - Reads logs from S3 and displays metrics

## Conclusion

This simple batch processing architecture provides:
- ✅ **Reliability**: Automatic resume on failures
- ✅ **Cost-effectiveness**: ~$0.02 per PDF
- ✅ **Simplicity**: Single Python script, minimal dependencies
- ✅ **Flexibility**: Works with any S3-compatible storage

The stateless design means no complex infrastructure, but you get automatic resume capability by checking S3 for completed work.

**Next Steps**:
1. Upload PDFs to S3
2. Build and push Docker image
3. Launch Vast.ai instance
4. Run processing script
5. Monitor and wait for completion
6. Download results from S3

**Estimated Timeline**:
- Setup: 1-2 hours
- Processing 1,000 PDFs: 40-50 hours
- Total cost: ~$17-25

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-07