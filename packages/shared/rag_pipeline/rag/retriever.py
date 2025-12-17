"""
Hybrid retriever with FAISS + ZeroEntropy reranking.

Usage:
    from rag_pipeline.rag.retriever import HybridRetriever

    retriever = HybridRetriever.from_s3(
        bucket_name="cs433-rag-project2",
        openai_api_key=os.environ["OPENAI_API_KEY"],
        zeroentropy_api_key=os.environ["ZEROENTROPY_API_KEY"]
    )

    results = retriever.search("What are the effects of climate change?", top_k=10)
"""

import os
import json
import tempfile
from typing import List, Dict, Optional
from dataclasses import dataclass
import numpy as np
import requests
import faiss
import boto3

from rag_pipeline.rag.openai_embedder import OpenAIEmbedder


@dataclass
class SearchResult:
    """A single search result with metadata."""
    chunk_id: str
    paper_id: str
    paper_title: str
    text: str
    section_hierarchy: List[str]
    score: float
    rank: int


class FAISSRetriever:
    """FAISS-based vector similarity search."""

    def __init__(
        self,
        index: faiss.Index,
        metadata: Dict[str, Dict],
        embedder: OpenAIEmbedder
    ):
        """
        Initialize FAISS retriever.

        Args:
            index: FAISS index
            metadata: Dict mapping index position to chunk metadata
            embedder: OpenAI embedder for query encoding
        """
        self.index = index
        self.metadata = metadata
        self.embedder = embedder

    @classmethod
    def from_s3(
        cls,
        bucket_name: str,
        chunk_type: str,
        openai_api_key: str,
        index_prefix: str = "indexes/"
    ) -> "FAISSRetriever":
        """
        Load FAISS retriever from S3.

        Args:
            bucket_name: S3 bucket name
            chunk_type: "coarse" or "fine"
            openai_api_key: OpenAI API key
            index_prefix: S3 prefix for indexes
        """
        s3_client = boto3.client('s3')

        # Download index
        index_key = f"{index_prefix}{chunk_type}.faiss"
        with tempfile.NamedTemporaryFile(suffix='.faiss', delete=False) as f:
            index_path = f.name

        print(f"Downloading index from s3://{bucket_name}/{index_key}...")
        s3_client.download_file(bucket_name, index_key, index_path)
        index = faiss.read_index(index_path)
        os.unlink(index_path)

        # Download metadata
        metadata_key = f"{index_prefix}{chunk_type}_metadata.json"
        print(f"Downloading metadata from s3://{bucket_name}/{metadata_key}...")
        response = s3_client.get_object(Bucket=bucket_name, Key=metadata_key)
        metadata = json.loads(response['Body'].read().decode('utf-8'))

        # Initialize embedder
        embedder = OpenAIEmbedder(
            api_key=openai_api_key,
            model="text-embedding-3-small"
        )

        print(f"Loaded {chunk_type} index with {index.ntotal} vectors")
        return cls(index, metadata, embedder)

    def search(self, query: str, top_k: int = 50) -> List[SearchResult]:
        """
        Search for similar chunks.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of SearchResult objects
        """
        # Embed query
        query_embedding = self.embedder.generate_embedding(query)
        query_vector = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_vector)

        # Search
        distances, indices = self.index.search(query_vector, top_k)

        # Build results
        results = []
        for rank, (idx, score) in enumerate(zip(indices[0], distances[0])):
            if idx == -1:  # No more results
                break

            meta = self.metadata[str(idx)]
            results.append(SearchResult(
                chunk_id=meta["chunk_id"],
                paper_id=meta["paper_id"],
                paper_title=meta["paper_title"],
                text=meta["text"],
                section_hierarchy=meta["section_hierarchy"],
                score=float(score),
                rank=rank
            ))

        return results


class ZeroEntropyReranker:
    """ZeroEntropy reranking API client."""

    def __init__(self, api_key: str, base_url: str = "https://api.zeroentropy.dev/v1"):
        """
        Initialize ZeroEntropy reranker.

        Args:
            api_key: ZeroEntropy API key
            base_url: API base URL
        """
        self.api_key = api_key
        self.base_url = base_url

    def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int = 10
    ) -> List[SearchResult]:
        """
        Rerank search results using ZeroEntropy.

        Args:
            query: Original search query
            results: List of SearchResult to rerank
            top_k: Number of results to return after reranking

        Returns:
            Reranked list of SearchResult
        """
        if not results:
            return []

        # Prepare documents for reranking
        documents = [r.text for r in results]

        # Call ZeroEntropy API
        response = requests.post(
            f"{self.base_url}/models/rerank",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "zerank-1",  # ZeroEntropy reranking model (or "zerank-1-small" for faster)
                "query": query,
                "documents": documents,
                "top_n": min(top_k, len(documents))
            },
            timeout=30
        )

        if response.status_code != 200:
            print(f"ZeroEntropy rerank failed: {response.status_code} - {response.text}")
            # Fallback: return original results
            return results[:top_k]

        # Parse response
        reranked_data = response.json()

        # Build reranked results
        reranked_results = []
        for rank, item in enumerate(reranked_data.get("results", [])):
            original_idx = item["index"]
            original_result = results[original_idx]

            reranked_results.append(SearchResult(
                chunk_id=original_result.chunk_id,
                paper_id=original_result.paper_id,
                paper_title=original_result.paper_title,
                text=original_result.text,
                section_hierarchy=original_result.section_hierarchy,
                score=item.get("relevance_score", original_result.score),
                rank=rank
            ))

        return reranked_results


class HybridRetriever:
    """
    Hybrid retriever combining FAISS retrieval with ZeroEntropy reranking.

    Flow:
    1. FAISS retrieves top-N candidates (fast, embedding similarity)
    2. ZeroEntropy reranks to top-K (accurate, relevance scoring)
    """

    def __init__(
        self,
        faiss_retriever: FAISSRetriever,
        reranker: Optional[ZeroEntropyReranker] = None,
        faiss_candidates: int = 75
    ):
        """
        Initialize hybrid retriever.

        Args:
            faiss_retriever: FAISS retriever for initial search
            reranker: Optional ZeroEntropy reranker
            faiss_candidates: Number of candidates to retrieve from FAISS
        """
        self.faiss_retriever = faiss_retriever
        self.reranker = reranker
        self.faiss_candidates = faiss_candidates

    @classmethod
    def from_s3(
        cls,
        bucket_name: str,
        openai_api_key: str,
        zeroentropy_api_key: Optional[str] = None,
        chunk_type: str = "coarse",
        faiss_candidates: int = 75
    ) -> "HybridRetriever":
        """
        Load hybrid retriever from S3.

        Args:
            bucket_name: S3 bucket name
            openai_api_key: OpenAI API key
            zeroentropy_api_key: Optional ZeroEntropy API key
            chunk_type: "coarse" or "fine"
            faiss_candidates: Number of FAISS candidates
        """
        faiss_retriever = FAISSRetriever.from_s3(
            bucket_name=bucket_name,
            chunk_type=chunk_type,
            openai_api_key=openai_api_key
        )

        reranker = None
        if zeroentropy_api_key:
            reranker = ZeroEntropyReranker(api_key=zeroentropy_api_key)

        return cls(faiss_retriever, reranker, faiss_candidates)

    def search(
        self,
        query: str,
        top_k: int = 10,
        use_reranker: bool = True
    ) -> List[SearchResult]:
        """
        Search for relevant chunks.

        Args:
            query: Search query
            top_k: Number of final results
            use_reranker: Whether to use ZeroEntropy reranking

        Returns:
            List of SearchResult objects
        """
        # Step 1: FAISS retrieval
        candidates = self.faiss_retriever.search(query, self.faiss_candidates)

        # Step 2: Reranking (if available and enabled)
        if use_reranker and self.reranker:
            results = self.reranker.rerank(query, candidates, top_k)
        else:
            results = candidates[:top_k]

        return results

    def search_with_context(
        self,
        query: str,
        top_k: int = 10,
        context_window: int = 1
    ) -> List[Dict]:
        """
        Search and include surrounding chunks for context.

        Args:
            query: Search query
            top_k: Number of results
            context_window: Number of chunks before/after to include

        Returns:
            List of result dicts with context
        """
        results = self.search(query, top_k)

        # TODO: Implement context expansion by loading adjacent chunks
        # For now, return results as-is
        return [
            {
                "chunk_id": r.chunk_id,
                "paper_id": r.paper_id,
                "paper_title": r.paper_title,
                "text": r.text,
                "section_hierarchy": r.section_hierarchy,
                "score": r.score,
                "rank": r.rank
            }
            for r in results
        ]


# Convenience function for quick usage
def create_retriever(
    openai_api_key: Optional[str] = None,
    zeroentropy_api_key: Optional[str] = None,
    bucket_name: str = "cs433-rag-project2"
) -> HybridRetriever:
    """
    Create a hybrid retriever with default settings.

    Args:
        openai_api_key: OpenAI API key (defaults to env var)
        zeroentropy_api_key: ZeroEntropy API key (defaults to env var)
        bucket_name: S3 bucket name

    Returns:
        Configured HybridRetriever
    """
    openai_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
    zeroentropy_key = zeroentropy_api_key or os.environ.get("ZEROENTROPY_API_KEY")

    if not openai_key:
        raise ValueError("OPENAI_API_KEY not provided")

    return HybridRetriever.from_s3(
        bucket_name=bucket_name,
        openai_api_key=openai_key,
        zeroentropy_api_key=zeroentropy_key
    )
