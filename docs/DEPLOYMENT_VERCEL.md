# Deploy Frontend on Vercel

## Prerequisites

- Backend running at: `https://ml-poc-backend.eliebruno.com`
- GitHub repo: `eliemada/cs433_ml_project_2`
- Vercel account (free tier is fine)

---

## Step 1: Push Frontend to GitHub

```bash
cd ~/Desktop/code/project-2-rag

# Make sure frontend is committed
git add frontend/
git commit -m "✨ Add Next.js frontend for RAG chat"
git push origin feature/rag-pipeline
```

---

## Step 2: Deploy on Vercel

### Go to Vercel Dashboard

1. Visit: https://vercel.com
2. Sign in with GitHub

### Import Project

1. Click **Add New** → **Project**
2. Select your repo: `eliemada/cs433_ml_project_2`
3. Click **Import**

### Configure Project

1. **Framework Preset**: Next.js (auto-detected ✓)
2. **Root Directory**: Click **Edit** → Set to `frontend`
3. **Build Command**: `npm run build` (default)
4. **Output Directory**: `.next` (default)
5. **Install Command**: `npm install` (default)

### Add Environment Variable

Click **Environment Variables** → Add:

```
Key:   NEXT_PUBLIC_API_URL
Value: https://ml-poc-backend.eliebruno.com
```

**Important**: Make sure there's no trailing slash in the URL.

### Deploy

1. Click **Deploy**
2. Wait ~2-3 minutes for build
3. You'll get a URL like: `https://cs433-ml-project-2.vercel.app`

---

## Step 3: Update Backend CORS

Your backend needs to allow the Vercel domain.

### SSH into Unraid

```bash
ssh root@192.168.0.11
cd /mnt/user/appdata/rag-api
```

### Edit api/main.py

Find the CORS middleware section and update:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "https://cs433-ml-project-2.vercel.app",  # Your Vercel URL
        "https://*.vercel.app",  # Allow all Vercel preview deployments
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
```

### Rebuild and Restart

```bash
# Rebuild Docker image
docker build -f api/Dockerfile -t rag-api:latest .

# Restart in Portainer
# Or via command line:
docker stop rag-api
docker rm rag-api

# Then redeploy the stack in Portainer
```

---

## Step 4: Test End-to-End

1. Go to your Vercel URL: `https://cs433-ml-project-2.vercel.app`
2. Type a query: "What affects patent quality?"
3. Verify:
   - Response appears with executive summary
   - Citations are numbered
   - Can click citations to see excerpts
   - Can click "View PDF" to get presigned S3 URL

---

## Step 5: Configure Custom Domain (Optional)

### In Vercel

1. Go to your project → **Settings** → **Domains**
2. Add custom domain: `rag-chat.eliebruno.com`
3. Vercel will give you DNS records to add

### In Your DNS Provider

Add the CNAME record Vercel provides:

```
Type:  CNAME
Name:  rag-chat
Value: cname.vercel-dns.com
```

Wait ~5-10 min for DNS propagation.

### Update Backend CORS

Add your custom domain to `allow_origins`:

```python
allow_origins=[
    "https://cs433-ml-project-2.vercel.app",
    "https://rag-chat.eliebruno.com",  # Custom domain
    "https://*.vercel.app",
]
```

---

## Deployment Architecture

```
┌─────────────────────────────────────────────┐
│           User Browser                      │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│   Vercel (Frontend - Next.js)               │
│   https://cs433-ml-project-2.vercel.app     │
│                                             │
│   Environment Variables:                    │
│   NEXT_PUBLIC_API_URL=                      │
│     https://ml-poc-backend.eliebruno.com    │
└──────────────┬──────────────────────────────┘
               │ HTTPS
               ▼
┌─────────────────────────────────────────────┐
│   Nginx Proxy Manager (Unraid)             │
│   https://ml-poc-backend.eliebruno.com     │
│                                             │
│   - SSL/TLS (Let's Encrypt)                 │
│   - CORS headers for Vercel domain          │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│   RAG API (Docker Container)                │
│   http://192.168.0.11:8765                  │
│                                             │
│   - DualIndexRetriever (FAISS)              │
│   - ZeroEntropy Reranker                    │
│   - GPT-4o-mini Generation                  │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│   AWS S3                                    │
│   - FAISS indexes (1.7 GB)                  │
│   - PDF files (presigned URLs)              │
└─────────────────────────────────────────────┘
```

---

## Troubleshooting

### Build Fails on Vercel

**Check build logs**:
- Look for dependency errors
- Verify `package.json` is valid
- Make sure `frontend/` directory is set as root

### Frontend Loads but API Calls Fail

**Check CORS**:
```bash
# Test from command line
curl -I https://ml-poc-backend.eliebruno.com/health \
  -H "Origin: https://cs433-ml-project-2.vercel.app"

# Should see:
# Access-Control-Allow-Origin: https://cs433-ml-project-2.vercel.app
```

**Check environment variable**:
- In Vercel dashboard: **Settings** → **Environment Variables**
- Make sure `NEXT_PUBLIC_API_URL` is set
- Redeploy after changing env vars

### "Citation not found" or PDF Errors

**Check API is responding**:
```bash
curl https://ml-poc-backend.eliebruno.com/health
```

Should return:
```json
{
  "status": "ok",
  "index_loaded": true,
  "coarse_index_size": 46063,
  "fine_index_size": 186460,
  "total_vectors": 232523
}
```

---

## Redeployment

### When you update frontend code:

```bash
# Commit changes
git add frontend/
git commit -m "Update frontend"
git push origin feature/rag-pipeline

# Vercel auto-deploys on push
```

### When you update backend code:

```bash
# Rebuild on Unraid
ssh root@192.168.0.11
cd /mnt/user/appdata/rag-api
docker build -f api/Dockerfile -t rag-api:latest .

# Restart in Portainer
```

---

## Cost Summary

| Service | Cost |
|---------|------|
| Vercel (Frontend) | **Free** (Hobby tier) |
| Unraid (Backend) | **Free** (self-hosted) |
| Domain + SSL | **Free** (Let's Encrypt) |
| S3 Storage (1.7 GB) | ~$0.04/month |
| OpenAI + ZeroEntropy | ~$0.001/query |
| **Total (1000 queries)** | **~$1.00** |

