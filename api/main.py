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

from rag_pipeline.rag.retriever import HybridRetriever, FAISSRetriever, ZeroEntropyReranker
from openai import OpenAI
from litellm import completion
from api.prompts import SYSTEM_PROMPT, RAG_PROMPT_TEMPLATE, format_sources_for_prompt
from api.config import AVAILABLE_MODELS, DEFAULT_MODEL
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

BUCKET_NAME = os.environ.get("S3_BUCKET", "cs433-rag-project2")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_SITE_URL = os.environ.get("OPENROUTER_SITE_URL", "")
OPENROUTER_APP_NAME = os.environ.get("OPENROUTER_APP_NAME", "RAG Research Assistant")
ZEROENTROPY_API_KEY = os.environ.get("ZEROENTROPY_API_KEY")
CHUNK_TYPE = os.environ.get("CHUNK_TYPE", "coarse")  # "coarse" or "fine"
FAISS_CANDIDATES = int(os.environ.get("FAISS_CANDIDATES", "75"))


# ============================================================================
# Global state
# ============================================================================

retriever: Optional[HybridRetriever] = None
openai_client: Optional[OpenAI] = None


# ============================================================================
# Lifespan (load index on startup)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load FAISS index on startup."""
    global retriever, openai_client

    print("=" * 60)
    print("Loading RAG retriever...")
    print("=" * 60)

    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY environment variable not set")

    # Initialize OpenAI client for chat completions
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

    start = time.time()

    # Load FAISS retriever
    faiss_retriever = FAISSRetriever.from_s3(
        bucket_name=BUCKET_NAME,
        chunk_type=CHUNK_TYPE,
        openai_api_key=OPENAI_API_KEY
    )

    # Setup reranker if available
    reranker = None
    if ZEROENTROPY_API_KEY:
        print("ZeroEntropy API key found - reranking enabled")
        reranker = ZeroEntropyReranker(api_key=ZEROENTROPY_API_KEY)
    else:
        print("No ZeroEntropy API key - using FAISS-only retrieval")

    retriever = HybridRetriever(
        faiss_retriever=faiss_retriever,
        reranker=reranker,
        faiss_candidates=FAISS_CANDIDATES
    )

    elapsed = time.time() - start
    print(f"Retriever loaded in {elapsed:.1f}s")
    print(f"Index: {faiss_retriever.index.ntotal} vectors ({CHUNK_TYPE})")
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
    index_size: int
    chunk_type: str


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
    return HealthResponse(
        status="ok",
        index_loaded=retriever is not None,
        index_size=retriever.faiss_retriever.index.ntotal if retriever else 0,
        chunk_type=CHUNK_TYPE
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


@app.get("/models")
def get_available_models():
    """
    Get list of available LLM models for chat.

    Returns model configurations including name, provider, tier, and description.
    """
    return {
        "models": [
            {
                "id": model_id,
                "name": info["name"],
                "provider": info["provider"],
                "tier": info["tier"],
                "context": info["context"],
                "description": info["description"]
            }
            for model_id, info in AVAILABLE_MODELS.items()
        ],
        "default": DEFAULT_MODEL
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

    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=503, detail="OpenRouter API key not configured")

    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Validate model selection
    if request.model not in AVAILABLE_MODELS:
        raise HTTPException(status_code=400, detail=f"Invalid model: {request.model}. Use /models endpoint to see available models.")

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

    # GPT-5 models require temperature=1, others can use 0.3
    temperature = 1.0 if "gpt-5" in request.model else 0.3

    try:
        completion_response = completion(
            model=request.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            api_base="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
            temperature=temperature,
            max_tokens=2000,
            extra_headers={
                "HTTP-Referer": OPENROUTER_SITE_URL,
                "X-Title": OPENROUTER_APP_NAME
            }
        )

        answer = completion_response.choices[0].message.content

    except Exception as e:
        logger.error(f"LLM completion failed for {request.model}: {e}")

        # Fallback to default model if requested model fails
        if request.model != DEFAULT_MODEL:
            try:
                logger.info(f"Attempting fallback to {DEFAULT_MODEL}")
                fallback_temperature = 1.0 if "gpt-5" in DEFAULT_MODEL else 0.3
                completion_response = completion(
                    model=DEFAULT_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    api_base="https://openrouter.ai/api/v1",
                    api_key=OPENROUTER_API_KEY,
                    temperature=fallback_temperature,
                    max_tokens=2000
                )
                answer = f"[Using fallback model {DEFAULT_MODEL}]\n\n{completion_response.choices[0].message.content}"
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                raise HTTPException(status_code=503, detail="All LLM providers unavailable")
        else:
            raise HTTPException(status_code=503, detail=f"LLM error: {str(e)}")

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
