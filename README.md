# Evidence-Based Policy Support Through RAG

A production-scale Retrieval-Augmented Generation (RAG) system for patent policy research that synthesizes 4,920+ peer-reviewed academic papers to support evidence-based intellectual property policymaking.

## Table of Contents

- [What is This Project?](#what-is-this-project)
- [The Problem We're Solving](#the-problem-were-solving)
- [System Architecture](#system-architecture)
- [Key Innovations](#key-innovations)
- [How It Works: The Four-Stage RAG Pipeline](#how-it-works-the-four-stage-rag-pipeline)
- [Corpus and Bias Analysis](#corpus-and-bias-analysis)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Technology Stack](#technology-stack)
- [Performance Metrics](#performance-metrics)
- [Documentation](#documentation)

## What is This Project?

This is a **complete end-to-end RAG system** designed to help policymakers, researchers, and analysts navigate the vast landscape of patent policy research. With 4,920+ peer-reviewed papers spanning economics, law, and innovation studies, finding relevant evidence for policy decisions is prohibitively time-consuming using traditional methods.

Our system enables **natural language queries** like:
- "What is the effect of R&D tax credits on innovation?"
- "Does patent litigation reduce startup formation?"
- "How do different countries measure patent quality?"
- "What if we strengthen patent protection in the pharmaceutical sector?"

And returns **evidence-based answers** with:
- ✅ Structured synthesis of relevant research
- ✅ Direct citations to source papers
- ✅ Quantitative details from studies
- ✅ Transparent acknowledgment of evidence limitations
- ✅ Geographic and methodological context

## The Problem We're Solving

### Challenge: Information Overload in Policy Research

Evidence-based IP policymaking requires synthesizing vast academic literature across multiple disciplines. Traditional approaches fall short:

- **Manual literature review**: 20-30 minutes per query, selection bias, limited coverage
- **Google Scholar**: No domain-specific ranking, no synthesis, overwhelming results
- **Generic LLMs** (e.g., ChatGPT): Fast but fabricates citations, lacks domain knowledge, can't trace evidence

### Our Solution: Domain-Specific RAG System

We built a specialized RAG system that:
1. **Processes 4,920 academic papers** with vision-language understanding (preserving equations, tables, figures)
2. **Maintains source traceability** with citation preservation and metadata
3. **Provides multi-model LLM infrastructure** with vendor-agnostic inference
4. **Analyzes and acknowledges corpus biases** across 6 dimensions (geography, language, methodology, institutions, venues, temporality)

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER INTERACTION LAYER                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │   Next.js Frontend (React, TypeScript, i18n)                         │   │
│  │   - Natural language query input                                     │   │
│  │   - Multi-model LLM selection (10 models)                            │   │
│  │   - Structured response display (4 sections)                         │   │
│  │   - Direct PDF access via citations                                  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            API SERVICE LAYER                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │   FastAPI Backend                                                    │   │
│  │   - /search: Query processing and retrieval                          │   │
│  │   - /chat: Conversational interface                                  │   │
│  │   - /models: LLM model management                                    │   │
│  │   - /health: System status monitoring                                │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RAG PIPELINE (4 STAGES)                              │
│                                                                              │
│  Stage 1: DISTRIBUTED PDF PROCESSING                                        │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  3 GPU Workers (EC2 g5.xlarge, NVIDIA A10G, 24GB VRAM)            │    │
│  │  - Dolphin VLM: Vision-language PDF extraction                     │    │
│  │  - Preserves: equations, tables, figures, citations, structure     │    │
│  │  - Output: Structured Markdown + metadata                          │    │
│  │  - Performance: 200-250 papers/day/worker, 87% GPU utilization     │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                     ▼                                        │
│  Stage 2: KNOWLEDGE REPRESENTATION                                          │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  Hybrid Structure-Aware Chunking                                   │    │
│  │  - Splits at section boundaries (markdown headers)                 │    │
│  │  - Preserves citation context (±1 sentence)                        │    │
│  │  - Target: ~420 tokens/chunk (SD=180)                              │    │
│  │  - Citation preservation: 55.2%                                     │    │
│  │                                                                     │    │
│  │  OpenAI text-embedding-3-small (1536D)                             │    │
│  │  - Embeds: title ⊕ section ⊕ chunk_text                           │    │
│  │  - 28,000 vectors total                                            │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                     ▼                                        │
│  Stage 3: HYBRID RETRIEVAL                                                  │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  Two-Stage Pipeline:                                               │    │
│  │  1. FAISS (HNSW): Retrieve top-75 candidates (<50ms)              │    │
│  │  2. ZeroEntropy cross-encoder: Rerank to top-10                   │    │
│  │     - Captures fine-grained query-document relevance              │    │
│  │     - Graceful degradation to FAISS-only on failure               │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                     ▼                                        │
│  Stage 4: MULTI-MODEL LLM GENERATION                                        │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  LiteLLM + OpenRouter (10 models across 3 tiers)                  │    │
│  │  - Fast: gpt-5-mini, gemini-3-pro ($0.12/query)                   │    │
│  │  - Balanced: claude-3.5-sonnet, deepseek-chat                     │    │
│  │  - Premium: claude-sonnet-4.5, deepseek-r1                        │    │
│  │                                                                     │    │
│  │  Structured Prompts Enforce:                                       │    │
│  │  - 4-section response (Summary, Analysis, Policy, References)     │    │
│  │  - Evidence quality labels                                         │    │
│  │  - Quantitative details                                            │    │
│  │  - Explicit limitation acknowledgment                              │    │
│  │  - Bilingual support (English/French)                             │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA STORAGE & INFRASTRUCTURE                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │   AWS S3 (cs433-rag-project2)                                       │   │
│  │   - raw_pdfs/: 4,920 academic papers                                │   │
│  │   - processed/: 999 structured markdown documents (20.3%)           │   │
│  │   - raw_metadata/: OpenAlex metadata (authors, venues, citations)   │   │
│  │   - failures/: Processing error reports                             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │   FAISS Vector Database                                             │   │
│  │   - 28,000 chunk embeddings (1536D)                                 │   │
│  │   - HNSW index for sub-50ms retrieval                               │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Innovations

### 1. Vision-Language PDF Processing with Equation Preservation

**Why it matters**: Patent policy papers contain critical information in equations (economic models, innovation metrics), tables (empirical results), and figures (causal diagrams) that text-only extractors completely miss.

**Our approach**:
- **Dolphin VLM** (8B-parameter vision-language model) processes PDF pages as images
- Extracts and renders **LaTeX equations** (e.g., `$\pi = pq - C(q)$`, `$R\&D_{it}/Sales_{it}$`)
- Preserves **citations** (23.4 avg/paper vs 12.3-18.7 for text-only tools)
- Maintains **document structure** (sections, subsections, paragraphs)
- **Distributed processing**: 3 GPU workers with deterministic hashing and S3 checkpointing

**Result**: 200-250 papers/day/worker at 87% GPU utilization with full semantic preservation.

### 2. Hybrid Structure-Aware Chunking for Citation Preservation

**Why it matters**: Evidence-based policymaking requires tracing claims back to original sources. When a system says "R&D tax credits increase innovation by 15%", policymakers must verify methodology and context.

**Our approach**:
- **Hybrid Semantic Chunking**: Splits at section boundaries, subdivides large sections at subsection/paragraph boundaries
- **Citation context preservation**: ±1 sentence around each citation
- **Controlled variance**: ~420 tokens/chunk (SD=180) for consistent embeddings
- **Benchmarked**: 55.2% citation preservation vs 44.6% for fixed-size chunking

**Result**: Optimal balance between semantic coherence and source traceability.

### 3. Multi-Model LLM Infrastructure with Automatic Failover

**Why it matters**: Avoid vendor lock-in, optimize cost/quality trade-offs, ensure uptime during API transitions.

**Our approach**:
- **LiteLLM**: Unified API abstraction across OpenAI, Anthropic, Google, DeepSeek
- **OpenRouter**: Model aggregation with 10 models across 3 performance tiers
- **Automatic failover**: Transparent provider switching during outages
- **Cost optimization**: $0.12/query average (Fast tier) to $0.50+ (Premium tier)

**Result**: Zero-downtime deployment with flexible model selection for different query types.

### 4. Systematic Corpus Bias Analysis

**Why it matters**: RAG systems risk reinforcing existing knowledge gaps. If the corpus over-represents certain geographies or methodologies, policy recommendations will systematically exclude alternative perspectives.

**Our approach**: Six-dimensional demographic analysis:
1. **Geography**: 78% concentration in 5 countries (US 27.5%, UK 8.4%, China 7.1%, Brazil 5.9%, France 4.2%)
2. **Language**: 96% English dominance (4,399/4,897 papers)
3. **Methodology**: 64% quantitative, 18% theory, 11% qualitative (N=100 sample)
4. **Institutions**: 72.4% academic (may underweight practitioner knowledge)
5. **Venues**: 1,624 unique sources (69% journals, 25.2% preprints)
6. **Temporality**: 48.6% post-2015, 34.6% 2005-2015, 16.9% pre-2005

**Result**: Transparent acknowledgment of corpus limitations in system responses. Users are warned when evidence is geographically/methodologically constrained.

## How It Works: The Four-Stage RAG Pipeline

### Stage 1: Distributed PDF Processing

**Input**: 4,920 academic PDFs from OpenAlex API (1990-2024, peer-reviewed only)

**Processing**:
1. **Work distribution**: 3 EC2 g5.xlarge instances with deterministic hashing (`hash(pdf_id) mod 3`)
2. **Dolphin VLM inference**: Batched processing (3 concurrent PDFs/worker)
3. **Post-processing**: Hyphenation merging, citation normalization
4. **S3 synchronization**: Idempotent uploads with checkpointing

**Output**: Structured Markdown documents with:
- Document hierarchy (sections, subsections)
- Inline citations `[@Aghion2015]`
- LaTeX equations
- Extracted figures
- Processing metadata (timestamps, status, errors)

**Performance**: 200-250 papers/day/worker, ~$0.08/paper processing cost

### Stage 2: Knowledge Representation

**Input**: Structured Markdown documents from Stage 1

**Chunking Strategy**:
1. Split at section boundaries (markdown `##` headers)
2. Recursively subdivide sections >800 tokens at subsection/paragraph boundaries
3. Preserve ±1 sentence around citations for context
4. Attach metadata (title, section, document ID)

**Embedding**:
- **Model**: OpenAI `text-embedding-3-small` (1536 dimensions)
- **Input format**: `title ⊕ section_name ⊕ chunk_text`
- **Corpus size**: 28,000 chunks across 999 processed papers

**Storage**: FAISS HNSW index (optimized for static corpus, batch processing)

### Stage 3: Hybrid Retrieval

**Input**: User query (natural language)

**Two-stage pipeline**:

**Step 1 - Dense Retrieval (FAISS)**:
- Embed query: `v_q = Embed(query)`
- Retrieve top-75 candidates via cosine similarity
- Latency: <50ms

**Step 2 - Cross-Encoder Reranking**:
- **Model**: ZeroEntropy `zerank-1`
- Jointly encode query-document pairs for fine-grained relevance
- Rerank to top-10 chunks
- Graceful degradation to FAISS-only on API failure

**Output**: Top-10 chunks with metadata (title, section, citations, document ID)

### Stage 4: Multi-Model LLM Generation

**Input**: Top-10 retrieved chunks + user query

**LLM Selection** (user-configurable):
- **Fast tier**: `gpt-5-mini`, `gemini-3-pro` ($0.12/query)
- **Balanced tier**: `claude-3.5-sonnet`, `deepseek-chat` ($0.25/query)
- **Premium tier**: `claude-sonnet-4.5`, `deepseek-r1` ($0.50+/query)

**Structured Prompt Enforces**:
1. **Executive Summary**: 2-3 sentence synthesis
2. **Detailed Analysis**: Evidence breakdown with quantitative details
3. **Policy Implications**: Actionable insights for policymakers
4. **Key References**: Direct citations with paper metadata

**Quality Controls**:
- Mandate "use ONLY provided sources" to reduce hallucinations
- Require evidence quality labels (strong/moderate/limited/mixed)
- Explicit limitation acknowledgment for geographic/methodological gaps

**Output**: Structured response with direct PDF access via citations

## Corpus and Bias Analysis

### Dataset Composition

- **Total papers**: 4,920 peer-reviewed (1990-2024)
- **Processed**: 999 papers (20.3%) - processing ongoing
- **Source**: OpenAlex API with keywords: "patent", "IP", "R&D tax incentives", "patent litigation", etc.
- **Metadata**: Authors, affiliations, venues, years, citation networks

### Identified Biases

| Dimension | Finding | Policy Implication |
|-----------|---------|-------------------|
| **Geography** | 78% from 5 countries (US 27.5%, UK 8.4%, China 7.1%) | Risk of US-centric policy transfer |
| **Language** | 96% English (4,399/4,897 papers) | Excludes non-Anglophone research traditions |
| **Methodology** | 64% quantitative, 11% qualitative | May underweight case studies, legal analyses |
| **Institutions** | 72.4% academic (vs practitioner) | May miss patent office, industry perspectives |
| **Temporality** | 48.6% post-2015, 16.9% pre-2005 | Good historical coverage, limited 2023-2024 |
| **Venues** | 1,624 unique sources (69% journals) | Reflects interdisciplinary fragmentation |

### Bias Propagation Mechanisms

1. **Geographic gap**: Queries about Vietnam vs US expected to retrieve 0-2 vs 3-5 papers (rating 2.0-3.0 vs 4.0-4.5)
2. **Methodological amplification**: Term-matching in retrieval further skews toward quantitative studies
3. **Temporal recency bias**: Post-2020 policy topics (AI patentability, open-source licensing) have low coverage

### Mitigation Strategies

- **Transparent disclosure**: System responses explicitly acknowledge when evidence is geographically/methodologically limited
- **Evidence quality labels**: Strong/moderate/limited/mixed classifications
- **Expert validation**: Alpha deployment with policymakers providing structured feedback
- **Future corpus expansion**: Target non-English sources, practitioner reports, recent publications

## Quick Start

### Installation

```bash
# Clone repository
git clone <repository-url>
cd project-2-rag

# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Optional: Install specific dependency groups
uv sync --extra api      # FastAPI backend
uv sync --extra worker   # PDF processing workers
uv sync --extra analysis # Jupyter notebooks, benchmarking
```

### Basic Usage

**1. Process a single PDF locally:**
```bash
uv run python scripts/dev/test_local_processing.py --pdf path/to/paper.pdf
```

**2. Run distributed worker (requires AWS credentials):**
```bash
# Set environment variables
export WORKER_ID=0
export TOTAL_WORKERS=3
export S3_INPUT_BUCKET=cs433-rag-project2
export S3_OUTPUT_BUCKET=cs433-rag-project2

# Run worker
uv run python scripts/operations/distributed_worker.py
```

**3. Check worker status:**
```bash
uv run python scripts/operations/check_worker_status.py
```

**4. Run the RAG API locally:**
```bash
# Start FastAPI backend
cd api
uv run uvicorn main:app --reload --port 8000

# In another terminal, start Next.js frontend
cd frontend
npm install
npm run dev
```

**5. Access the web interface:**
Open `http://localhost:3000` and start querying the knowledge base.

## Project Structure

```
project-2-rag/
├── README.md                          # This file
├── pyproject.toml                     # Python dependencies (uv)
├── docker-compose.yml                 # Local development setup
│
├── docs/                              # Documentation
│   ├── plans/                         # Design documents
│   │   ├── distributed-pdf-processing-design.md
│   │   └── rag-architecture-design.md
│   ├── checkpoint_2025-11-10.md       # Project checkpoint
│   └── deployment.md                  # AWS deployment instructions
│
├── rag_pipeline/                      # Core Python package
│   ├── pdf_parsing/                   # PDF processing (Dolphin VLM)
│   │   ├── core/                      # Core pipeline logic
│   │   ├── processors/                # Document processors
│   │   ├── model_wrapper/             # Dolphin model interface
│   │   └── utils/                     # PDF utilities
│   ├── rag/                           # RAG components
│   │   ├── chunking/                  # Structure-aware chunking
│   │   ├── embeddings/                # OpenAI embedding generation
│   │   ├── retrieval/                 # FAISS + cross-encoder
│   │   └── generation/                # Multi-model LLM inference
│   ├── benchmarking/                  # Evaluation framework
│   │   ├── chunking_evaluator.py     # Citation preservation metrics
│   │   ├── bias_analysis.py          # Corpus demographic analysis
│   │   └── visualizations.py         # Report generation
│   └── openalex/                      # OpenAlex API client
│       ├── client.py                  # Metadata fetching
│       └── schemas.py                 # Paper metadata models
│
├── scripts/                           # Operational scripts
│   ├── operations/                    # Production/deployment
│   │   ├── distributed_worker.py     # Main PDF processing worker
│   │   ├── check_worker_status.py    # Worker monitoring
│   │   ├── process_pdfs_batch.py     # Batch PDF processing
│   │   ├── batch_chunk_markdown.py   # Batch chunking
│   │   ├── chunk_all_documents.py    # Full corpus chunking
│   │   └── embed_and_index.py        # FAISS index creation
│   ├── benchmarking/                  # Evaluation scripts
│   │   ├── generate_chunking_report.py  # Chunking metrics
│   │   └── regenerate_plots.py       # Visualization updates
│   ├── dev/                           # Development/testing
│   │   ├── test_local_processing.py  # Local PDF testing
│   │   ├── test_markdown_chunking.py # Chunking validation
│   │   └── test_retriever.py         # Retrieval testing
│   ├── utils/                         # Shared utilities
│   │   ├── s3_utils.py               # S3 operations
│   │   ├── worker_distribution.py    # Work partitioning
│   │   └── markdown_s3_loader.py     # S3 markdown loading
│   └── README.md                      # Scripts documentation
│
├── api/                               # FastAPI backend service
│   ├── main.py                        # FastAPI application
│   ├── routers/                       # API endpoints
│   │   ├── search.py                 # /search endpoint
│   │   ├── chat.py                   # /chat endpoint
│   │   └── models.py                 # /models endpoint
│   ├── services/                      # Business logic
│   │   ├── retrieval_service.py      # Hybrid retrieval
│   │   └── llm_service.py            # Multi-model LLM
│   ├── models/                        # Pydantic schemas
│   └── Dockerfile                     # API container
│
├── frontend/                          # Next.js web interface
│   ├── app/                           # Next.js 16 App Router
│   │   ├── [locale]/                 # i18n routes
│   │   │   ├── page.tsx              # Main query interface
│   │   │   └── chat/                 # Chat interface
│   │   └── api/                      # API routes
│   ├── components/                    # React components
│   │   ├── QueryInput.tsx            # Search input
│   │   ├── ResponseDisplay.tsx       # Structured response
│   │   ├── ModelSelector.tsx         # LLM selection
│   │   └── CitationCard.tsx          # Citation display
│   ├── i18n/                          # Internationalization
│   │   ├── en.json                   # English translations
│   │   └── fr.json                   # French translations
│   └── middleware.ts                  # i18n routing
│
├── notebooks/                         # Jupyter notebooks
│   ├── corpus_analysis.ipynb         # Bias analysis
│   ├── chunking_evaluation.ipynb     # Chunking benchmarks
│   └── retrieval_testing.ipynb       # Retrieval experiments
│
└── reports/                           # Generated evaluation reports
    ├── chunking_evaluation_*.html     # Chunking metrics (gitignored)
    └── plots/                         # Visualizations (gitignored)
```

## Technology Stack

### Core Infrastructure
- **Python 3.10+**: Core language
- **uv**: Fast Python package manager
- **Docker**: Containerization
- **AWS S3**: Cloud storage
- **AWS EC2 (g5.xlarge)**: GPU compute (NVIDIA A10G, 24GB VRAM)

### PDF Processing
- **Dolphin VLM** (8B parameters): Vision-language model for PDF extraction
- **PyTorch**: Deep learning framework
- **Pillow**: Image processing
- **boto3**: AWS SDK for Python

### RAG Pipeline
- **OpenAI Embeddings** (`text-embedding-3-small`): 1536D vectors
- **FAISS** (HNSW): Dense vector retrieval
- **ZeroEntropy cross-encoder** (`zerank-1`): Reranking
- **LiteLLM**: Multi-provider LLM abstraction
- **OpenRouter**: Model aggregation (10+ models)

### API & Frontend
- **FastAPI**: Python async web framework
- **Next.js 16**: React framework with App Router
- **TypeScript**: Type-safe frontend
- **Tailwind CSS**: Styling
- **i18next**: Internationalization (English/French)

### Data & Analysis
- **OpenAlex API**: Academic metadata fetching
- **Pandas**: Data analysis
- **Matplotlib/Seaborn**: Visualization
- **Jupyter**: Interactive notebooks

## Performance Metrics

### PDF Processing
- **Throughput**: 200-250 papers/day/worker
- **GPU Utilization**: 87% average
- **Concurrent PDFs**: 3 per worker
- **Citation Preservation**: 23.4 avg/paper (vs 12.3-18.7 for text-only)
- **Processing Cost**: $0.08/paper

### Chunking
- **Chunk Size**: ~420 tokens (SD=180)
- **Citation Preservation**: 55.2%
- **Semantic Units**: 92% chunks contain complete semantic units

### Retrieval
- **FAISS Latency**: <50ms for top-75 retrieval
- **Total Corpus**: 28,000 chunks across 999 papers
- **Index Type**: HNSW (Hierarchical Navigable Small World)

### Generation
- **Query Cost**: $0.12 (Fast) to $0.50+ (Premium)
- **Latency**: 2-3 seconds end-to-end
- **Response Structure**: 4 sections (Summary, Analysis, Policy, References)
- **Hallucination Target**: <10% phantom citations, <15% fact fabrication

### Evaluation (Preliminary, N=20 queries)
- **Structure Compliance**: 95%
- **Citation Inclusion**: 100%
- **Quantitative Detail**: 70%
- **Completeness Target**: >3.5/5.0 expert rating

## Documentation

- **[docs/plans/distributed-pdf-processing-design.md](docs/plans/)**: Distributed worker architecture
- **[docs/plans/rag-architecture-design.md](docs/plans/)**: RAG pipeline design decisions
- **[scripts/README.md](scripts/README.md)**: Operational scripts documentation
- **[Research Report](../project-2-rag-report/main.pdf)**: Full academic paper with evaluation framework

## Current Status & Roadmap

### Completed ✅
- [x] OpenAlex API integration (4,920 papers)
- [x] Distributed PDF processing with Dolphin VLM
- [x] Structure-aware chunking with citation preservation
- [x] Hybrid retrieval (FAISS + cross-encoder)
- [x] Multi-model LLM infrastructure (10 models)
- [x] FastAPI backend with structured prompts
- [x] Next.js frontend with bilingual support
- [x] Corpus bias analysis (6 dimensions)
- [x] Chunking evaluation framework

### In Progress 🚧
- [ ] Full corpus processing (999/4,920 papers, 20.3%)
- [ ] Systematic evaluation (N=100 test queries)
- [ ] Hallucination rate measurement
- [ ] Expert validation (alpha deployment)

### Future Work 📋
- [ ] Real-time PDF upload and processing
- [ ] Migration to managed vector database (Pinecone/Weaviate)
- [ ] Citation graph visualization
- [ ] Multi-document synthesis
- [ ] Comparative policy analysis
- [ ] Non-English corpus expansion

## Cost Analysis

### Processing Costs
- **GPU Compute**: $0.79/hour (3x g5.xlarge Spot instances)
- **PDF Processing**: ~33 hours total, ~$26 for full corpus
- **S3 Storage**: ~$0.023/GB/month (4,920 PDFs + processed outputs)

### Query Costs
- **Fast tier**: $0.12/query (gpt-5-mini, gemini-3-pro)
- **Balanced tier**: $0.25/query (claude-3.5-sonnet, deepseek-chat)
- **Premium tier**: $0.50+/query (claude-sonnet-4.5, deepseek-r1)

### Total Budget
- **Initial processing**: ~$26 (one-time)
- **Storage**: ~$5/month
- **Query costs**: Variable ($0.12-$0.50/query)

Well within typical research project budgets.

## Contributors

- **Elie Bruno** - École Polytechnique Fédérale de Lausanne (EPFL)
- **Andrea Trugenberger** - EPFL
- **Youssef Chelaifa** - EPFL

## License

[MIT License / Your License]

## Citation

If you use this system in your research, please cite:

```bibtex
@article{bruno2025rag,
  title={Evidence-Based Policy Support Through RAG: A Critical Analysis of Bias and Reliability in AI-Assisted Patent Research},
  author={Bruno, Elie and Trugenberger, Andrea and Chelaifa, Youssef},
  year={2025},
  institution={École Polytechnique Fédérale de Lausanne (EPFL)}
}
```

---

**Last Updated**: December 17, 2025
