# Deploy RAG API Backend on Unraid

## Quick Overview

1. Copy project files to Unraid
2. Create `.env` file with API keys
3. Deploy in Portainer using docker-compose
4. Access API on port 8000

---

## Step 1: Copy Files to Unraid

### From your Mac, transfer the project:

```bash
rsync -avz --exclude 'node_modules' --exclude '.venv' --exclude '__pycache__' --exclude 'frontend' \
  ~/Desktop/code/project-2-rag/ \
  root@<UNRAID_IP>:/mnt/user/appdata/rag-api/
```

**Or manually copy these folders via SMB/SFTP:**
- `api/`
- `rag_pipeline/`
- `pyproject.toml`
- `uv.lock`

---

## Step 2: Create Environment File

SSH into Unraid and create `.env`:

```bash
ssh root@<UNRAID_IP>
cd /mnt/user/appdata/rag-api

cat > .env << 'EOF'
# Required: OpenAI API Key
OPENAI_API_KEY=sk-your-key-here

# Required: ZeroEntropy API Key
ZEROENTROPY_API_KEY=ze-your-key-here

# Required: AWS S3 Credentials
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET=cs433-rag-project2

# Optional: Tuning
COARSE_CANDIDATES=50
FINE_CANDIDATES=50
EOF
```

---

## Step 3: Deploy in Portainer

### Open Portainer
Go to: `http://<UNRAID_IP>:9000`

### Create Stack
1. Click **Stacks** → **+ Add Stack**
2. Name: `rag-api`
3. Build method: **Web editor**
4. Paste this docker-compose:

```yaml
version: '3.8'

services:
  rag-api:
    build:
      context: /mnt/user/appdata/rag-api
      dockerfile: api/Dockerfile
    container_name: rag-api
    ports:
      - "8765:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ZEROENTROPY_API_KEY=${ZEROENTROPY_API_KEY}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
      - S3_BUCKET=${S3_BUCKET:-cs433-rag-project2}
      - COARSE_CANDIDATES=${COARSE_CANDIDATES:-50}
      - FINE_CANDIDATES=${FINE_CANDIDATES:-50}
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "python -c 'import urllib.request; urllib.request.urlopen(\"http://localhost:8000/health\")' || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 90s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

5. **Scroll down to Environment variables section**
6. Click **Advanced mode**
7. Paste your credentials (get values from your `.env` file):

```
OPENAI_API_KEY=sk-proj-...
ZEROENTROPY_API_KEY=ze_...
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET=cs433-rag-project2
COARSE_CANDIDATES=50
FINE_CANDIDATES=50
```

8. Click **Deploy the stack**

---

## Step 4: Wait for Startup

The container will:
1. Build the image (~2-3 min)
2. Download indexes from S3 (~1-2 min for 1.7GB)
3. Load into memory (~30 sec)

**Watch logs:**
```bash
docker logs rag-api -f
```

Expected output:
```
============================================================
Loading RAG retriever (dual-index mode)...
============================================================
Loading coarse index...
Downloading index from s3://cs433-rag-project2/indexes/coarse.faiss...
Downloading metadata from s3://cs433-rag-project2/indexes/coarse_metadata.json...
Loaded coarse index with 46063 vectors
Loading fine index...
Downloading index from s3://cs433-rag-project2/indexes/fine.faiss...
Downloading metadata from s3://cs433-rag-project2/indexes/fine_metadata.json...
Loaded fine index with 186460 vectors
Retriever loaded in 87.3s
Coarse index: 46063 vectors
Fine index: 186460 vectors
Total: 232523 vectors
ZeroEntropy reranking: enabled
============================================================
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## Step 5: Test the API

```bash
# Health check
curl http://<UNRAID_IP>:8765/health

# Search test
curl -X POST http://<UNRAID_IP>:8765/search \
  -H "Content-Type: application/json" \
  -d '{"query": "patent quality", "top_k": 3}'

# Chat test
curl -X POST http://<UNRAID_IP>:8765/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What affects patent quality?", "top_k": 10}'
```

---

## Step 6: Access from Outside

### Option A: Direct Port Forward
1. In your router, forward port `8765` → Unraid IP
2. Access: `http://<YOUR_PUBLIC_IP>:8765`

### Option B: Nginx Proxy Manager (Recommended)
1. Install Nginx Proxy Manager on Unraid
2. Create proxy host:
   - Domain: `rag-api.yourdomain.com`
   - Forward to: `<UNRAID_IP>:8765`
   - Enable SSL (Let's Encrypt)
3. Access: `https://rag-api.yourdomain.com`

### Option C: Cloudflare Tunnel (No Port Forward)
1. Install Cloudflare Tunnel on Unraid
2. Point tunnel to `localhost:8765`
3. Get URL: `https://rag-api-xyz.trycloudflare.com`

---

## Troubleshooting

### Container won't start
```bash
# Check logs
docker logs rag-api

# Common issues:
# - Missing .env file → create it
# - Wrong path in docker-compose → verify /mnt/user/appdata/rag-api exists
```

### Out of memory
- Indexes need ~2GB RAM
- Increase Docker memory limit in Unraid settings
- Check: **Settings** → **Docker** → **Default container size**

### Cannot connect to S3
```bash
# Test AWS credentials
docker exec rag-api aws s3 ls s3://cs433-rag-project2/indexes/

# If fails:
# - Check AWS credentials in .env
# - Check network connectivity
```

### API responds but slow
- First query is slow (~3-5s) - normal
- Subsequent queries faster (~3s)
- If consistently slow, check ZeroEntropy API quota

---

## Update/Rebuild

When you change code:

```bash
# Copy new files
rsync -avz api/ root@<UNRAID_IP>:/mnt/user/appdata/rag-api/api/

# In Portainer: Stacks → rag-api → Stop → Start
# Or force rebuild:
docker-compose -f /path/to/docker-compose.yml up --build -d
```

---

## Resource Usage

| Resource | Usage |
|----------|-------|
| RAM | ~2.5 GB (indexes + overhead) |
| CPU | Low (spikes during query) |
| Disk | ~50 MB (image) |
| Network | ~1.7 GB download on first start |

---

## API Endpoints

Once running, visit: `http://<UNRAID_IP>:8765/docs` for interactive API docs (Swagger UI)

Main endpoints:
- `GET /health` - Check status
- `POST /search` - FAISS search only
- `POST /chat` - Full RAG with LLM
- `GET /pdf/{paper_id}` - Get PDF presigned URL

