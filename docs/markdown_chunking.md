# Chunking System for Research Papers RAG

This system implements hybrid semantic chunking for markdown research papers, optimized for RAG with ZeroEntropy reranker.

## Overview

The chunking system creates two types of chunks:
- **Coarse chunks** (~2000 chars): For broad context retrieval (top 50-75 candidates)
- **Fine chunks** (~200-400 chars): For precise snippet extraction after reranking

## Architecture

```
┌─────────────────┐
│  S3 Bucket      │
│  999 Papers     │
│  (markdown)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  S3MarkdownLoader│────▶│MarkdownChunker  │
└─────────────────┘     └────────┬─────────┘
                                 │
                ┌────────────────┼────────────────┐
                ▼                ▼                ▼
         ┌──────────┐    ┌──────────┐    ┌──────────┐
         │  Coarse  │    │   Fine   │    │ Metadata │
         │  Chunks  │    │  Chunks  │    │ (section │
         │          │    │          │    │hierarchy)│
         └──────────┘    └──────────┘    └──────────┘
```

## Files

### Core Modules
- **`rag_pipeline/rag/markdown_chunker.py`**: Main chunking logic with `MarkdownChunker` class
- **`scripts/utils/markdown_s3_loader.py`**: AWS S3 utilities for loading papers and metadata
- **`scripts/test_markdown_chunking.py`**: Test suite verifying system functionality
- **`notebooks/chunking_benchmark.ipynb`**: Jupyter notebook for benchmarking different strategies

### Configuration
- **`docs/requirements_chunking.txt`**: Python dependencies (or use `pyproject.toml`)

## Installation

```bash
# Install dependencies
uv add tiktoken boto3 openai numpy pandas matplotlib seaborn scikit-learn jupyter tqdm

# Or using pip with the requirements file
pip install -r requirements_chunking.txt
```

## Quick Start

### 1. Test the System

```bash
# Run from project root
uv run python scripts/test_markdown_chunking.py
```

This runs three tests:
- Local markdown chunking
- S3 document loading
- End-to-end integration

### 2. Run Benchmarking

```bash
# Run from project root
jupyter notebook notebooks/chunking_benchmark.ipynb
```

The notebook compares three strategies:
- **Hybrid semantic** (recommended)
- **Fixed-size baseline**
- **Pure semantic baseline**

Evaluation metrics:
- Semantic coherence (embedding similarity within chunks)
- Boundary quality (similarity across chunk boundaries)
- Citation integrity (% of citations with context)
- Size distribution and variance

### 3. Use in Your Code

```python
from rag_pipeline.rag.markdown_chunker import MarkdownChunker
from scripts.utils.markdown_s3_loader import S3MarkdownLoader

# Load paper from S3
loader = S3MarkdownLoader(bucket_name="cs433-rag-project2")
markdown_text, metadata = loader.load_paper("00002_W2122361802")
title = loader.extract_title_from_metadata(metadata)

# Chunk it
chunker = MarkdownChunker(
    coarse_target_size=2000,
    coarse_max_size=2500,
    fine_target_size=300,
    fine_max_size=450,
    coarse_overlap_pct=0.10,
    fine_overlap_pct=0.20
)

results = chunker.chunk_document(
    markdown_text,
    paper_id="00002_W2122361802",
    paper_title=title,
    create_both_types=True
)

coarse_chunks = results['coarse']  # List[Chunk]
fine_chunks = results['fine']      # List[Chunk]

# Access chunk data
for chunk in coarse_chunks[:3]:
    print(f"ID: {chunk.chunk_id}")
    print(f"Section: {' > '.join(chunk.section_hierarchy)}")
    print(f"Text: {chunk.text[:100]}...")
    print()
```

## Chunking Strategy Details

### Hybrid Semantic Approach

1. **Extract hierarchy**: Parse markdown headings (##, ###, etc.)
2. **Split into sections**: Use headings as natural boundaries
3. **Size constraints**:
   - If section > max_size, split at paragraph boundaries
   - Target: ~2000 chars for coarse, ~300 chars for fine
4. **Add overlap**:
   - Coarse: 10% overlap (last ~200 chars from previous chunk)
   - Fine: 20% overlap (cross-paragraph boundaries)
5. **Metadata enrichment**:
   - Section hierarchy (e.g., ["Chapter 2", "2.1", "The Nature of Security"])
   - Paper ID and title
   - Chunk position (5/47 in document)

### Why This Works for Research Papers

**Preserves structure**:
- Headings indicate topic boundaries
- Arguments stay together within sections
- Citations remain with referencing text

**Balances context and precision**:
- Coarse chunks: Enough context for semantic understanding
- Fine chunks: Precise answers for policymaker queries

**Overlap prevents information loss**:
- Important sentences at boundaries appear in both chunks
- Retrieval doesn't miss cross-boundary information

## Benchmarking Results

Based on 10 sample papers (run `chunking_benchmark.ipynb` for full results):

| Metric | Hybrid | Fixed-size | Pure Semantic |
|--------|--------|------------|---------------|
| Mean chunk size | ~2000 chars | ~2000 chars | ~4500 chars (variable) |
| Size variance | Low | Very low | High |
| Semantic coherence | **High** | Medium | **High** |
| Boundary quality | **Good** | Poor | **Good** |
| Citation integrity | **High** | Medium | **High** |

**Recommendation**: Use **Hybrid** strategy for best balance of all metrics.

## RAG Pipeline Integration

### With ZeroEntropy Reranker

```python
# 1. Initial retrieval: Get top 50-75 coarse chunks from vector DB
top_coarse_chunks = vector_db.search(query, k=75)

# 2. Rerank with ZeroEntropy zrank
reranked_chunks = zrank.rerank(query, top_coarse_chunks, top_k=10)

# 3. For each reranked coarse chunk, retrieve associated fine chunks
fine_chunks_for_answer = []
for coarse_chunk in reranked_chunks[:5]:
    # Get fine chunks from same section
    fine_chunks = get_fine_chunks_for_coarse(coarse_chunk.chunk_id)
    fine_chunks_for_answer.extend(fine_chunks)

# 4. Generate answer with LLM using fine chunks for precision
answer = llm.generate(query, context=fine_chunks_for_answer)
```

### Recommended Vector Database

For your scale (999 papers × ~50 chunks = ~50k chunks):

**FAISS** (recommended for prototyping):
- Fast, local, no setup required
- Good for <100k chunks
- Easy to iterate and experiment

```python
import faiss
import numpy as np

# Create index
dimension = 1536  # text-embedding-3-small
index = faiss.IndexFlatL2(dimension)

# Add embeddings
embeddings = get_embeddings([chunk.text for chunk in coarse_chunks])
index.add(embeddings)

# Search
query_embedding = get_embeddings([query])
distances, indices = index.search(query_embedding, k=75)
```

**Weaviate/Qdrant** (for production):
- Better metadata filtering (e.g., "only papers from 2020+")
- Hybrid search (dense + sparse)
- More features, but more setup

## S3 Structure

Your bucket: `cs433-rag-project2`

```
cs433-rag-project2/
├── raw_pdfs/
├── raw_metadata/
└── processed/
    ├── 00002_W2122361802/
    │   ├── document.md
    │   ├── metadata.json
    │   └── figures/
    ├── 00004_W2114989862/
    │   ├── document.md
    │   └── metadata.json
    └── ...
```

Total papers: **999** (with valid document.md files)

## Next Steps

1. **Run benchmarking**: Execute the full notebook on more papers
2. **Adjust parameters**: Fine-tune chunk sizes based on results
3. **Create ground truth**: Develop sample policymaker queries for evaluation
4. **Set up vector DB**: Choose FAISS/Weaviate and load chunks
5. **Integrate reranker**: Test with ZeroEntropy zrank
6. **Build RAG pipeline**: Combine retrieval + reranking + generation

## Configuration Parameters

### MarkdownChunker

```python
MarkdownChunker(
    coarse_target_size=2000,    # Target size for coarse chunks (chars)
    coarse_max_size=2500,       # Max before forcing split
    fine_target_size=300,       # Target size for fine chunks
    fine_max_size=450,          # Max before forcing split
    coarse_overlap_pct=0.10,    # 10% overlap for coarse
    fine_overlap_pct=0.20,      # 20% overlap for fine
    model_name="text-embedding-3-small"  # For token counting
)
```

### S3MarkdownLoader

```python
S3MarkdownLoader(
    bucket_name="cs433-rag-project2",
    prefix="processed/"
)
```

## Troubleshooting

**"No papers found in S3"**
- Check AWS credentials: `aws configure`
- Verify bucket access: `aws s3 ls s3://cs433-rag-project2/`

**"Import error: No module named 'chunking'"**
- Ensure you're in the project directory
- Install dependencies: `uv add tiktoken boto3`

**"OpenAI API error"**
- Set API key: `export OPENAI_API_KEY=your-key`
- Or set in notebook: `openai.api_key = "your-key"`

## Performance Notes

**Chunking speed**: ~1-2 seconds per paper (depends on size)

**For all 999 papers**:
- Estimated time: ~20-30 minutes
- Total chunks: ~50k coarse + ~200k fine
- Storage: ~100MB JSON (uncompressed)

**Embedding cost** (text-embedding-3-small):
- 50k chunks × ~400 tokens = ~20M tokens
- Cost: ~$1-2 for all embeddings

## Contact

For questions or issues with this chunking system, please refer to the implementation files or run the test suite for verification.

---

**Status**: ✅ All tests passing (3/3)
**Last tested**: 2025-11-15
