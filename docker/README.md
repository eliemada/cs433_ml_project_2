# Docker Setup for Distributed PDF Processing

## Overview

The Docker image supports two modes:

1. **Distributed Worker Mode** (default) - For parallel processing on AWS EC2
2. **Legacy Batch Mode** - For local processing

## Building the Image

### Build locally

```bash
# From project root
docker build -t ravinala/pdf-parser:v2-distributed .

# Or with specific tag
docker build -t ravinala/pdf-parser:latest .
```

**Build time**: ~10-15 minutes (includes downloading 2GB Dolphin model)

### Build arguments

None currently required - all configuration via environment variables.

## Running the Image

### Distributed Worker Mode

Set `S3_INPUT_BUCKET` and `S3_OUTPUT_BUCKET` to enable distributed mode:

```bash
docker run --gpus all --rm \
  -e WORKER_ID=0 \
  -e TOTAL_WORKERS=5 \
  -e S3_INPUT_BUCKET=cs433-rag-project2 \
  -e S3_INPUT_PREFIX=raw_pdfs/ \
  -e S3_OUTPUT_BUCKET=cs433-rag-project2 \
  -e S3_OUTPUT_PREFIX=processed/ \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  -e AWS_DEFAULT_REGION=us-east-1 \
  ravinala/pdf-parser:v2-distributed
```

### Legacy Batch Mode

If S3 environment variables are not set, runs in legacy mode:

```bash
docker run --gpus all --rm \
  -v $(pwd)/data:/app/data \
  ravinala/pdf-parser:v2-distributed
```

## Testing the Image

### Test 1: Verify Image Builds

```bash
# Build
docker build -t test-pdf-parser .

# Check image size
docker images test-pdf-parser

# Expected size: ~8-10GB (includes CUDA, Python, Dolphin model)
```

### Test 2: Test Entrypoint Script

```bash
# Test distributed mode detection
docker run --rm \
  -e S3_INPUT_BUCKET=test \
  -e S3_OUTPUT_BUCKET=test \
  test-pdf-parser echo "Should show: Starting DISTRIBUTED WORKER MODE"

# Test legacy mode
docker run --rm \
  test-pdf-parser --help
```

### Test 3: Test with Mock AWS (Optional)

```bash
# Install localstack for local S3 testing
pip install localstack awscli-local

# Start localstack
docker run -d -p 4566:4566 localstack/localstack

# Create test bucket
awslocal s3 mb s3://test-bucket
awslocal s3 cp sample.pdf s3://test-bucket/raw_pdfs/

# Run worker against localstack
docker run --gpus all --rm \
  --network host \
  -e WORKER_ID=0 \
  -e TOTAL_WORKERS=1 \
  -e S3_INPUT_BUCKET=test-bucket \
  -e S3_OUTPUT_BUCKET=test-bucket \
  -e AWS_ENDPOINT_URL=http://localhost:4566 \
  test-pdf-parser
```

## Pushing to Docker Hub

### Login

```bash
docker login
# Enter username: ravinala
# Enter password: <your-token>
```

### Tag and Push

```bash
# Tag with version
docker tag ravinala/pdf-parser:v2-distributed ravinala/pdf-parser:v2-distributed
docker tag ravinala/pdf-parser:v2-distributed ravinala/pdf-parser:latest

# Push both tags
docker push ravinala/pdf-parser:v2-distributed
docker push ravinala/pdf-parser:latest
```

**Push time**: ~5-10 minutes (depends on connection speed)

## Environment Variables

### Required for Distributed Mode

| Variable | Description | Example |
|----------|-------------|---------|
| `S3_INPUT_BUCKET` | Input S3 bucket | `cs433-rag-project2` |
| `S3_OUTPUT_BUCKET` | Output S3 bucket | `cs433-rag-project2` |
| `AWS_ACCESS_KEY_ID` | AWS access key | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | `secret...` |

### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `WORKER_ID` | `0` | Worker ID (0-indexed) |
| `TOTAL_WORKERS` | `1` | Total number of workers |
| `S3_INPUT_PREFIX` | `raw_pdfs/` | Input folder prefix |
| `S3_OUTPUT_PREFIX` | `processed/` | Output folder prefix |
| `AWS_DEFAULT_REGION` | - | AWS region (e.g., `us-east-1`) |
| `MAX_RETRIES` | `2` | Retry failed PDFs N times |

## Troubleshooting

### GPU Not Detected

```bash
# Check NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# If fails, install nvidia-docker2
# Ubuntu:
sudo apt-get install nvidia-docker2
sudo systemctl restart docker
```

### Image Too Large

Current size (~8-10GB) is expected due to:
- CUDA runtime: ~2GB
- Dolphin model: ~2GB
- Python dependencies: ~2-3GB
- System libraries: ~1-2GB

To reduce size (not recommended as it breaks functionality):
- Remove CUDA → CPU-only (very slow)
- Remove model → Download at runtime (slower startup)
- Use multi-stage build (minimal savings)

### Build Fails

Common issues:

**Git LFS fails**:
```bash
# Ensure git-lfs is installed
git lfs install

# Clear Docker cache
docker builder prune -af
```

**UV sync fails**:
```bash
# Check pyproject.toml and uv.lock are present
ls -l pyproject.toml uv.lock

# Rebuild with --no-cache
docker build --no-cache -t ravinala/pdf-parser:v2-distributed .
```

## Multi-Architecture Builds (Optional)

For ARM64 support (Apple Silicon, AWS Graviton):

```bash
# Setup buildx
docker buildx create --name multiarch --use

# Build for multiple architectures
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ravinala/pdf-parser:v2-distributed \
  --push .
```

**Note**: ARM64 build takes 30-60 minutes.

## Deployment Commands

### Quick Deploy (5 workers)

```bash
# See: scripts/launch_distributed_workers.py (Phase 3)
# Or manually via AWS Console:
# - Launch 5x g4dn.xlarge Spot instances
# - Use Deep Learning AMI
# - Set User Data with docker run command
```

### EC2 User Data Script

```bash
#!/bin/bash
docker pull ravinala/pdf-parser:v2-distributed

docker run --gpus all --rm \
  -e WORKER_ID=${WORKER_ID} \
  -e TOTAL_WORKERS=5 \
  -e S3_INPUT_BUCKET=cs433-rag-project2 \
  -e S3_INPUT_PREFIX=raw_pdfs/ \
  -e S3_OUTPUT_BUCKET=cs433-rag-project2 \
  -e S3_OUTPUT_PREFIX=processed/ \
  -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
  -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
  -e AWS_DEFAULT_REGION=us-east-1 \
  ravinala/pdf-parser:v2-distributed

# Auto-terminate when done
shutdown -h now
```

## Version History

- **v2-distributed** - Distributed worker support with S3 integration
- **v1** - Original batch processing version

## Next Steps

After building and pushing the image:
1. Test with 1 PDF locally
2. Deploy single EC2 instance for testing
3. Deploy 5 workers for full batch

See: `docs/plans/2025-11-09-distributed-pdf-processing-design.md`
