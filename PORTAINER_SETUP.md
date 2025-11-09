# Running PDF Parser on Portainer

## Prerequisites

- Docker with NVIDIA GPU support (`nvidia-docker2`)
- Portainer installed
- NVIDIA GPU with CUDA support

## Setup Steps

### 1. Create Environment File

Copy `.env.example` to `.env` and fill in your AWS credentials:

```bash
cp .env.example .env
# Edit .env with your actual credentials
```

### 2. Deploy via Portainer

#### Option A: Using Portainer Stacks (Recommended)

1. **Login to Portainer** (usually http://your-server:9000)

2. **Go to Stacks** → **Add Stack**

3. **Name**: `pdf-parser`

4. **Build method**: Choose "Upload"
   - Upload `docker-compose.yml` file

5. **Environment variables**:
   - Click "Load variables from .env file"
   - Upload your `.env` file

   OR manually add:
   ```
   AWS_ACCESS_KEY_ID=your_key
   AWS_SECRET_ACCESS_KEY=your_secret
   AWS_DEFAULT_REGION=us-east-1
   S3_BUCKET=cs433-rag-project2
   ```

6. **Click "Deploy the stack"**

#### Option B: Using Portainer Containers

1. **Go to Containers** → **Add Container**

2. **Configuration**:
   - Name: `pdf-parser`
   - Image: `ravinala/pdf-parser:latest`

3. **Advanced container settings**:

   **Runtime & Resources**:
   - Runtime: `nvidia`

   **Env variables**:
   - Add each variable manually from your `.env`

   **Volumes** (optional):
   ```
   /path/on/host/logs → /tmp
   ```

4. **Click "Deploy the container"**

### 3. Monitor Progress

**View Logs**:
- Go to **Containers** → Click on `pdf-parser`
- Click **Logs** tab
- You'll see colorful loguru output showing progress

**Expected output**:
```
2025-11-09 14:00:00 | INFO     | Using S3 bucket: cs433-rag-project2
2025-11-09 14:00:05 | INFO     | Finding unprocessed PDFs...
2025-11-09 14:00:10 | INFO     | Total PDFs: 1000
2025-11-09 14:00:10 | SUCCESS  | Pipeline initialized successfully
2025-11-09 14:00:15 | INFO     | Downloaded: 00001_W12345...
2025-11-09 14:00:45 | SUCCESS  | Parsed: 00001_W12345... (1/1000)
2025-11-09 14:00:50 | SUCCESS  | Uploaded: 00001_W12345...
```

### 4. Check Results in S3

```bash
# List processed documents
aws s3 ls s3://cs433-rag-project2/processed/

# Download a processed document
aws s3 cp s3://cs433-rag-project2/processed/00001_W12345/document.md .
```

## Troubleshooting

### GPU Not Detected

If you see "Model loaded successfully on cpu" instead of "cuda":

1. **Check NVIDIA Docker runtime**:
   ```bash
   docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
   ```

2. **Edit Docker daemon** (`/etc/docker/daemon.json`):
   ```json
   {
     "runtimes": {
       "nvidia": {
         "path": "nvidia-container-runtime",
         "runtimeArgs": []
       }
     },
     "default-runtime": "nvidia"
   }
   ```

3. **Restart Docker**:
   ```bash
   sudo systemctl restart docker
   ```

### Model Loading Error

If you see "header too large" error:

**Option 1: Rebuild with fixed model download**
```bash
# SSH into server
docker pull ravinala/pdf-parser:latest
```

**Option 2: Mount local model**
1. Download model to server:
   ```bash
   mkdir -p /opt/models/dolphin
   cd /opt/models
   git clone https://huggingface.co/ByteDance/Dolphin-1.5 dolphin
   ```

2. Update `docker-compose.yml`:
   ```yaml
   volumes:
     - /opt/models/dolphin:/app/models/dolphin
   ```

### Out of Memory

If processing crashes with OOM:

1. **Process fewer PDFs at once** - modify the script to limit queue sizes
2. **Use smaller images** - reduce `target_image_size` in config
3. **Add more RAM/swap**

## Manual Run (for debugging)

Launch container with shell instead of auto-running:

```bash
docker run -it --rm --gpus all \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  -e AWS_DEFAULT_REGION=us-east-1 \
  -e S3_BUCKET=cs433-rag-project2 \
  ravinala/pdf-parser:latest \
  /bin/bash

# Inside container:
cd /app
uv run python scripts/process_pdfs_batch.py
```

## Stopping the Job

The container will automatically exit when all PDFs are processed.

To stop manually:
- In Portainer: **Containers** → `pdf-parser` → **Stop**
- Or: `docker stop pdf-parser`

## Re-running

The pipeline automatically resumes - it only processes PDFs that don't have a `processed/{doc_id}/` folder in S3.

Just restart the container:
- In Portainer: **Containers** → `pdf-parser` → **Start**
- Or: `docker-compose up` / `docker start pdf-parser`
