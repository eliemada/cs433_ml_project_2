# AWS EC2 Deployment Guide

Complete guide to deploying the distributed PDF processing system on AWS EC2 Spot instances.

## Overview

- **Goal**: Process 4,921 PDFs in parallel using 5 GPU instances
- **Cost**: ~$26-32 (well under $100 budget)
- **Time**: ~33-40 hours wall-clock time
- **Instances**: 5x g4dn.xlarge Spot instances ($0.158/hour each)

## Prerequisites

✅ Docker image pushed to Docker Hub: `ravinala/pdf-parser:v2-distributed`
✅ PDFs in S3: `s3://cs433-rag-project2/raw_pdfs/` (4,921 files)
✅ AWS account with credits
✅ AWS CLI configured with credentials

## Step 1: Set Up AWS Infrastructure

Create IAM role for EC2 instances to access S3:

```bash
# Install dependencies
pip install boto3

# Create IAM role
python scripts/setup_aws_infrastructure.py
```

This creates:
- IAM Role: `pdf-processing-user`
- Permissions: S3 read/write on `cs433-rag-project2` bucket

## Step 2: Test with Dry Run

Preview what will be launched without actually creating instances:

```bash
# Set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export S3_INPUT_BUCKET=cs433-rag-project2
export S3_OUTPUT_BUCKET=cs433-rag-project2

# Dry run
python scripts/launch_distributed_workers.py --dry-run
```

Expected output:
```
Validating prerequisites...
✓ AWS credentials found
✓ IAM role 'pdf-processing-user' exists
✓ Deep Learning AMI found: ami-xxxxx
✓ All prerequisites validated

🔍 DRY RUN MODE - No instances will be launched

Using AMI: ami-xxxxx

Launching worker 0/4...
  Would launch instance for worker 0
  User Data (preview):
#!/bin/bash
set -e
...
```

## Step 3: Launch Workers

If dry run looks good, launch for real:

```bash
# Launch 5 workers
python scripts/launch_distributed_workers.py --workers 5
```

You'll be prompted to confirm:
```
⚠️  About to launch 5 Spot instances:
   Instance type: g4dn.xlarge
   Max price: $0.30/hour
   Region: eu-north-1
   Estimated cost: ~$31.60 for 40 hours

Continue? [y/N]: y
```

The script will:
1. Launch 5 Spot instance requests
2. Each instance gets unique WORKER_ID (0-4)
3. Instances auto-start Docker containers
4. Print monitoring commands

## Step 4: Monitor Progress

### Option A: Real-time Monitoring Script

```bash
# Continuous monitoring (updates every 60s)
python scripts/monitor_progress.py

# Single status check
python scripts/monitor_progress.py --once
```

Output:
```
[16:45:23] Workers: 5 | Processed: 1,234/4,921 (25.1%) | Rate: 37.3 PDF/hr | ETA: 98.9h
```

### Option B: Manual Checks

**Check Spot requests:**
```bash
aws ec2 describe-spot-instance-requests \
  --region eu-north-1 \
  --filters Name=tag:Project,Values=pdf-processing
```

**Check running instances:**
```bash
aws ec2 describe-instances \
  --region eu-north-1 \
  --filters Name=tag:Project,Values=pdf-processing \
           Name=instance-state-name,Values=running
```

**Check S3 progress:**
```bash
# Count processed PDFs
aws s3 ls s3://cs433-rag-project2/processed/ | grep "PRE" | wc -l

# Or count document.md files
aws s3 ls s3://cs433-rag-project2/processed/ --recursive | grep "document.md" | wc -l
```

**View worker logs (SSH):**
```bash
# Get instance ID from describe-instances above
ssh -i your-key.pem ubuntu@instance-public-ip

# View logs
sudo tail -f /var/log/user-data.log
```

## Step 5: Verify Completion

Workers automatically shut down when finished. Check:

```bash
# Should show 0 running instances
aws ec2 describe-instances \
  --region eu-north-1 \
  --filters Name=tag:Project,Values=pdf-processing \
           Name=instance-state-name,Values=running
```

**Check output:**
```bash
# Should show 4,921 folders
aws s3 ls s3://cs433-rag-project2/processed/ | grep "PRE" | wc -l

# Check for failures
aws s3 ls s3://cs433-rag-project2/failures/
```

## Troubleshooting

### Spot Requests Not Fulfilling

**Issue**: Spot requests stay in "pending" state

**Solution**:
- Check Spot pricing: instances may be unavailable at your max price
- Increase `--max-price` (e.g., `--max-price 0.50`)
- Try different availability zone or region
- Use on-demand instances (more expensive)

### Workers Failing Immediately

**Issue**: Instances start then terminate quickly

**Check logs**:
```bash
# In AWS Console:
# EC2 → Instances → Select instance → Actions → Monitor and troubleshoot → Get system log

# Or via CLI:
aws ec2 get-console-output --instance-id i-xxxxx
```

**Common causes**:
- Docker image pull failed (check Docker Hub)
- AWS credentials invalid
- Dolphin model loading error
- Out of GPU memory

### No Progress in S3

**Issue**: Instances running but no files in S3

**Debug**:
```bash
# SSH into instance
ssh -i your-key.pem ubuntu@instance-ip

# Check Docker container
sudo docker ps -a

# View container logs
sudo docker logs <container-id>

# Check user-data execution
sudo tail -100 /var/log/user-data.log
```

### High Failure Rate

**Check failure reports**:
```bash
# Download failure reports
aws s3 cp s3://cs433-rag-project2/failures/ ./failures/ --recursive

# View
cat failures/worker-0-failures.json
```

**Common failures**:
- Corrupted PDFs
- PDFs with no text
- Out of memory (reduce batch size)

## Cost Management

### Monitor Spending

```bash
# Check current month costs
aws ce get-cost-and-usage \
  --time-period Start=2025-11-01,End=2025-11-30 \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --group-by Type=SERVICE
```

### Set Up Budget Alerts

```bash
# Create budget (via Console is easier)
# AWS Console → Billing → Budgets → Create budget
# Set threshold: $50 and $90
```

### Emergency Stop

If costs are running away:

```bash
# Cancel all Spot requests
aws ec2 cancel-spot-instance-requests \
  --spot-instance-request-ids $(aws ec2 describe-spot-instance-requests \
    --filters Name=tag:Project,Values=pdf-processing \
    --query 'SpotInstanceRequests[*].SpotInstanceRequestId' \
    --output text)

# Terminate all instances
aws ec2 terminate-instances \
  --instance-ids $(aws ec2 describe-instances \
    --filters Name=tag:Project,Values=pdf-processing \
    --query 'Reservations[*].Instances[*].InstanceId' \
    --output text)
```

## Advanced Options

### Use On-Demand Instead of Spot

Modify `launch_distributed_workers.py`:
```python
# Replace request_spot_instances with run_instances
response = self.ec2.run_instances(
    ImageId=ami_id,
    InstanceType=self.instance_type,
    MinCount=1,
    MaxCount=1,
    # ... rest of configuration
)
```

**Cost**: ~$0.526/hour (3x more expensive)

### Scale Up/Down

```bash
# Launch more workers
python scripts/launch_distributed_workers.py --workers 10

# Launch fewer workers
python scripts/launch_distributed_workers.py --workers 2
```

Workers use modulo distribution, so they won't duplicate work.

### Different Instance Type

```bash
# Use larger instance (faster, more expensive)
python scripts/launch_distributed_workers.py --instance-type g4dn.2xlarge

# Use smaller instance (slower, cheaper)
python scripts/launch_distributed_workers.py --instance-type g4dn.xlarge
```

## Expected Timeline

**With 5 workers**:
- Hour 0: Launch instances (~5 min)
- Hour 0-1: Pull Docker images, initialize (~10 min/worker)
- Hour 1-40: Process PDFs (~2.5 min/PDF avg)
- Hour 40: Workers auto-terminate

**Total wall-clock time**: ~33-40 hours
**Total cost**: ~$26-32

## Cleanup

After processing completes:

```bash
# Verify all instances terminated
aws ec2 describe-instances \
  --filters Name=tag:Project,Values=pdf-processing

# Delete IAM role (optional)
aws iam remove-role-from-instance-profile \
  --instance-profile-name pdf-processing-user \
  --role-name pdf-processing-user

aws iam delete-instance-profile \
  --instance-profile-name pdf-processing-user

aws iam delete-role-policy \
  --role-name pdf-processing-user \
  --policy-name S3Access

aws iam delete-role \
  --role-name pdf-processing-user
```

## Success Criteria

✅ 4,921 folders in `s3://cs433-rag-project2/processed/`
✅ Each folder contains `document.md`
✅ Failure rate < 5% (<250 failures)
✅ Total cost < $50
✅ All instances terminated

## Next Steps

After processing completes:
1. Verify output quality (spot check a few markdown files)
2. Process any failed PDFs individually
3. Move to embedding generation phase
4. Build vector database for RAG

---

**Questions?** Check the main design doc: `docs/plans/2025-11-09-distributed-pdf-processing-design.md`
