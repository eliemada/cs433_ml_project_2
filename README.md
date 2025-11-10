# RAG Pipeline for Academic Papers

A distributed GPU-accelerated system for processing academic PDFs into a searchable knowledge base using Dolphin vision-language model and retrieval-augmented generation.

## Overview

This project processes academic papers from PDFs into structured markdown documents with embedded figures, then enables semantic search and question answering through a RAG pipeline.

### Current Status

- **353 academic papers processed** (out of 4,920 available)
- **Distributed processing** with 3 GPU workers on AWS EC2
- **S3-based storage** for scalability
- **Ready for RAG pipeline integration** (chunking, embeddings, vector database)

## Architecture

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
    └─────────┘          └─────────┘          └─────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   Dolphin Model   │
                    │  Vision-Language  │
                    └───────────────────┘
```

## Features

- **PDF Processing**: Converts academic PDFs to structured markdown
- **Figure Extraction**: Automatically extracts and saves figures from papers
- **Layout Understanding**: Preserves document structure (sections, paragraphs, citations)
- **Distributed Processing**: Scales horizontally with multiple GPU workers
- **S3 Integration**: Efficient cloud storage for inputs and outputs
- **RAG-Ready**: Includes chunking and embedding utilities for RAG pipeline

## Quick Start

See [GUIDE.md](GUIDE.md) for detailed setup and usage instructions.

### Installation

```bash
# Clone repository
git clone <repository-url>
cd project-2-rag

# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

### Basic Usage

**Process a single PDF locally:**
```bash
uv run python scripts/test_local_processing.py --pdf path/to/paper.pdf
```

**Run distributed worker:**
```bash
# Set environment variables
export WORKER_ID=0
export TOTAL_WORKERS=3
export S3_INPUT_BUCKET=cs433-rag-project2
export S3_OUTPUT_BUCKET=cs433-rag-project2

# Run worker
uv run python scripts/distributed_worker.py
```

**Check worker status:**
```bash
uv run python scripts/check_worker_status.py
```

## Project Structure

```
project-2-rag/
├── README.md                    # This file
├── GUIDE.md                     # Detailed usage guide
├── docs/                        # Documentation
│   ├── checkpoint_2025-11-10.md # Project checkpoint
│   └── deployment.md            # Deployment instructions
├── rag_pipeline/
│   ├── pdf_parsing/             # PDF processing (Dolphin model)
│   ├── rag/                     # RAG utilities (chunking, embeddings)
│   └── openalex/                # OpenAlex metadata fetching
├── scripts/
│   ├── distributed_worker.py    # Main distributed processing script
│   ├── check_worker_status.py  # Monitor worker progress
│   └── test_local_processing.py # Test processing locally
└── tests/                       # Test suite
```

## Output Format

Each processed PDF generates:

```
processed/{PDF_ID}/
├── document.md                  # Structured markdown content
├── metadata.json                # Processing metadata
└── figures/                     # Extracted figures
    ├── figure_001.png
    ├── figure_002.png
    └── ...
```

## Technology Stack

- **Dolphin Model**: Vision-language model for document understanding
- **PyTorch**: Deep learning framework
- **AWS S3**: Cloud storage
- **OpenAI**: Embeddings generation (for RAG)
- **Python 3.10+**: Core language

## Performance

- **Processing Speed**: ~200-250 PDFs/day/worker
- **GPU Utilization**: 85-95%
- **Concurrent Processing**: 3 PDFs per worker
- **Total Workers**: 3 (scalable to more)

## Documentation

- **[GUIDE.md](GUIDE.md)**: Complete setup and usage guide
- **[docs/checkpoint_2025-11-10.md](docs/checkpoint_2025-11-10.md)**: Detailed project checkpoint
- **[docs/deployment.md](docs/deployment.md)**: Deployment instructions

## Roadmap

- [x] Phase 1: PDF Processing with Dolphin model
- [x] Phase 1: Distributed worker system
- [x] Phase 1: S3 infrastructure
- [ ] Phase 2: Text chunking pipeline
- [ ] Phase 3: Embedding generation
- [ ] Phase 4: Vector database integration
- [ ] Phase 5: RAG query system

## License

[Your License]

## Contributors

[Your Names]

---

**Last Updated**: November 10, 2025
