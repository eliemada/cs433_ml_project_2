# Manual Deployment Guide

Simple instructions for deploying workers manually on AWS EC2.

## What You Need

- **3-5 AWS EC2 instances**
- **Instance type**: g4dn.xlarge (or any GPU instance)
- **AMI**: Deep Learning Base AMI with CUDA (Ubuntu 22.04)
  - In eu-north-1: `ami-071addcbd200d2f65`
- **Storage**: 125 GB
- **Security group**: Allow SSH (optional for debugging)

## Step 1: Launch EC2 Instances

In AWS Console:

1. Go to EC2 → Launch Instance
2. Choose AMI: "Deep Learning Base AMI with Single CUDA (Ubuntu 22.04)"
3. Choose instance type: `g4dn.xlarge`
4. Configure storage: 125 GB
5. **Launch 3 instances** (or 5 if you want faster processing)

## Step 2: SSH Into Each Instance

```bash
ssh -i your-key.pem ubuntu@<instance-ip>
```

## Step 3: Run Worker on Each Instance

On **Instance 1** (Worker 0):
```bash
docker pull ravinala/pdf-parser:v2-distributed

docker run --gpus all --rm \
  -e WORKER_ID=0 \
  -e TOTAL_WORKERS=3 \
  -e S3_INPUT_BUCKET=cs433-rag-project2 \
  -e S3_INPUT_PREFIX=raw_pdfs/ \
  -e S3_OUTPUT_BUCKET=cs433-rag-project2 \
  -e S3_OUTPUT_PREFIX=processed/ \
  -e AWS_ACCESS_KEY_ID=<your-access-key> \
  -e AWS_SECRET_ACCESS_KEY=<your-secret-key> \
  -e AWS_DEFAULT_REGION=eu-north-1 \
  ravinala/pdf-parser:v2-distributed
```

On **Instance 2** (Worker 1):
```bash
docker pull ravinala/pdf-parser:v2-distributed

docker run --gpus all --rm \
  -e WORKER_ID=1 \
  -e TOTAL_WORKERS=3 \
  -e S3_INPUT_BUCKET=cs433-rag-project2 \
  -e S3_INPUT_PREFIX=raw_pdfs/ \
  -e S3_OUTPUT_BUCKET=cs433-rag-project2 \
  -e S3_OUTPUT_PREFIX=processed/ \
  -e AWS_ACCESS_KEY_ID=<your-access-key> \
  -e AWS_SECRET_ACCESS_KEY=<your-secret-key> \
  -e AWS_DEFAULT_REGION=eu-north-1 \
  ravinala/pdf-parser:v2-distributed
```

On **Instance 3** (Worker 2):
```bash
docker pull ravinala/pdf-parser:v2-distributed

docker run --gpus all --rm \
  -e WORKER_ID=2 \
  -e TOTAL_WORKERS=3 \
  -e S3_INPUT_BUCKET=cs433-rag-project2 \
  -e S3_INPUT_PREFIX=raw_pdfs/ \
  -e S3_OUTPUT_BUCKET=cs433-rag-project2 \
  -e S3_OUTPUT_PREFIX=processed/ \
  -e AWS_ACCESS_KEY_ID=<your-access-key> \
  -e AWS_SECRET_ACCESS_KEY=<your-secret-key> \
  -e AWS_DEFAULT_REGION=eu-north-1 \
  ravinala/pdf-parser:v2-distributed
```

**If using 5 workers**, change `TOTAL_WORKERS=5` and use `WORKER_ID=0,1,2,3,4`

## Important Notes

### Worker Distribution
- Worker 0 processes PDFs at indices: 0, 3, 6, 9, ...
- Worker 1 processes PDFs at indices: 1, 4, 7, 10, ...
- Worker 2 processes PDFs at indices: 2, 5, 8, 11, ...

This ensures no duplicate work!

### Replace Your Credentials
Replace `<your-access-key>` and `<your-secret-key>` with your actual AWS credentials from your `.env` file:
```bash
# From your .env file:
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```

### Running in Background
To keep it running after you disconnect:
```bash
nohup docker run --gpus all --rm \
  -e WORKER_ID=0 \
  -e TOTAL_WORKERS=3 \
  ... \
  ravinala/pdf-parser:v2-distributed > worker.log 2>&1 &
```

### Check Progress
```bash
# View logs
tail -f worker.log

# Count processed PDFs in S3
aws s3 ls s3://cs433-rag-project2/processed/ | grep "PRE" | wc -l
```

## Cost Estimate

**3 workers × g4dn.xlarge × 40 hours = ~$63**
**5 workers × g4dn.xlarge × 40 hours = ~$105**

## When Done

Workers will finish and exit automatically. Then:
1. Terminate all EC2 instances
2. Verify output in S3: `s3://cs433-rag-project2/processed/`

That's it! ✅
