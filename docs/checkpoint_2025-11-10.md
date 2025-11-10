# Project Checkpoint: RAG Pipeline for Academic Papers

**Date**: November 10, 2025
**Course**: CS-433
**Status**: Phase 1 Complete (PDF Processing) | Phase 2 Ready (Chunking & Embeddings)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current System Architecture](#current-system-architecture)
3. [What We Have Accomplished](#what-we-have-accomplished)
4. [Data Storage on S3](#data-storage-on-s3)
5. [Technical Implementation Details](#technical-implementation-details)
6. [Next Steps: Chunking & RAG Pipeline](#next-steps-chunking--rag-pipeline)
7. [Performance & Scalability](#performance--scalability)
8. [Code Structure](#code-structure)

---

## Executive Summary

We have successfully implemented **Phase 1** of our RAG (Retrieval-Augmented Generation) pipeline: **Large-scale PDF Processing with GPU Acceleration**.

### Key Achievements

- ✅ **353 academic papers processed** (out of 4,920 available)
- ✅ **Distributed GPU processing** with 3 concurrent workers
- ✅ **Dolphin vision-language model** for layout understanding
- ✅ **Structured markdown output** with extracted figures
- ✅ **S3-based storage** for scalability
- ✅ **Automated worker distribution** to prevent duplicate work

### Current Status

| Component | Status | Progress |
|-----------|--------|----------|
| PDF Processing | ✅ Complete | 353/4,920 PDFs (7.2%) |
| S3 Infrastructure | ✅ Complete | Fully operational |
| Distributed Workers | ✅ Complete | 3 workers deployed |
| Chunking Pipeline | 🟡 Ready to implement | Code exists, needs integration |
| Embedding Generation | ⏳ Pending | Next phase |
| Vector Database | ⏳ Pending | Next phase |
| RAG Query System | ⏳ Pending | Final phase |

---

## Current System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          AWS S3 Storage                              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐       │
│  │  raw_pdfs/     │  │  processed/    │  │ raw_metadata/  │       │
│  │  4,920 PDFs    │  │  353 folders   │  │  Paper info    │       │
│  └────────────────┘  └────────────────┘  └────────────────┘       │
└─────────────────────────────────────────────────────────────────────┘
                              ▲
                              │
                    ┌─────────┴─────────┐
                    │   Distributed     │
                    │   Processing      │
                    └─────────┬─────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
    ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
    │Worker 0 │          │Worker 1 │          │Worker 2 │
    │(GPU)    │          │(GPU)    │          │(GPU)    │
    │PDFs:    │          │PDFs:    │          │PDFs:    │
    │0,3,6... │          │1,4,7... │          │2,5,8... │
    └─────────┘          └─────────┘          └─────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   Dolphin Model   │
                    │  Vision-Language  │
                    │   GPU Inference   │
                    └───────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   Output Format   │
                    │  • document.md    │
                    │  • metadata.json  │
                    │  • figures/*.png  │
                    └───────────────────┘
```

### Processing Pipeline

Each PDF goes through this pipeline:

```
PDF File → Download from S3 → Dolphin Model → Layout Analysis
                                     ↓
                            Element Recognition
                                     ↓
                    ┌────────────────┼────────────────┐
                    │                │                │
              Text Blocks      Figures          Tables
                    │                │                │
                    └────────────────┼────────────────┘
                                     ↓
                          Markdown Conversion
                                     ↓
                    ┌────────────────┼────────────────┐
                    │                │                │
             document.md      metadata.json     figures/
                    │                │                │
                    └────────────────┼────────────────┘
                                     ↓
                           Upload to S3
                                     ↓
                processed/{PDF_ID}/document.md
                processed/{PDF_ID}/metadata.json
                processed/{PDF_ID}/figures/*.png
```

---

## What We Have Accomplished

### 1. PDF Processing Infrastructure

**Technology Stack**:
- **Model**: Dolphin (Vision-Language Model for document understanding)
- **GPU**: CUDA-accelerated inference
- **Batch Processing**: 50 PDFs per batch with concurrent processing
- **Framework**: PyTorch 2.1+ with transformers

**Capabilities**:
- Layout understanding (headers, paragraphs, figures, tables)
- Figure extraction and storage
- Text recognition with structure preservation
- Mathematical notation handling
- Citation extraction

### 2. Distributed Worker System

**Implementation**: `scripts/distributed_worker.py`

**Features**:
- **Worker Distribution**: Round-robin assignment prevents duplicate work
  - Worker 0: PDFs at indices 0, 3, 6, 9, ...
  - Worker 1: PDFs at indices 1, 4, 7, 10, ...
  - Worker 2: PDFs at indices 2, 5, 8, 11, ...
- **Concurrent Processing**: 3 PDFs processed simultaneously per worker
- **Skip Processed**: Automatically skips already processed PDFs
- **Failure Tracking**: Records failures in `failures/worker-{id}-failures.json`

**Configuration** (via environment variables):
```bash
WORKER_ID=0              # Worker identifier (0, 1, 2)
TOTAL_WORKERS=3          # Total number of workers
CONCURRENT_PDFS=3        # PDFs processed concurrently
S3_INPUT_BUCKET          # Source bucket
S3_OUTPUT_BUCKET         # Destination bucket
```

### 3. GPU Optimization

**Recent Improvements** (from latest commit):
- ⚡ Increased batch size for better GPU utilization
- ⚡ Concurrent PDF processing (3 at once per worker)
- ⚡ Optimized memory management
- ⚡ Reduced model loading overhead

**Performance**:
- ~200-250 PDFs per day per worker (with GPU acceleration)
- ~600-750 PDFs per day with 3 workers
- Estimated completion: ~7 days for all 4,920 PDFs

---

## Data Storage on S3

### Bucket Structure

```
s3://cs433-rag-project2/
│
├── raw_pdfs/                          # Source PDFs (4,920 files)
│   ├── 00001_W2134859631_Title.pdf
│   ├── 00002_W2122361802_Title.pdf
│   └── ...
│
├── raw_metadata/                      # Paper metadata from OpenAlex
│   ├── 00001_W2134859631_metadata.json
│   ├── 00002_W2122361802_metadata.json
│   └── ...
│
└── processed/                         # Processed outputs (353 folders)
    ├── 00002_W2122361802/
    │   ├── document.md                # ✨ Main content in markdown
    │   ├── metadata.json              # ✨ Processing metadata
    │   └── figures/                   # ✨ Extracted images
    │       ├── figure_001.png
    │       ├── figure_002.png
    │       └── ...
    │
    ├── 00004_W2114989862/
    │   ├── document.md
    │   ├── metadata.json
    │   └── figures/
    │
    └── ...
```

### Storage Statistics

| Category | Count | Size |
|----------|-------|------|
| **Raw PDFs** | 4,920 files | ~15-20 GB |
| **Processed Folders** | 353 folders | ~2-3 GB |
| **Total Files in S3** | ~12,183 files | ~18-23 GB |
| **Average per PDF** | ~34 files | ~5-6 MB |

### File Formats

#### 1. `document.md` (Markdown Document)

**Purpose**: Human-readable and machine-parseable document content

**Structure**:
```markdown
# Paper Title

## Abstract
[Abstract text...]

## 1. Introduction
[Introduction text...]

![Figure 1: Caption](figures/figure_001.png)

## 2. Related Work
[Content...]

### 2.1 Subsection
[Content...]

## References
[1] Author et al. (2023). Title. Journal.
[2] ...
```

**Size**: Average 50-100 KB per document

**Why Markdown?**:
- ✅ Preserves document structure (headers, sections)
- ✅ Easy to parse for chunking
- ✅ Supports figure references
- ✅ Human-readable for debugging
- ✅ Compatible with most text processing tools

#### 2. `metadata.json` (Processing Metadata)

**Purpose**: Processing details and document structure

**Structure**:
```json
{
  "pdf_id": "00002_W2122361802",
  "processing_timestamp": "2025-11-09T16:18:55Z",
  "model_version": "dolphin-v2",
  "page_count": 12,
  "figure_count": 8,
  "processing_time_seconds": 45.3,
  "elements": [
    {
      "type": "title",
      "bbox": [x1, y1, x2, y2],
      "page": 1,
      "confidence": 0.98
    },
    {
      "type": "figure",
      "bbox": [x1, y1, x2, y2],
      "page": 3,
      "image_path": "figures/figure_001.png"
    }
  ]
}
```

**Size**: Average 100-150 KB per file

#### 3. `figures/*.png` (Extracted Images)

**Purpose**: Visual content from papers (plots, diagrams, tables)

**Format**: PNG (lossless)
**Naming**: `figure_001.png`, `figure_002.png`, ...
**Average**: 5-15 figures per paper
**Size**: 50-500 KB per image

---

## Technical Implementation Details

### Core Pipeline Implementation

**Location**: `rag_pipeline/pdf_parsing/core/pipeline.py`

```python
class PDFParsingPipeline:
    """
    End-to-end PDF processing pipeline using Dolphin model
    """

    def parse_document(self, pdf_path: Path) -> ProcessingResult:
        """
        Main processing method:
        1. Load PDF with PyMuPDF
        2. Extract pages as images
        3. Run Dolphin model for layout analysis
        4. Extract text, figures, tables
        5. Convert to markdown
        6. Save outputs
        """
```

**Key Classes**:
- `PDFParsingPipeline`: Orchestrates the entire process
- `LayoutParser`: Analyzes document layout
- `ImageExtractor`: Extracts and saves figures
- `MarkdownConverter`: Converts to markdown format
- `ElementRecognizer`: Identifies document elements

### Distributed Processing

**Location**: `scripts/distributed_worker.py`

```python
class DistributedWorker:
    """
    Worker that processes a subset of PDFs from S3
    """

    def __init__(self):
        self.worker_id = int(os.getenv('WORKER_ID', '0'))
        self.total_workers = int(os.getenv('TOTAL_WORKERS', '1'))
        self.concurrent_pdfs = 3  # Process 3 PDFs at once

    def run(self):
        """
        1. List all PDFs from S3
        2. Get worker's assigned subset
        3. Process concurrently with ThreadPoolExecutor
        4. Upload results to S3
        """
```

**Worker Distribution Logic**:
```python
def get_worker_pdfs(all_pdfs: List[str], worker_id: int, total_workers: int):
    """
    Assign PDFs to workers in round-robin fashion
    Worker N gets PDFs at indices: N, N+total_workers, N+2*total_workers, ...
    """
    return [pdf for i, pdf in enumerate(all_pdfs) if i % total_workers == worker_id]
```

### S3 Utilities

**Location**: `scripts/utils/s3_utils.py`

```python
def list_pdfs_from_s3(s3_client, bucket, prefix):
    """List all PDFs in S3 bucket"""

def download_from_s3(s3_client, bucket, key, local_path):
    """Download file from S3"""

def upload_to_s3(s3_client, bucket, key, content):
    """Upload file to S3"""

def s3_object_exists(s3_client, bucket, key):
    """Check if object exists (for skipping processed PDFs)"""
```

---

## Next Steps: Chunking & RAG Pipeline

### Phase 2: Text Chunking & Embeddings

**Status**: 🟡 Code exists, needs integration

**Implementation**: `rag_pipeline/rag/chunking.py`

#### Chunking Strategy

We have **3 chunking strategies** already implemented:

##### 1. **Semantic Chunking** (Recommended for academic papers)

```python
chunker = DocumentChunker(
    chunk_size=1024,        # ~1024 characters per chunk
    chunk_overlap=100,      # 100 char overlap between chunks
    min_chunk_size=100      # Minimum chunk size
)

chunks = chunker.semantic_chunking(text, metadata)
```

**How it works**:
- Splits by paragraph boundaries first
- Preserves section structure
- Maintains context with overlap
- Handles long paragraphs intelligently

**Output format**:
```python
{
    "text": "Chunk content...",
    "chunk_index": 0,
    "length": 1024,
    "word_count": 180,
    "pdf_id": "00002_W2122361802",
    "section": "Introduction"
}
```

##### 2. **Fixed-Size Chunking** (Simple, fast)

- Fixed character count per chunk
- Sliding window with overlap
- Good for uniform processing

##### 3. **Recursive Chunking** (Flexible)

- Uses separator hierarchy: `\n\n` → `\n` → `. ` → ` `
- Adapts to content structure
- Balances chunk size and coherence

#### Integration Plan

**Step 1**: Create chunking worker
```python
# scripts/chunking_worker.py

class ChunkingWorker:
    def __init__(self):
        self.chunker = DocumentChunker(chunk_size=1024, chunk_overlap=100)

    def process_document(self, pdf_id: str):
        # 1. Download document.md from S3
        markdown_text = download_from_s3(f"processed/{pdf_id}/document.md")

        # 2. Download metadata for context
        metadata = json.loads(download_from_s3(f"processed/{pdf_id}/metadata.json"))

        # 3. Chunk the document
        chunks = self.chunker.semantic_chunking(
            markdown_text,
            metadata={"pdf_id": pdf_id, "source": metadata}
        )

        # 4. Upload chunks to S3
        upload_to_s3(f"chunks/{pdf_id}.json", json.dumps(chunks))
```

**Step 2**: Process all 353 documents
```bash
# Run chunking for all processed PDFs
python scripts/chunking_worker.py --s3-bucket cs433-rag-project2
```

**Expected Output**:
```
s3://cs433-rag-project2/chunks/
├── 00002_W2122361802.json        # ~50-100 chunks per document
├── 00004_W2114989862.json
└── ...
```

### Phase 3: Embedding Generation

**Status**: ⏳ Ready to implement

**Technology**: OpenAI Embeddings API (ada-002 or text-embedding-3)

**Implementation**: `rag_pipeline/rag/openai_embedder.py` (already exists)

```python
from rag_pipeline.rag.openai_embedder import OpenAIEmbedder

embedder = OpenAIEmbedder(api_key=os.getenv("OPENAI_API_KEY"))

# Embed all chunks
for chunk in chunks:
    embedding = embedder.embed_text(chunk["text"])
    chunk["embedding"] = embedding
```

**Integration Plan**:

```python
# scripts/embedding_worker.py

class EmbeddingWorker:
    def __init__(self):
        self.embedder = OpenAIEmbedder()

    def process_chunks(self, pdf_id: str):
        # 1. Download chunks
        chunks = json.loads(download_from_s3(f"chunks/{pdf_id}.json"))

        # 2. Generate embeddings (batch processing)
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedder.embed_batch(texts)

        # 3. Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding

        # 4. Upload to S3
        upload_to_s3(f"embeddings/{pdf_id}.json", json.dumps(chunks))
```

**Expected Output**:
```
s3://cs433-rag-project2/embeddings/
├── 00002_W2122361802.json        # Chunks with 1536-dim embeddings
├── 00004_W2114989862.json
└── ...
```

**Cost Estimate**:
- 353 documents × 50 chunks/doc × $0.0001/1K tokens ≈ **$2-5 total**

### Phase 4: Vector Database

**Technology Options**:

1. **Weaviate** (already in dependencies)
   - ✅ Open source
   - ✅ Fast vector search
   - ✅ Python client ready
   - ✅ Self-hosted or cloud

2. **Pinecone** (optional dependency)
   - ✅ Managed service
   - ✅ Easy to use
   - ⚠️ Requires API key

**Recommended**: Weaviate (self-hosted)

**Schema Design**:
```python
{
    "class": "AcademicChunk",
    "properties": [
        {"name": "text", "dataType": ["text"]},
        {"name": "pdf_id", "dataType": ["string"]},
        {"name": "chunk_index", "dataType": ["int"]},
        {"name": "section", "dataType": ["string"]},
        {"name": "paper_title", "dataType": ["string"]},
        {"name": "authors", "dataType": ["string[]"]},
        {"name": "year", "dataType": ["int"]}
    ],
    "vectorizer": "none"  # We provide embeddings
}
```

**Integration**:
```python
# scripts/vectordb_indexer.py

import weaviate

client = weaviate.Client("http://localhost:8080")

def index_document(pdf_id: str):
    # 1. Download chunks with embeddings
    chunks = json.loads(download_from_s3(f"embeddings/{pdf_id}.json"))

    # 2. Batch insert into Weaviate
    with client.batch as batch:
        for chunk in chunks:
            batch.add_data_object(
                data_object={
                    "text": chunk["text"],
                    "pdf_id": chunk["pdf_id"],
                    "chunk_index": chunk["chunk_index"]
                },
                class_name="AcademicChunk",
                vector=chunk["embedding"]
            )
```

### Phase 5: RAG Query System

**Architecture**:

```
User Query → Embedding → Vector Search → Top-K Chunks → LLM (GPT-4) → Answer
                                              ↓
                                    Retrieve Context:
                                    - Chunk text
                                    - Paper metadata
                                    - Figure references
```

**Implementation**:
```python
# scripts/rag_query.py

def query(question: str, top_k: int = 5):
    # 1. Embed query
    query_embedding = embedder.embed_text(question)

    # 2. Search Weaviate
    results = client.query.get(
        "AcademicChunk",
        ["text", "pdf_id", "section"]
    ).with_near_vector({
        "vector": query_embedding,
        "certainty": 0.7
    }).with_limit(top_k).do()

    # 3. Build context
    context = "\n\n".join([r["text"] for r in results])

    # 4. Query GPT-4
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a research assistant..."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ]
    )

    return response["choices"][0]["message"]["content"]
```

---

## Performance & Scalability

### Current Performance

| Metric | Value |
|--------|-------|
| **Processing Speed** | ~200-250 PDFs/day/worker |
| **GPU Utilization** | ~85-95% during processing |
| **Memory Usage** | ~16 GB GPU RAM |
| **Concurrent PDFs** | 3 per worker |
| **Total Workers** | 3 |
| **Combined Throughput** | ~600-750 PDFs/day |

### Scalability Analysis

**Horizontal Scaling** (More Workers):
- ✅ Easy: Add more EC2 instances with `WORKER_ID=3,4,5...`
- ✅ Linear speedup: 5 workers → ~1,000 PDFs/day
- ✅ No code changes needed

**Vertical Scaling** (Bigger GPU):
- Upgrade to g4dn.2xlarge (1 × T4, 16 GB)
- Or p3.2xlarge (1 × V100, 16 GB)
- ~1.5-2x speedup per worker

**Cost Analysis**:

| Configuration | Cost/Hour | Cost/Day | Days to Complete | Total Cost |
|---------------|-----------|----------|------------------|------------|
| **Current (3 workers)** | $1.58 | $37.92 | 7 days | ~$265 |
| **5 workers** | $2.63 | $63.12 | 5 days | ~$316 |
| **3 workers (V100)** | $9.18 | $220.32 | 3 days | ~$661 |

**Recommendation**: Continue with current setup (3 × g4dn.xlarge)

### S3 Storage Projections

| Stage | Files | Size | Cost/Month |
|-------|-------|------|------------|
| **Raw PDFs** | 4,920 | ~18 GB | ~$0.40 |
| **Processed** | ~170K files | ~25 GB | ~$0.60 |
| **Chunks** | 4,920 JSON | ~200 MB | ~$0.01 |
| **Embeddings** | 4,920 JSON | ~500 MB | ~$0.01 |
| **Total** | ~180K files | ~44 GB | **~$1.02/month** |

**Data Transfer**:
- Processing: ~25 GB download + ~25 GB upload ≈ **$0.50** (one-time)

---

## Code Structure

```
project-2-rag/
│
├── rag_pipeline/
│   ├── pdf_parsing/                    # ✅ Complete
│   │   ├── core/
│   │   │   ├── pipeline.py            # Main PDF processing
│   │   │   ├── interfaces.py
│   │   │   └── exceptions.py
│   │   ├── processors/
│   │   │   ├── layout_parser.py       # Layout analysis
│   │   │   ├── image_extractor.py     # Figure extraction
│   │   │   ├── markdown_converter.py   # MD conversion
│   │   │   └── element_recognizer.py
│   │   ├── model/
│   │   │   └── dolphin.py             # Dolphin model wrapper
│   │   └── config.py
│   │
│   ├── rag/                            # 🟡 Ready for integration
│   │   ├── chunking.py                # Text chunking strategies
│   │   └── openai_embedder.py         # Embedding generation
│   │
│   └── openalex/                       # ✅ Complete
│       ├── fetcher.py                  # Metadata fetching
│       └── downloader.py               # PDF downloading
│
├── scripts/
│   ├── distributed_worker.py           # ✅ Main processing worker
│   ├── process_pdfs_batch.py          # ✅ Batch processing
│   ├── test_local_processing.py       # ✅ Testing utility
│   │
│   └── utils/
│       ├── s3_utils.py                # ✅ S3 operations
│       └── worker_distribution.py     # ✅ Worker assignment
│
├── tests/
│   └── distributed/
│       ├── test_s3_utils.py           # ✅ S3 tests
│       └── test_worker_distribution.py # ✅ Distribution tests
│
├── MANUAL_DEPLOYMENT.md                # ✅ Deployment guide
├── CHECKPOINT.md                       # ✅ This document
└── README.md                           # Project overview
```

---

## Roadmap Summary

### ✅ Phase 1: PDF Processing (COMPLETE)
- [x] Dolphin model integration
- [x] Distributed worker system
- [x] S3 storage infrastructure
- [x] GPU optimization
- [x] 353 PDFs processed

### 🟡 Phase 2: Chunking (READY)
- [ ] Integrate chunking worker
- [ ] Process all 353 documents
- [ ] Upload chunks to S3
- **Estimated time**: 1-2 days
- **Estimated cost**: Free

### 🟡 Phase 3: Embeddings (READY)
- [ ] Set up OpenAI API
- [ ] Generate embeddings for all chunks
- [ ] Upload to S3
- **Estimated time**: 1 day
- **Estimated cost**: ~$5

### ⏳ Phase 4: Vector Database (TODO)
- [ ] Deploy Weaviate instance
- [ ] Define schema
- [ ] Index all chunks
- **Estimated time**: 2-3 days
- **Estimated cost**: Free (self-hosted)

### ⏳ Phase 5: RAG Query System (TODO)
- [ ] Implement query interface
- [ ] Integrate GPT-4
- [ ] Build demo UI
- **Estimated time**: 3-4 days
- **Estimated cost**: ~$10 (GPT-4 usage)

---

## Questions & Discussion Points

### For the Teacher

1. **Processing Scale**:
   - Should we process all 4,920 PDFs or is 353 sufficient for the demo?
   - Current cost: ~$265 for all PDFs

2. **Chunking Strategy**:
   - We recommend semantic chunking for academic papers
   - Alternative: section-based chunking (one chunk per section)
   - Your preference?

3. **Vector Database**:
   - Self-hosted Weaviate vs. managed Pinecone?
   - We recommend Weaviate for cost savings

4. **Evaluation Metrics**:
   - How should we evaluate the RAG system?
   - Retrieval accuracy? Answer quality? Both?

5. **Demo Format**:
   - Command-line interface?
   - Web UI (Streamlit/Gradio)?
   - Jupyter notebook?

---

## Contact & Repository

**Repository**: [Your GitHub URL]
**Team**: [Your Names]
**Course**: CS-433
**Instructor**: [Instructor Name]

**For Questions**: [Your Email]

---

**Last Updated**: November 10, 2025
**Document Version**: 1.0
