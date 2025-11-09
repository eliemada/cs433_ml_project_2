# Distributed PDF Processing System Design

**Date**: 2025-11-09
**Author**: Design validated with user
**Status**: Approved for implementation

## Executive Summary

Design for a distributed batch processing system to convert 4000 PDFs to markdown using the Dolphin model across multiple AWS EC2 GPU instances in parallel. The system maximizes throughput within a $100 AWS budget by using Spot instances and simple work distribution to avoid duplicate processing.

## Problem Statement

- **Input**: 4000 PDF files stored in AWS S3
- **Processing**: Each PDF requires 2-3 minutes of GPU processing with Dolphin model
- **Constraint**: $100 AWS budget
- **Requirement**: No duplicate processing (don't process the same PDF twice)
- **Output**: Markdown files uploaded back to S3

**Sequential processing time**: ~133-200 hours (unacceptable)
**Target parallel processing time**: ~8-24 hours with 5-10 instances

## Architecture Overview

### High-Level Design

```
┌─────────────────────────────────────────────────────────┐
│           S3 Input Bucket (4000 PDFs)                   │
│           s3://cs433-rag-project2/raw_pdfs/             │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┬────────────┬──────────┐
        │            │            │            │          │
        ▼            ▼            ▼            ▼          ▼
  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
  │ Worker 0│  │ Worker 1│  │ Worker 2│  │ Worker 3│  │ Worker 4│
  │ (EC2)   │  │ (EC2)   │  │ (EC2)   │  │ (EC2)   │  │ (EC2)   │
  │ PDFs    │  │ PDFs    │  │ PDFs    │  │ PDFs    │  │ PDFs    │
  │ 0,5,10..│  │ 1,6,11..│  │ 2,7,12..│  │ 3,8,13..│  │ 4,9,14..│
  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘
       │            │            │            │            │
       │     Each worker runs Dolphin model on GPU        │
       │            │            │            │            │
       └────────────┴────────────┴────────────┴────────────┘
                                 │
                                 ▼
                   ┌──────────────────────────┐
                   │  S3 Output Bucket        │
                   │  s3://bucket/processed/  │
                   │  - file1.md              │
                   │  - file2.md              │
                   │  - ...                   │
                   └──────────────────────────┘
```

### Key Design Principles

1. **Stateless Workers**: Each EC2 instance is independent and self-contained
2. **Deterministic Work Distribution**: Workers use modulo arithmetic to claim PDFs (no coordination needed)
3. **Idempotent Processing**: Workers check S3 for existing output before processing
4. **Fail-Fast and Continue**: Individual PDF failures don't stop the entire batch
5. **Cost Optimization**: Use Spot instances and auto-termination

## Component Design

### 1. AWS EC2 Instance Configuration

**Instance Type**: `g4dn.xlarge`

| Specification | Value |
|--------------|-------|
| GPU | 1x NVIDIA T4 (16GB VRAM) |
| vCPUs | 4 cores |
| RAM | 16GB |
| Storage | 125GB SSD |
| On-Demand Cost | $0.526/hour |
| **Spot Cost** | **~$0.158/hour** (70% savings) |

**AMI**: AWS Deep Learning AMI (Ubuntu 22.04)
- Pre-installed: NVIDIA drivers, CUDA 11.8+, Docker with GPU support
- AMI ID: `ami-0c7217cdde317cfec` (us-east-1, verify current version)

**Budget Calculation** (with 5 Spot instances):
```
$100 budget ÷ $0.158/hour ÷ 5 instances = ~126 hours per instance
126 hours × 60 min/hour ÷ 2.5 min/PDF = ~3,024 PDFs processable per instance
5 instances × 3,024 = 15,120 PDFs total capacity >> 4,000 PDFs needed ✓

Expected wall-clock time: 4,000 PDFs ÷ 5 workers ÷ 24 PDFs/hour = ~33 hours
Expected cost: 5 instances × 33 hours × $0.158/hour = ~$26
```

**Recommendation**: Start with 5 instances to comfortably stay under budget with buffer for retries.

### 2. Work Distribution Strategy

**Problem**: Avoid duplicate work without coordination overhead.

**Solution**: Deterministic modulo-based partitioning.

```python
# Each worker gets assigned PDFs based on modulo arithmetic
# Worker 0: indices 0, 5, 10, 15, 20, ...
# Worker 1: indices 1, 6, 11, 16, 21, ...
# Worker 2: indices 2, 7, 12, 17, 22, ...
# etc.

all_pdfs = sorted(list_s3_objects(bucket, prefix="pdfs/"))

for i, pdf_key in enumerate(all_pdfs):
    if i % TOTAL_WORKERS == WORKER_ID:
        process_pdf(pdf_key)
```

**Advantages**:
- No central coordinator needed
- No database or locking required
- Perfect distribution (each worker gets ≈800 PDFs)
- Deterministic and reproducible

**Idempotency**: Before processing, check if output exists:
```python
output_key = pdf_key.replace("pdfs/", "processed/").replace(".pdf", ".md")
if s3.object_exists(output_bucket, output_key):
    skip_pdf()  # Already processed
```

### 3. Worker Container Design

**Base Image**: `ravinala/pdf-parser:latest` (existing)

**Enhancements Needed**:
1. Add worker script: `scripts/distributed_worker.py`
2. Modify entrypoint to accept worker parameters
3. Add S3 utilities for listing, downloading, uploading
4. Add progress logging to CloudWatch

**Environment Variables**:
```bash
WORKER_ID=0                           # Unique ID: 0, 1, 2, 3, 4
TOTAL_WORKERS=5                       # Total number of parallel workers
S3_INPUT_BUCKET=cs433-rag-project2    # Input PDFs bucket
S3_INPUT_PREFIX=raw_pdfs/             # Prefix for PDFs
S3_OUTPUT_BUCKET=cs433-rag-project2   # Output markdown bucket
S3_OUTPUT_PREFIX=processed/           # Prefix for outputs
AWS_DEFAULT_REGION=us-east-1          # AWS region
MAX_RETRIES=2                         # Retry failed PDFs this many times
```

**Container Entrypoint**:
```dockerfile
# Dockerfile enhancement
COPY scripts/distributed_worker.py /app/distributed_worker.py
CMD ["python", "/app/distributed_worker.py"]
```

### 4. Worker Script Logic

**File**: `scripts/distributed_worker.py`

**Main Algorithm**:
```python
def main():
    # 1. Initialize
    worker_id = int(os.getenv("WORKER_ID"))
    total_workers = int(os.getenv("TOTAL_WORKERS"))
    s3_client = boto3.client('s3')

    # 2. List all PDFs
    all_pdfs = list_pdfs_from_s3(s3_client, INPUT_BUCKET, INPUT_PREFIX)
    all_pdfs.sort()  # Ensure deterministic ordering

    # 3. Filter to this worker's slice
    my_pdfs = [pdf for i, pdf in enumerate(all_pdfs)
               if i % total_workers == worker_id]

    logger.info(f"Worker {worker_id}: Assigned {len(my_pdfs)} PDFs")

    # 4. Process each PDF
    for pdf_key in my_pdfs:
        try:
            # Check if already processed
            output_key = get_output_key(pdf_key)
            if s3_object_exists(s3_client, OUTPUT_BUCKET, output_key):
                logger.info(f"Skipping {pdf_key} (already processed)")
                continue

            # Download PDF
            local_pdf = download_from_s3(s3_client, INPUT_BUCKET, pdf_key)

            # Process with Dolphin
            markdown_content = process_pdf_with_dolphin(local_pdf)

            # Upload markdown
            upload_to_s3(s3_client, OUTPUT_BUCKET, output_key, markdown_content)

            # Cleanup
            os.remove(local_pdf)

            logger.info(f"✓ Processed {pdf_key}")

        except Exception as e:
            logger.error(f"✗ Failed {pdf_key}: {e}")
            record_failure(pdf_key, str(e))
            continue  # Continue with next PDF

    # 5. Save failure report
    upload_failure_report(worker_id)
    logger.info(f"Worker {worker_id} completed!")
```

**Error Handling**:
- Individual PDF failures are logged but don't stop processing
- Failed PDFs are recorded in `s3://bucket/failures/worker-{id}-failures.json`
- Structured logs sent to CloudWatch for debugging

**Spot Interruption Handling**:
```python
# AWS provides 2-minute warning before Spot termination
# Listen to instance metadata endpoint for interruption notice
def handle_spot_interruption():
    logger.warning("Spot interruption detected, graceful shutdown...")
    save_current_progress()
    sys.exit(0)
```

### 5. Deployment Strategy

**Launch Script**: `scripts/launch_distributed_workers.py`

**Responsibilities**:
1. Validate AWS credentials and permissions
2. Request 5x `g4dn.xlarge` Spot instances
3. Use EC2 User Data to bootstrap each instance
4. Tag instances for easy identification
5. Set up CloudWatch log groups
6. Print instance IDs and monitoring URLs

**EC2 User Data Script** (runs on instance boot):
```bash
#!/bin/bash
set -e

# Pull latest Docker image
docker pull ravinala/pdf-parser:latest

# Run worker container with GPU support
docker run --gpus all \
  --rm \
  -e WORKER_ID=${WORKER_ID} \
  -e TOTAL_WORKERS=5 \
  -e S3_INPUT_BUCKET=cs433-rag-project2 \
  -e S3_INPUT_PREFIX=raw_pdfs/ \
  -e S3_OUTPUT_BUCKET=cs433-rag-project2 \
  -e S3_OUTPUT_PREFIX=processed/ \
  -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
  -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
  -e AWS_DEFAULT_REGION=us-east-1 \
  ravinala/pdf-parser:latest

# Auto-terminate when processing completes
shutdown -h now
```

**Spot Instance Request Configuration**:
```json
{
  "InstanceType": "g4dn.xlarge",
  "InstanceCount": 5,
  "SpotPrice": "0.30",  // Max price (well above typical ~$0.158)
  "ImageId": "ami-0c7217cdde317cfec",
  "SecurityGroupIds": ["sg-default"],
  "IamInstanceProfile": {
    "Name": "EC2-S3-Access"  // IAM role with S3 read/write permissions
  },
  "BlockDeviceMappings": [
    {
      "DeviceName": "/dev/sda1",
      "Ebs": {
        "VolumeSize": 125,
        "VolumeType": "gp3"
      }
    }
  ],
  "UserData": "<base64-encoded-script>",
  "TagSpecifications": [
    {
      "ResourceType": "instance",
      "Tags": [
        {"Key": "Name", "Value": "pdf-worker-{WORKER_ID}"},
        {"Key": "Project", "Value": "pdf-processing"},
        {"Key": "WorkerID", "Value": "{WORKER_ID}"}
      ]
    }
  ]
}
```

### 6. Monitoring and Progress Tracking

**CloudWatch Logs**:
- Log group: `/aws/ec2/pdf-workers/`
- Log streams: `worker-0`, `worker-1`, ..., `worker-4`
- Retention: 7 days

**Log Events**:
```
[Worker 0] Starting processing: 800 PDFs assigned
[Worker 0] Progress: 50/800 PDFs (6.25%) - ETA: 31.2 hours
[Worker 0] ✓ Processed: pdfs/paper_0123.pdf -> processed/paper_0123.md
[Worker 0] ✗ Failed: pdfs/corrupt_file.pdf - Error: Invalid PDF
[Worker 0] Completed: 798/800 PDFs, 2 failures
```

**Simple Monitoring Dashboard** (optional):
```python
# scripts/monitor_progress.py
# Polls S3 output bucket and shows real-time progress
# Output:
# Worker 0: ████████░░ 234/800 (29%) | ETA: 18.2h
# Worker 1: ████████░░ 245/800 (31%) | ETA: 17.8h
# ...
# Total:    ████░░░░░░ 1,123/4,000 (28%) | $4.23 spent
```

### 7. Cost Control Mechanisms

**1. Budget Alerts**:
```python
# AWS Budgets configuration
{
  "BudgetName": "PDF-Processing-Budget",
  "BudgetLimit": {"Amount": "100", "Unit": "USD"},
  "Alerts": [
    {"Threshold": 50, "Email": "your-email@example.com"},
    {"Threshold": 90, "Email": "your-email@example.com"}
  ]
}
```

**2. Max Runtime Protection**:
```python
# In User Data script
# Kill instance after 48 hours (safety net)
echo "shutdown -h now" | at now + 48 hours
```

**3. Spot Instance Benefits**:
- Pay only while processing (auto-terminates when done)
- 70% cheaper than on-demand
- Low interruption risk for 24-48 hour jobs

**4. Cost Estimate**:
```
Scenario 1: All 5 workers complete successfully
- 800 PDFs/worker × 2.5 min/PDF = 2,000 min = 33.3 hours/worker
- 5 workers × 33.3 hours × $0.158/hour = $26.30

Scenario 2: 20% of PDFs need retry (worst case)
- 33.3 hours × 1.2 = 40 hours/worker
- 5 workers × 40 hours × $0.158/hour = $31.60

Safety margin: $100 budget - $32 expected = $68 buffer ✓
```

## Implementation Plan

### Phase 1: Code Preparation (1-2 hours)
- [ ] Create `scripts/distributed_worker.py` with main processing loop
- [ ] Add S3 utility functions (list, download, upload, check exists)
- [ ] Integrate with existing Dolphin pipeline code
- [ ] Add CloudWatch logging setup
- [ ] Test locally with small batch (5 PDFs)

### Phase 2: Docker Image Update (30 min)
- [ ] Update Dockerfile to include worker script
- [ ] Build new image: `ravinala/pdf-parser:v2-distributed`
- [ ] Push to Docker Hub
- [ ] Test container locally with environment variables

### Phase 3: AWS Infrastructure Setup (30 min)
- [ ] Create IAM role: `EC2-S3-PDF-Processing` with S3 read/write permissions
- [ ] Create security group (minimal: SSH only from your IP)
- [ ] Set up CloudWatch log group: `/aws/ec2/pdf-workers/`
- [ ] Configure AWS Budget alert ($50 and $90 thresholds)

### Phase 4: Launch Script Development (1 hour)
- [ ] Create `scripts/launch_distributed_workers.py` using boto3
- [ ] Implement Spot instance request logic
- [ ] Generate unique User Data for each worker (WORKER_ID 0-4)
- [ ] Add instance tagging and monitoring setup
- [ ] Test launch with 1 instance first

### Phase 5: Production Launch (5 min)
- [ ] Run launch script to start 5 workers
- [ ] Verify all instances started in AWS Console
- [ ] Verify CloudWatch logs are flowing
- [ ] Monitor progress for first 30 minutes

### Phase 6: Monitoring Phase (24-48 hours)
- [ ] Check progress every 4-6 hours
- [ ] Review CloudWatch logs for errors
- [ ] Monitor AWS budget usage
- [ ] Verify markdown files appearing in S3

### Phase 7: Completion and Cleanup (1 hour)
- [ ] Verify all instances auto-terminated
- [ ] Check S3 for 4,000 markdown files
- [ ] Review failure reports: `s3://bucket/failures/worker-*-failures.json`
- [ ] Re-run failed PDFs if needed (single instance)
- [ ] Delete CloudWatch logs (optional, saves $0.50/GB/month)

## File Structure

```
project-2-rag/
├── scripts/
│   ├── distributed_worker.py           # Main worker script (NEW)
│   ├── launch_distributed_workers.py   # Launch script (NEW)
│   ├── monitor_progress.py             # Optional monitoring (NEW)
│   └── utils/
│       ├── s3_utils.py                 # S3 helper functions (NEW)
│       └── cloudwatch_logger.py        # CloudWatch integration (NEW)
├── docker/
│   └── Dockerfile.distributed          # Enhanced Dockerfile (NEW)
├── docs/
│   └── plans/
│       └── 2025-11-09-distributed-pdf-processing-design.md  # This file
└── (existing project files...)
```

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **Spot instance interruptions** | Workers check for existing output (idempotent), can resume |
| **Individual PDF failures** | Fail-fast per PDF, log failures, continue processing |
| **Cost overrun** | Budget alerts at $50/$90, max runtime limit (48h), auto-termination |
| **Network failures** | Retry logic in boto3 (3 retries default), exponential backoff |
| **Duplicate processing** | Deterministic work distribution + idempotency check |
| **Docker image pull failures** | Deep Learning AMI has Docker pre-configured, image is public |
| **Out of disk space** | Delete PDFs after processing, 125GB SSD per instance |
| **GPU out of memory** | Dolphin model fits in 16GB T4, tested in existing pipeline |

## Testing Strategy

**Test 1: Local Simulation** (before AWS launch)
```bash
# Simulate Worker 0 with 5 total workers on first 10 PDFs
docker run --gpus all \
  -e WORKER_ID=0 \
  -e TOTAL_WORKERS=5 \
  -e S3_INPUT_BUCKET=cs433-rag-project2 \
  -e S3_INPUT_PREFIX=raw_pdfs/ \
  ravinala/pdf-parser:v2-distributed

# Expected: Processes PDFs at indices 0, 5 (2 PDFs)
```

**Test 2: Single Instance in AWS** (before full launch)
```bash
# Launch just Worker 0 as Spot instance
python scripts/launch_distributed_workers.py --workers 1 --dry-run false

# Verify:
# - Instance launches successfully
# - Docker container starts
# - CloudWatch logs appear
# - Markdown files upload to S3
# - Instance terminates when done
```

**Test 3: Full Production Launch** (5 workers)
```bash
# Launch all 5 workers
python scripts/launch_distributed_workers.py --workers 5

# Monitor for 1 hour to ensure:
# - No duplicate processing
# - All workers making progress
# - Budget tracking accurate
```

## Success Criteria

- [ ] All 4,000 PDFs converted to markdown
- [ ] 0 duplicate processing (same PDF processed twice)
- [ ] <5% failure rate (<200 failed PDFs)
- [ ] Total cost < $50 (target), < $100 (maximum)
- [ ] Completion time < 48 hours wall-clock time
- [ ] All Spot instances auto-terminated upon completion
- [ ] Failure report generated for any failed PDFs

## Open Questions and Future Enhancements

**Open Questions**:
- Q: Should we process failures immediately or in a separate batch?
  - A: Separate batch after reviewing failure logs

**Future Enhancements**:
1. **Auto-scaling**: Add AWS Lambda to dynamically adjust worker count based on queue depth
2. **SQS Integration**: Use SQS queue instead of modulo distribution for more flexible scaling
3. **Checkpointing**: Save progress to DynamoDB for more granular resume capability
4. **Retry Logic**: Implement exponential backoff for transient failures
5. **Notification**: SNS notifications when batch completes
6. **Cost Dashboard**: Real-time cost tracking dashboard

## References

- AWS Deep Learning AMI: https://aws.amazon.com/releasenotes/aws-deep-learning-ami-ubuntu-22-04/
- EC2 Spot Best Practices: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-best-practices.html
- boto3 Documentation: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
- Existing PDF Parser: `/Users/eliebruno/Desktop/code/project-2-rag/rag_pipeline/pdf_parsing/`

---

**Next Steps**: Ready to implement? Let me know if you'd like to proceed with Phase 1 (code preparation).
