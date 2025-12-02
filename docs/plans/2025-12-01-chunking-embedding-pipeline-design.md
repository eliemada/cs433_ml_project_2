# Chunking & Embedding Pipeline Design

## Overview

Pipeline to chunk all processed PDFs using hybrid strategy, embed with OpenAI, index with FAISS, and enable retrieval with ZeroEntropy reranking.

## Architecture

```
S3 processed/          Hybrid Chunker         OpenAI API           FAISS
─────────────────► ──────────────────► ─────────────────► ─────────────────►
999 markdown files    ~50k coarse chunks     Embeddings (1536d)   Index files
                      ~200k fine chunks
```

## Components

### 1. Chunking Script (`scripts/chunk_all_documents.py`)

**Input:** `s3://cs433-rag-project2/processed/{paper_id}/document.md`

**Output:**
- `s3://cs433-rag-project2/chunks/{paper_id}_coarse.json`
- `s3://cs433-rag-project2/chunks/{paper_id}_fine.json`

**Behavior:**
- Lists all paper folders in `processed/`
- Skips papers already chunked (idempotent)
- Uses `MarkdownChunker` for hybrid chunking:
  - Coarse chunks: ~2000 chars (for broad retrieval)
  - Fine chunks: ~300 chars (for precise extraction)
- Progress bar + failure logging

**Chunk JSON format:**
```json
{
  "paper_id": "00002_W2122361802",
  "paper_title": "Paper Title Here",
  "chunk_type": "coarse",
  "chunks": [
    {
      "chunk_id": "00002_W2122361802_coarse_0",
      "text": "...",
      "section_hierarchy": ["Introduction"],
      "char_start": 0,
      "char_end": 1950,
      "chunk_index": 0,
      "total_chunks": 25
    }
  ]
}
```

### 2. Embedding & Indexing Script (`scripts/embed_and_index.py`)

**Input:** `s3://cs433-rag-project2/chunks/*.json`

**Output:**
- `s3://cs433-rag-project2/indexes/coarse.faiss`
- `s3://cs433-rag-project2/indexes/coarse_metadata.json`
- `s3://cs433-rag-project2/indexes/fine.faiss`
- `s3://cs433-rag-project2/indexes/fine_metadata.json`

**Behavior:**
- Downloads all chunk files from S3
- Embeds using OpenAI `text-embedding-3-small` (1536 dimensions)
- Batches 100 texts per API call with rate limiting
- Builds FAISS `IndexFlatIP` (cosine similarity via normalized vectors)
- Metadata JSON maps index position → chunk details
- Progress bar + cost estimation

**Metadata format:**
```json
{
  "0": {
    "chunk_id": "00002_W2122361802_coarse_0",
    "paper_id": "00002_W2122361802",
    "paper_title": "...",
    "text": "...",
    "section_hierarchy": ["Introduction"]
  }
}
```

### 3. Retriever Module (`rag_pipeline/rag/retriever.py`)

**Query-time flow:**

```
User Query
    │
    ▼
┌─────────────────────────────────┐
│ 1. FAISS Retrieval              │  Embed query → top 75 coarse chunks
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 2. ZeroEntropy Reranking        │  Rerank by relevance → top 10
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 3. Fine Chunk Retrieval (opt)   │  Get precise snippets from sections
└─────────────────────────────────┘
    │
    ▼
    Results with metadata
```

**Key classes:**
- `FAISSRetriever`: Loads index, performs similarity search
- `ZeroEntropyReranker`: Calls rerank API
- `HybridRetriever`: Combines FAISS + reranking

## Configuration

**Environment variables:**
- `OPENAI_API_KEY`: For embeddings
- `ZEROENTROPY_API_KEY`: For reranking
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`: For S3

**S3 Bucket:** `cs433-rag-project2`

## Cost Estimates

| Component | Estimate |
|-----------|----------|
| Chunking | Free (CPU) |
| Embedding (~250k chunks) | $2-4 |
| FAISS indexing | Free (CPU) |
| ZeroEntropy | Per-query at runtime |

## Execution Order

1. Run `chunk_all_documents.py` (~20-30 min for 999 papers)
2. Run `embed_and_index.py` (~30-60 min depending on rate limits)
3. Use `retriever.py` for queries

## Dependencies

Already in `pyproject.toml`:
- `openai`, `tiktoken` - embeddings
- `boto3` - S3 access
- `faiss-cpu` - vector indexing (add if missing)

To add:
- `faiss-cpu` if not present
