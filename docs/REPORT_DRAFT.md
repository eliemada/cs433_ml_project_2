# RAG Pipeline for Academic Policy Research
## CS433 Machine Learning Project 2 - Report Draft

---

# Main Report (4 pages)

---

## 1. Introduction (0.5 page)

### 1.1 Problem Statement
Policymakers and researchers need to synthesize insights from large collections of academic literature on intellectual property, innovation, and economic policy. Traditional keyword search returns documents but doesn't provide synthesized, evidence-based answers.

### 1.2 Objectives
- Build an end-to-end Retrieval-Augmented Generation (RAG) system
- Process ~1,000 academic papers into searchable chunks
- Provide structured, citation-backed responses to policy questions
- Enable direct access to source PDFs

### 1.3 Contributions
1. **Hybrid chunking strategy** combining coarse (~2000 char) and fine (~300 char) chunks
2. **Dual-index retrieval** searching both chunk types simultaneously
3. **Two-stage retrieval** with FAISS + neural reranking
4. **Policy-focused generation** with structured output format

---

## 2. System Architecture (0.75 page)

### 2.1 Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INDEXING PIPELINE                            │
├─────────────────────────────────────────────────────────────────────┤
│  PDF → Dolphin Parser → Markdown → Hybrid Chunker → OpenAI Embed   │
│                                          │                          │
│                              ┌───────────┴───────────┐              │
│                              ▼                       ▼              │
│                      Coarse Index            Fine Index             │
│                      (46,063 vec)           (186,460 vec)           │
│                              │                       │              │
│                              └───────────┬───────────┘              │
│                                          ▼                          │
│                                    FAISS on S3                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        RETRIEVAL PIPELINE                           │
├─────────────────────────────────────────────────────────────────────┤
│  User Query                                                         │
│      │                                                              │
│      ▼                                                              │
│  OpenAI Embedding (text-embedding-3-small)                          │
│      │                                                              │
│      ├──────────────────┬──────────────────┐                        │
│      ▼                  ▼                  │                        │
│  FAISS Coarse      FAISS Fine              │                        │
│  (top 50)          (top 50)                │                        │
│      │                  │                  │                        │
│      └────────┬─────────┘                  │                        │
│               ▼                            │                        │
│      Merge & Deduplicate                   │                        │
│               │                            │                        │
│               ▼                            │                        │
│      ZeroEntropy Reranker (zerank-1)       │                        │
│               │                            │                        │
│               ▼                            │                        │
│         Top 10 Results                     │                        │
│               │                            │                        │
│               ▼                            │                        │
│      GPT-4o-mini Generation                │                        │
│               │                            │                        │
│               ▼                            │                        │
│      Structured Response + Citations       │                        │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Summary

| Component | Technology | Purpose |
|-----------|------------|---------|
| PDF Parsing | Dolphin (vision model) | Layout-aware extraction to Markdown |
| Chunking | Custom semantic chunker | Preserve document structure |
| Embeddings | OpenAI text-embedding-3-small | 1536-dim dense vectors |
| Vector Store | FAISS IndexFlatIP | Cosine similarity search |
| Reranking | ZeroEntropy zerank-1 | Neural relevance scoring |
| Generation | GPT-4o-mini | Policy-focused synthesis |
| Backend | FastAPI | REST API |
| Frontend | Next.js | Chat interface |

---

## 3. Methodology (1.5 pages)

### 3.1 Document Processing

**PDF Parsing**: We use the Dolphin vision-language model to extract text from academic PDFs while preserving document structure (headings, tables, figures). Output is clean Markdown with section hierarchy.

**Hybrid Chunking Strategy**:

| Chunk Type | Target Size | Purpose | Count |
|------------|-------------|---------|-------|
| Coarse | ~2000 chars | Rich context for LLM | 46,063 |
| Fine | ~300 chars | Precise fact matching | 186,460 |

Chunks are created at semantic boundaries (section breaks, paragraph ends) rather than fixed character counts. Each chunk retains metadata:
- `paper_id`: Unique document identifier
- `section_hierarchy`: Path from document root (e.g., ["Introduction", "Background"])
- `chunk_id`: Unique identifier with type prefix (`coarse_` or `fine_`)

### 3.2 Embedding & Indexing

We embed all chunks using OpenAI's `text-embedding-3-small` model (1536 dimensions). This model offers a good balance of quality and cost for academic text.

Vectors are stored in two FAISS `IndexFlatIP` indexes (one per chunk type) and hosted on S3 for serverless deployment. We use inner product with L2-normalized vectors, equivalent to cosine similarity.

### 3.3 Dual-Index Retrieval

Unlike single-index approaches, our system searches **both** indexes simultaneously:

1. **Parallel Search**: Query both coarse (k=50) and fine (k=50) indexes
2. **Merge & Deduplicate**: Combine results, removing fine chunks that overlap with coarse chunks from the same paper (coarse chunks provide more context)
3. **Neural Reranking**: ZeroEntropy's `zerank-1` model scores all candidates by semantic relevance
4. **Top-K Selection**: Return the 10 highest-scoring chunks

This approach captures both:
- **Broad context** from coarse chunks (better for understanding)
- **Precise facts** from fine chunks (better for specific claims)

### 3.4 LLM Generation

Retrieved chunks are formatted into a structured prompt for GPT-4o-mini:

```
You are a policy research assistant analyzing academic literature...

## Sources
[1] Title: {paper_title}
Section: {section_hierarchy}
Content: {chunk_text}

[2] ...

## Question
{user_question}

Provide a structured response with:
- Executive Summary (3-5 bullet points)
- Detailed Analysis (with subsections)
- Always cite sources as [1], [2], etc.
```

The model is instructed to:
- Synthesize across multiple sources
- Distinguish consensus from debate
- Acknowledge limitations and evidence gaps
- Use numbered citations matching source order

---

## 4. Results & Evaluation (0.75 page)

### 4.1 System Statistics

| Metric | Value |
|--------|-------|
| Documents processed | ~1,000 papers |
| Total vectors | 232,523 |
| Coarse chunks | 46,063 |
| Fine chunks | 186,460 |
| Avg. coarse chunk size | ~1,800 chars |
| Avg. fine chunk size | ~280 chars |

### 4.2 Latency Breakdown

| Stage | Time |
|-------|------|
| Query embedding | ~100ms |
| Dual FAISS search | ~50ms |
| Merge & dedupe | ~5ms |
| ZeroEntropy rerank | ~400ms |
| LLM generation | ~2-3s |
| **Total (end-to-end)** | **~3-4s** |

### 4.3 Qualitative Evaluation

**Example Query**: *"What is the relationship between patent strength and R&D investment?"*

**System Response** (summarized):
- Executive summary with 4 key findings across sources
- Detailed analysis covering theoretical frameworks and empirical evidence
- 5 citations from relevant papers with direct quotes

**Observations**:
- Responses successfully synthesize multiple sources
- Citations accurately match source content
- Structure makes responses scannable for busy policymakers

### 4.4 Limitations

1. **No quantitative benchmark**: We lack ground-truth Q&A pairs for this corpus
2. **Embedding model**: General-purpose embeddings may miss domain-specific terminology
3. **Reranker latency**: Adds ~400ms per query
4. **No conversation memory**: Each query is independent (follow-ups not supported)

---

## 5. Conclusion (0.5 page)

### 5.1 Summary

We built a complete RAG system for policy research that:
- Processes academic PDFs into structured, searchable chunks
- Uses dual-index retrieval (coarse + fine) for balanced context and precision
- Applies neural reranking for improved relevance
- Generates structured, citation-backed responses

### 5.2 Future Work

1. **Domain-adapted embeddings**: Fine-tune on policy/economics corpus
2. **Conversation memory**: Support follow-up questions with context
3. **Evaluation benchmark**: Create Q&A pairs for quantitative metrics
4. **Streaming responses**: Reduce perceived latency
5. **User feedback loop**: Collect relevance judgments to improve retrieval

---

# Appendix

---

## A. Technical Implementation Details

### A.1 Chunking Algorithm

```python
def create_hybrid_chunks(markdown: str, paper_id: str):
    """
    Create both coarse and fine chunks from markdown.

    Coarse: ~2000 chars, split at section boundaries
    Fine: ~300 chars, split at paragraph boundaries
    """
    sections = split_by_headers(markdown)

    coarse_chunks = []
    fine_chunks = []

    for section in sections:
        # Coarse: keep sections together (up to 2000 chars)
        if len(section.text) <= 2000:
            coarse_chunks.append(section)
        else:
            # Split large sections
            coarse_chunks.extend(split_at_paragraphs(section, max_size=2000))

        # Fine: split into smaller pieces
        fine_chunks.extend(split_at_paragraphs(section, max_size=300))

    return coarse_chunks, fine_chunks
```

### A.2 Merge & Deduplicate Logic

```python
def merge_results(coarse_results, fine_results):
    """
    Merge results from both indexes, deduplicating overlaps.
    Prioritize coarse chunks (more context).
    """
    merged = []
    seen_fingerprints = set()

    # Add coarse first (they have more context)
    for result in coarse_results:
        fingerprint = result.text[:100].lower()
        if fingerprint not in seen_fingerprints:
            seen_fingerprints.add(fingerprint)
            merged.append(result)

    # Add non-overlapping fine chunks
    for result in fine_results:
        fingerprint = result.text[:100].lower()
        is_substring = any(
            result.text[:100].lower() in existing.text.lower()
            for existing in merged
            if existing.paper_id == result.paper_id
        )
        if fingerprint not in seen_fingerprints and not is_substring:
            seen_fingerprints.add(fingerprint)
            merged.append(result)

    return merged
```

### A.3 System Prompt for Generation

```
You are a senior policy research assistant specializing in intellectual
property, innovation economics, and technology policy. Your role is to
analyze academic sources and provide evidence-based insights.

Response Structure:
## Executive Summary
- 3-5 bullet points capturing key findings

## Detailed Analysis
- Organized subsections addressing different aspects
- Always cite sources as [1], [2], etc.

## Key References
- List the most relevant sources used

Guidelines:
- Distinguish between consensus findings and ongoing debates
- Note limitations and evidence gaps
- Be specific about what sources actually say vs. inference
```

---

## B. API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System status, index sizes |
| `/search` | POST | Search without LLM generation |
| `/chat` | POST | Full RAG pipeline with generation |
| `/pdf/{paper_id}` | GET | Presigned URL for PDF download |

### B.1 Example Request/Response

**Request**:
```json
POST /chat
{
  "message": "How do patents affect innovation?",
  "top_k": 10,
  "use_reranker": true,
  "model": "gpt-4o-mini"
}
```

**Response**:
```json
{
  "message": "How do patents affect innovation?",
  "answer": "## Executive Summary\n- Patents provide incentives...",
  "sources_used": 10,
  "citations": [
    {
      "id": "00275_W2234817904",
      "title": "Prospects for Improving U.S. Patent Quality...",
      "snippet": "Patent quality refers to..."
    }
  ],
  "elapsed_ms": 3420.5
}
```

---

## C. Frontend Screenshots

[Include screenshots of:]
1. Empty state with welcome message
2. User query being typed
3. Response with executive summary expanded
4. Citation modal showing source excerpt
5. PDF viewer (via presigned URL)

---

## D. Dataset Statistics

| Statistic | Value |
|-----------|-------|
| Total papers | ~1,000 |
| Average paper length | ~15 pages |
| Total pages processed | ~15,000 |
| Topics covered | IP, patents, innovation, R&D, technology policy |
| Source | OpenAlex academic database |

---

## E. Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| PDF Parsing | Dolphin Vision Model | - |
| Embeddings | OpenAI text-embedding-3-small | - |
| Vector Store | FAISS | 1.7.4 |
| Reranking | ZeroEntropy zerank-1 | API |
| LLM | OpenAI GPT-4o-mini | - |
| Backend | FastAPI + Python | 3.11 |
| Frontend | Next.js + TypeScript | 14 |
| Styling | Tailwind CSS | 3.4 |
| Storage | AWS S3 | - |
| Deployment | Docker | - |

---

## F. Cost Analysis

| Component | Cost per 1M tokens/requests |
|-----------|----------------------------|
| Embeddings (text-embedding-3-small) | $0.02 / 1M tokens |
| Reranking (ZeroEntropy) | ~$0.10 / 1K requests |
| Generation (GPT-4o-mini) | $0.15 input, $0.60 output / 1M tokens |
| S3 Storage | ~$0.023 / GB-month |

**Estimated cost per query**: ~$0.002-0.005 (excluding infrastructure)

---

# Page Budget Guide

| Section | Suggested Length |
|---------|------------------|
| 1. Introduction | 0.5 page |
| 2. System Architecture | 0.75 page |
| 3. Methodology | 1.5 pages |
| 4. Results & Evaluation | 0.75 page |
| 5. Conclusion | 0.5 page |
| **Total** | **4 pages** |
| Appendix | As needed (not counted) |

---

# Figures to Create

1. **System Architecture Diagram** (Section 2) - Use the ASCII art as reference
2. **Chunking Example** (Section 3) - Show same text as coarse vs fine chunks
3. **Retrieval Flow** (Section 3) - Visual of dual-index merge
4. **Frontend Screenshot** (Section 4) - Show a real query/response
5. **Latency Breakdown Chart** (Section 4) - Stacked bar chart

