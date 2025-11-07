# PDF-to-RAG System with Dolphin Model

## Overview

This project implements a complete RAG (Retrieval Augmented Generation) system that processes PDF documents using the ByteDance Dolphin multimodal model, converts them to machine-readable markdown with proper citations, and enables semantic search and retrieval with reranking capabilities.

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   PDF       │─────▶│   Dolphin    │─────▶│  Markdown   │
│ Documents   │      │   Model      │      │  + Citations│
└─────────────┘      │ (Vast.ai GPU)│      └─────────────┘
                     └──────────────┘             │
                                                  │
                                                  ▼
                     ┌──────────────┐      ┌─────────────┐
                     │   OpenAI     │◀─────│   Chunk &   │
                     │  Embeddings  │      │   Process   │
                     └──────────────┘      └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Vector DB  │
                     │(Pinecone or  │
                     │  Weaviate)   │
                     └──────────────┘
                            │
                            ▼
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│    Query    │─────▶│  Retrieval   │─────▶│  Reranking  │
│             │      │   (k-NN)     │      │  Mechanism  │
└─────────────┘      └──────────────┘      └─────────────┘
                                                  │
                                                  ▼
                                           ┌─────────────┐
                                           │   Final     │
                                           │  Results    │
                                           └─────────────┘
```

## System Components

### 1. GPU Infrastructure (Vast.ai)

**Purpose**: Host the ByteDance Dolphin model for PDF processing

**Specifications**:
- GPU: NVIDIA GPU with at least 24GB VRAM (recommended: A6000, RTX 4090, or A100)
- CUDA: 11.8 or higher
- RAM: 32GB+ system RAM
- Storage: 100GB+ for model weights and temporary files

**Why Vast.ai**: Cost-effective GPU rental for running large multimodal models on-demand

### 2. ByteDance Dolphin Model

**Purpose**: Convert PDF documents to structured markdown with citations

**Capabilities**:
- Multimodal understanding (text + images + tables)
- Layout preservation and structure recognition
- Citation extraction and formatting
- OCR for scanned documents
- Table and figure captioning

**Model Details**:
- Repository: `bytedance/dolphin`
- Type: Vision-Language Model (VLM)
- Input: PDF files (converted to images per page)
- Output: Structured markdown with metadata

### 3. Document Processing Pipeline

**Workflow**:

1. **PDF Ingestion**
   - Accept PDF files via API or batch processing
   - Extract metadata (title, author, date, etc.)
   - Convert PDF pages to high-resolution images

2. **Dolphin Processing**
   - Send page images to Dolphin model
   - Extract text, tables, figures, and citations
   - Preserve document structure (headings, lists, code blocks)
   - Generate machine-readable markdown

3. **Markdown Enrichment**
   - Add citation metadata
   - Create document hierarchy
   - Link references and footnotes
   - Preserve mathematical equations (LaTeX format)

4. **Chunking Strategy**
   - Semantic chunking (preserve paragraph/section boundaries)
   - Chunk size: 512-1024 tokens
   - Overlap: 50-100 tokens for context preservation
   - Maintain citation context in chunks

### 4. Embedding Generation (OpenAI)

**Model**: `text-embedding-3-large` or `text-embedding-ada-002`

**Process**:
- Generate embeddings for each markdown chunk
- Dimensions: 1536 (ada-002) or 3072 (3-large)
- Batch processing for efficiency
- Rate limiting and error handling

**Metadata Storage**:
```json
{
  "chunk_id": "doc123_chunk_45",
  "document_id": "doc123",
  "document_title": "Research Paper Title",
  "page_number": 5,
  "citations": ["Smith et al. 2023", "Jones 2022"],
  "chunk_text": "...",
  "embedding": [0.123, -0.456, ...]
}
```

### 5. Vector Database

**Options**: Pinecone or Weaviate

#### Pinecone Setup
```python
# Index configuration
{
  "dimension": 1536,  # or 3072 for larger model
  "metric": "cosine",
  "pods": 1,
  "pod_type": "p1.x1"  # or higher for larger datasets
}
```

#### Weaviate Setup
```python
# Schema configuration
{
  "class": "Document",
  "vectorizer": "none",  # using OpenAI embeddings
  "properties": [
    {"name": "chunk_text", "dataType": ["text"]},
    {"name": "document_title", "dataType": ["string"]},
    {"name": "citations", "dataType": ["string[]"]},
    {"name": "page_number", "dataType": ["int"]}
  ]
}
```

### 6. Reranking Mechanism

**Purpose**: Improve retrieval quality by reordering results based on relevance

**Approach**: Advanced reranking model (researching "Zero Entropy" or similar approaches)

**Options**:
1. **Cross-Encoder Reranking**
   - Model: `cross-encoder/ms-marco-MiniLM-L-6-v2`
   - Scores query-document pairs
   - More accurate than embedding similarity alone

2. **Cohere Rerank**
   - API-based reranking
   - Multilingual support
   - High accuracy

3. **LLM-based Reranking**
   - Use GPT-4 or similar to score relevance
   - Expensive but highly accurate

**Workflow**:
1. Retrieve top-k documents (k=50-100) using vector similarity
2. Rerank using reranking model
3. Return top-n results (n=5-10)

### 7. RAG Query Pipeline

**Query Flow**:

1. **Query Processing**
   - Receive user query
   - Generate query embedding using OpenAI
   - Optional: query expansion or reformulation

2. **Retrieval**
   - Semantic search in vector database
   - Retrieve top-k candidates (k=50-100)
   - Apply metadata filters if needed

3. **Reranking**
   - Rerank candidates using reranking model
   - Select top-n most relevant chunks (n=5-10)

4. **Context Assembly**
   - Combine retrieved chunks
   - Include citation information
   - Format for LLM consumption

5. **Generation** (optional)
   - Send context + query to LLM
   - Generate response with citations
   - Return to user

## Implementation Plan

### Phase 1: Infrastructure Setup
- [ ] Set up Vast.ai account and select GPU instance
- [ ] Create Docker container for Dolphin model
- [ ] Set up API endpoints for PDF processing
- [ ] Configure environment variables and secrets

### Phase 2: Document Processing
- [ ] Implement PDF to image conversion
- [ ] Integrate Dolphin model for markdown generation
- [ ] Build citation extraction logic
- [ ] Create chunking strategy
- [ ] Test with sample PDFs

### Phase 3: Embedding & Storage
- [ ] Set up OpenAI API integration
- [ ] Choose and configure vector database (Pinecone vs Weaviate)
- [ ] Implement batch embedding generation
- [ ] Create indexing pipeline
- [ ] Build metadata management

### Phase 4: Retrieval & Reranking
- [ ] Implement semantic search
- [ ] Integrate reranking mechanism
- [ ] Optimize retrieval parameters
- [ ] Add filtering and metadata search

### Phase 5: RAG Pipeline
- [ ] Build query processing
- [ ] Create end-to-end RAG pipeline
- [ ] Add LLM integration for generation
- [ ] Implement citation formatting

### Phase 6: Testing & Optimization
- [ ] Create test suite
- [ ] Benchmark retrieval accuracy
- [ ] Optimize chunking and embedding parameters
- [ ] Load testing and performance optimization

## Project Structure

```
project-2-rag/
├── README.md                    # This file
├── docs/                        # Documentation
│   ├── api.md                   # API documentation
│   ├── deployment.md            # Deployment guide
│   └── examples.md              # Usage examples
├── src/
│   ├── dolphin/                 # Dolphin model integration
│   │   ├── model.py             # Model loading and inference
│   │   ├── pdf_processor.py    # PDF to markdown conversion
│   │   └── citation_extractor.py
│   ├── embeddings/              # Embedding generation
│   │   ├── openai_embedder.py
│   │   └── chunking.py
│   ├── vectordb/                # Vector database integration
│   │   ├── pinecone_client.py
│   │   ├── weaviate_client.py
│   │   └── base.py
│   ├── retrieval/               # Retrieval and reranking
│   │   ├── retriever.py
│   │   ├── reranker.py
│   │   └── query_processor.py
│   ├── rag/                     # RAG pipeline
│   │   ├── pipeline.py
│   │   └── generator.py
│   └── api/                     # API endpoints
│       ├── main.py
│       └── routes/
├── scripts/                     # Utility scripts
│   ├── deploy_vastai.py         # Vast.ai deployment automation
│   ├── setup_vectordb.py        # Vector DB initialization
│   └── batch_process.py         # Batch PDF processing
├── tests/                       # Test suite
├── docker/                      # Docker configurations
│   ├── Dockerfile.dolphin       # Dolphin model container
│   └── docker-compose.yml
├── config/                      # Configuration files
│   ├── config.yaml
│   └── .env.example
└── requirements.txt             # Python dependencies
```

## Key Technologies

- **Python 3.10+**: Core language
- **PyTorch**: Deep learning framework for Dolphin model
- **Transformers**: Hugging Face library for model loading
- **FastAPI**: API framework
- **OpenAI Python SDK**: Embeddings generation
- **Pinecone/Weaviate**: Vector database
- **PyPDF2/pdf2image**: PDF processing
- **Docker**: Containerization
- **Vast.ai**: GPU infrastructure

## Environment Variables

```bash
# Vast.ai
VASTAI_API_KEY=your_vastai_api_key

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Vector Database (choose one)
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_environment
# OR
WEAVIATE_URL=your_weaviate_url
WEAVIATE_API_KEY=your_weaviate_key

# Model Configuration
DOLPHIN_MODEL_PATH=/models/dolphin
GPU_MEMORY_LIMIT=24GB
BATCH_SIZE=4

# Chunking Configuration
CHUNK_SIZE=1024
CHUNK_OVERLAP=100

# Retrieval Configuration
TOP_K_RETRIEVAL=50
TOP_N_RERANK=10
```

## Cost Estimates

### GPU (Vast.ai)
- **RTX 4090**: ~$0.30-0.50/hour
- **A6000**: ~$0.40-0.70/hour
- **A100**: ~$1.00-2.00/hour

**Monthly estimate** (8 hours/day): $72-$480/month

### OpenAI Embeddings
- **text-embedding-3-large**: $0.13 per 1M tokens
- **Typical document**: ~2,000 tokens
- **1,000 documents**: ~$0.26

### Vector Database
- **Pinecone**: ~$70/month (1M vectors)
- **Weaviate Cloud**: ~$25/month (starter tier)

**Total estimated monthly cost**: $100-$600 depending on usage

## Success Metrics

1. **PDF Processing Quality**
   - Citation accuracy: >95%
   - Layout preservation score: >90%
   - OCR accuracy (if needed): >98%

2. **Retrieval Performance**
   - Retrieval accuracy (MRR): >0.85
   - Reranking improvement: >10% over baseline
   - Query latency: <500ms

3. **System Reliability**
   - Uptime: >99%
   - Error rate: <1%
   - Successful PDF processing rate: >98%

## Next Steps

1. Review this documentation and confirm the approach
2. Set up development environment
3. Begin Phase 1: Infrastructure Setup
4. Iterate based on testing results

---

**Last Updated**: 2025-11-06
**Version**: 1.0.0
