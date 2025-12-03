"""
FastAPI backend for RAG search.

Run locally:
    uvicorn api.main:app --reload --port 8000

Run with Docker:
    docker-compose up
"""

import os
import time
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import retriever
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_pipeline.rag.retriever import DualIndexRetriever, ZeroEntropyReranker
from openai import OpenAI
from api.prompts import SYSTEM_PROMPT, RAG_PROMPT_TEMPLATE, format_sources_for_prompt


# ============================================================================
# Configuration
# ============================================================================

BUCKET_NAME = os.environ.get("S3_BUCKET", "cs433-rag-project2")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ZEROENTROPY_API_KEY = os.environ.get("ZEROENTROPY_API_KEY")
COARSE_CANDIDATES = int(os.environ.get("COARSE_CANDIDATES", "50"))
FINE_CANDIDATES = int(os.environ.get("FINE_CANDIDATES", "50"))


# ============================================================================
# Global state
# ============================================================================

retriever: Optional[DualIndexRetriever] = None
openai_client: Optional[OpenAI] = None


# ============================================================================
# Lifespan (load index on startup)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load both FAISS indexes on startup."""
    global retriever, openai_client

    print("=" * 60)
    print("Loading RAG retriever (dual-index mode)...")
    print("=" * 60)

    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY environment variable not set")

    # Initialize OpenAI client for chat completions
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

    start = time.time()

    # Load dual-index retriever (both coarse and fine)
    retriever = DualIndexRetriever.from_s3(
        bucket_name=BUCKET_NAME,
        openai_api_key=OPENAI_API_KEY,
        zeroentropy_api_key=ZEROENTROPY_API_KEY,
        coarse_candidates=COARSE_CANDIDATES,
        fine_candidates=FINE_CANDIDATES
    )

    elapsed = time.time() - start
    print(f"Retriever loaded in {elapsed:.1f}s")
    print(f"Coarse index: {retriever.coarse_index_size} vectors")
    print(f"Fine index: {retriever.fine_index_size} vectors")
    print(f"Total: {retriever.coarse_index_size + retriever.fine_index_size} vectors")
    if ZEROENTROPY_API_KEY:
        print("ZeroEntropy reranking: enabled")
    else:
        print("ZeroEntropy reranking: disabled")
    print("=" * 60)

    yield

    # Cleanup
    print("Shutting down...")


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="RAG Search API",
    description="Search academic papers using FAISS + ZeroEntropy reranking",
    version="1.0.0",
    lifespan=lifespan
)

# CORS - allow frontend to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, set to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    use_reranker: bool = True


class SearchResult(BaseModel):
    chunk_id: str
    paper_id: str
    paper_title: str
    text: str
    section_hierarchy: List[str]
    score: float
    rank: int


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int
    elapsed_ms: float


class HealthResponse(BaseModel):
    status: str
    index_loaded: bool
    coarse_index_size: int
    fine_index_size: int
    total_vectors: int


class ChatRequest(BaseModel):
    message: str
    top_k: int = 10
    use_reranker: bool = True
    model: str = "gpt-4o-mini"  # or "gpt-4o" for better quality


class Citation(BaseModel):
    id: str
    title: str
    authors: str
    year: str
    snippet: str


class ChatResponse(BaseModel):
    message: str
    answer: str
    sources_used: int
    citations: List[Citation]
    elapsed_ms: float


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/health", response_model=HealthResponse)
def health():
    """Health check endpoint."""
    coarse_size = retriever.coarse_index_size if retriever else 0
    fine_size = retriever.fine_index_size if retriever else 0
    return HealthResponse(
        status="ok",
        index_loaded=retriever is not None,
        coarse_index_size=coarse_size,
        fine_index_size=fine_size,
        total_vectors=coarse_size + fine_size
    )


@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    """
    Search for relevant document chunks.

    - **query**: Search query text
    - **top_k**: Number of results to return (default: 10)
    - **use_reranker**: Whether to use ZeroEntropy reranking (default: true)
    """
    if not retriever:
        raise HTTPException(status_code=503, detail="Retriever not loaded")

    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    start = time.time()

    # Search
    results = retriever.search(
        query=request.query,
        top_k=request.top_k,
        use_reranker=request.use_reranker
    )

    elapsed_ms = (time.time() - start) * 1000

    return SearchResponse(
        query=request.query,
        results=[
            SearchResult(
                chunk_id=r.chunk_id,
                paper_id=r.paper_id,
                paper_title=r.paper_title,
                text=r.text,
                section_hierarchy=r.section_hierarchy,
                score=r.score,
                rank=r.rank
            )
            for r in results
        ],
        total_results=len(results),
        elapsed_ms=round(elapsed_ms, 2)
    )


@app.get("/")
def root():
    """API root - redirect to docs."""
    return {
        "message": "RAG Search API",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/pdf/{paper_id}")
def get_pdf_url(paper_id: str):
    """
    Get a presigned URL to download/view the PDF for a paper.

    - **paper_id**: Paper ID (e.g., "02596_W1962380625")

    Returns a temporary URL valid for 1 hour.
    """
    import boto3
    from botocore.exceptions import ClientError

    s3_client = boto3.client('s3')

    # Try to find the PDF in raw_pdfs/
    # The filename pattern is: {index}_{work_id}_*.pdf
    # e.g., 02596_W1962380625_Some_Title.pdf

    try:
        # List objects with the paper_id prefix
        response = s3_client.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix=f"raw_pdfs/{paper_id}",
            MaxKeys=1
        )

        if 'Contents' not in response or len(response['Contents']) == 0:
            raise HTTPException(status_code=404, detail=f"PDF not found for paper {paper_id}")

        pdf_key = response['Contents'][0]['Key']

        # Generate presigned URL (valid for 1 hour)
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': pdf_key,
                'ResponseContentType': 'application/pdf'
            },
            ExpiresIn=3600  # 1 hour
        )

        return {
            "paper_id": paper_id,
            "pdf_url": presigned_url,
            "expires_in": 3600
        }

    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"S3 error: {str(e)}")


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    RAG Chat endpoint - retrieves relevant sources and generates a policy-focused answer.

    - **message**: User's policy question
    - **top_k**: Number of sources to retrieve (default: 10)
    - **use_reranker**: Whether to use ZeroEntropy reranking (default: true)
    - **model**: OpenAI model to use (default: gpt-4o-mini)
    """
    if not retriever:
        raise HTTPException(status_code=503, detail="Retriever not loaded")

    if not openai_client:
        raise HTTPException(status_code=503, detail="OpenAI client not initialized")

    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    start = time.time()

    # Step 1: Retrieve relevant sources
    search_results = retriever.search(
        query=request.message,
        top_k=request.top_k,
        use_reranker=request.use_reranker
    )

    if not search_results:
        return ChatResponse(
            message=request.message,
            answer="I couldn't find any relevant sources to answer your question. Please try rephrasing or ask a different question.",
            sources_used=0,
            citations=[],
            elapsed_ms=round((time.time() - start) * 1000, 2)
        )

    # Step 2: Format sources for the prompt
    sources_text = format_sources_for_prompt(search_results)

    # Step 3: Generate answer using LLM
    user_prompt = RAG_PROMPT_TEMPLATE.format(
        sources=sources_text,
        question=request.message
    )

    completion = openai_client.chat.completions.create(
        model=request.model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,  # Lower temperature for more factual responses
        max_tokens=2000
    )

    answer = completion.choices[0].message.content

    # Step 4: Build citations from unique papers
    seen_papers = set()
    citations = []
    for result in search_results:
        if result.paper_id not in seen_papers:
            seen_papers.add(result.paper_id)
            citations.append(Citation(
                id=result.paper_id,
                title=result.paper_title.split('\n')[0][:100],
                authors=result.paper_id,  # Could be enhanced with actual metadata
                year="",
                snippet=result.text[:150] + "..."
            ))

    elapsed_ms = (time.time() - start) * 1000

    return ChatResponse(
        message=request.message,
        answer=answer,
        sources_used=len(search_results),
        citations=citations,
        elapsed_ms=round(elapsed_ms, 2)
    )
