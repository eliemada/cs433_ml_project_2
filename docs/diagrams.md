# Report Diagrams (Mermaid)

## 1. System Architecture Diagram

```mermaid
flowchart TB
    subgraph INDEXING["<b>Indexing Pipeline</b>"]
        direction TB
        PDF["PDF Documents<br/>~1,000 papers"]
        DOLPHIN["Dolphin Parser<br/>(Vision Model)"]
        MD["Markdown<br/>+ Structure"]
        CHUNKER["Hybrid Chunker"]

        PDF --> DOLPHIN --> MD --> CHUNKER

        CHUNKER --> COARSE["Coarse Chunks<br/>~2000 chars<br/>(46,063)"]
        CHUNKER --> FINE["Fine Chunks<br/>~300 chars<br/>(186,460)"]

        COARSE --> EMB1["OpenAI<br/>Embedding"]
        FINE --> EMB2["OpenAI<br/>Embedding"]

        EMB1 --> FAISS_C["FAISS Index<br/>(Coarse)"]
        EMB2 --> FAISS_F["FAISS Index<br/>(Fine)"]
    end

    subgraph S3["<b>S3 Storage</b> (cs433-rag-project2)"]
        direction TB
        S3_PDF["<b>raw_pdfs/</b><br/>{paper_id}_{title}.pdf<br/>~1,000 files"]
        S3_META["<b>raw_metadata/</b><br/>{paper_id}.json<br/>OpenAlex metadata"]
        S3_PROC["<b>processed/</b><br/>{paper_id}/document.md<br/>{paper_id}/metadata.json"]
        S3_CHUNKS["<b>chunks/</b><br/>{paper_id}_coarse.json<br/>{paper_id}_fine.json"]
        S3_IDX["<b>indexes/</b><br/>coarse.faiss (270 MB)<br/>fine.faiss (1.1 GB)<br/>+ metadata JSONs"]
    end

    PDF --> S3_PDF
    MD --> S3_PROC
    COARSE --> S3_CHUNKS
    FINE --> S3_CHUNKS
    FAISS_C --> S3_IDX
    FAISS_F --> S3_IDX

    subgraph RETRIEVAL["<b>Retrieval Pipeline</b>"]
        direction TB
        QUERY["User Query"]
        Q_EMB["Query Embedding<br/>(text-embedding-3-small)"]

        QUERY --> Q_EMB

        Q_EMB --> SEARCH_C["FAISS Search<br/>Coarse (k=50)"]
        Q_EMB --> SEARCH_F["FAISS Search<br/>Fine (k=50)"]

        SEARCH_C --> MERGE["Merge &<br/>Deduplicate"]
        SEARCH_F --> MERGE

        MERGE --> RERANK["ZeroEntropy<br/>Reranker<br/>(zerank-1)"]

        RERANK --> TOP_K["Top 10<br/>Results"]

        TOP_K --> LLM["GPT-4o-mini<br/>Generation"]

        LLM --> RESPONSE["Structured Response<br/>+ Citations"]
    end

    S3_IDX -.->|"Load on startup"| SEARCH_C
    S3_IDX -.->|"Load on startup"| SEARCH_F
    S3_PDF -.->|"Presigned URL"| RESPONSE

    style INDEXING fill:#e8f4f8,stroke:#0d6efd
    style RETRIEVAL fill:#f8f4e8,stroke:#fd7e14
    style S3 fill:#f0fff0,stroke:#28a745
    style PDF fill:#fff,stroke:#333
    style RESPONSE fill:#d4edda,stroke:#28a745
```

---

## 3. Dual-Index Retrieval Flow

```mermaid
flowchart LR
    subgraph INPUT
        Q["Query:<br/>'patent strength<br/>and R&D'"]
    end

    subgraph EMBED["Embedding"]
        E["OpenAI<br/>text-embedding-3-small<br/>(1536 dims)"]
    end

    subgraph SEARCH["Parallel FAISS Search"]
        direction TB
        C["<b>Coarse Index</b><br/>46,063 vectors<br/>→ top 50"]
        F["<b>Fine Index</b><br/>186,460 vectors<br/>→ top 50"]
    end

    subgraph MERGE["Merge & Dedupe"]
        direction TB
        M1["Coarse results<br/>(priority)"]
        M2["+ Non-overlapping<br/>fine results"]
        M3["≈ 60-80 unique<br/>candidates"]
        M1 --> M3
        M2 --> M3
    end

    subgraph RERANK["Neural Reranking"]
        R["ZeroEntropy<br/>zerank-1<br/>→ top 10"]
    end

    subgraph OUTPUT
        O["Final Results<br/>Mixed coarse/fine<br/>Best relevance"]
    end

    Q --> E
    E --> C
    E --> F
    C --> M1
    F --> M2
    M3 --> R
    R --> O

    style Q fill:#e3f2fd,stroke:#1976d2
    style O fill:#e8f5e9,stroke:#388e3c
    style C fill:#fff3e0,stroke:#f57c00
    style F fill:#fce4ec,stroke:#c2185b
```

---

## Alternative: Vertical Retrieval Flow

```mermaid
flowchart TB
    Q["User Query"] --> EMB["Embed Query<br/>(100ms)"]

    EMB --> DUAL["Dual-Index Search<br/>(50ms)"]

    subgraph DUAL_DETAIL[" "]
        direction LR
        COARSE["Coarse<br/>50 results"]
        FINE["Fine<br/>50 results"]
    end

    DUAL --> COARSE
    DUAL --> FINE

    COARSE --> MERGE["Merge & Dedupe<br/>(5ms)"]
    FINE --> MERGE

    MERGE --> RERANK["ZeroEntropy Rerank<br/>(400ms)"]

    RERANK --> TOP["Top 10 Chunks"]

    TOP --> LLM["GPT-4o-mini<br/>(2-3s)"]

    LLM --> RESP["Structured Response<br/>+ Citations"]

    style Q fill:#bbdefb
    style RESP fill:#c8e6c9
    style COARSE fill:#ffe0b2
    style FINE fill:#f8bbd9
```

---

## Chunking Strategy Visualization

```mermaid
flowchart TB
    subgraph ORIGINAL["Original Document Section"]
        DOC["<b>Section: Patent Quality</b><br/><br/>Patent quality refers to the probability...<br/>(paragraph 1 - 800 chars)<br/><br/>The examination process has been...<br/>(paragraph 2 - 600 chars)<br/><br/>Recent reforms attempt to address...<br/>(paragraph 3 - 500 chars)"]
    end

    subgraph COARSE["Coarse Chunking (~2000 chars)"]
        C1["<b>Chunk 1</b><br/>All 3 paragraphs together<br/>(1900 chars)<br/><br/>✓ Full context<br/>✓ Better for LLM understanding"]
    end

    subgraph FINE["Fine Chunking (~300 chars)"]
        F1["<b>Chunk 1</b><br/>First part of para 1<br/>(300 chars)"]
        F2["<b>Chunk 2</b><br/>Second part of para 1<br/>(300 chars)"]
        F3["<b>Chunk 3</b><br/>Paragraph 2<br/>(300 chars)"]
        F4["<b>Chunk 4</b><br/>...<br/>(300 chars)"]
    end

    DOC --> C1
    DOC --> F1
    DOC --> F2
    DOC --> F3
    DOC --> F4

    style ORIGINAL fill:#f5f5f5
    style COARSE fill:#e3f2fd
    style FINE fill:#fce4ec
```

---

## How to Use

### Option 1: Mermaid Live Editor
1. Go to https://mermaid.live
2. Paste the code
3. Export as SVG/PNG

### Option 2: VS Code
1. Install "Markdown Preview Mermaid Support" extension
2. Open this file and preview

### Option 3: GitHub
- GitHub renders Mermaid in markdown automatically

### Option 4: Export for Report
1. Use Mermaid CLI: `npx @mermaid-js/mermaid-cli mmdc -i diagrams.md -o output.png`
2. Or screenshot from mermaid.live

