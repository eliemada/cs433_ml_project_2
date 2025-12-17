"""
Evaluation metrics for chunking strategies.

This module provides various metrics to evaluate the quality of text chunking
strategies for RAG systems, including semantic coherence, boundary quality,
citation integrity, and statistical measures.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import re
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)


@dataclass
class ChunkMetrics:
    """Comprehensive metrics for a chunking strategy."""

    strategy_name: str
    total_chunks: int
    mean_size_chars: float
    median_size_chars: float
    std_size_chars: float
    min_size_chars: int
    max_size_chars: int
    mean_size_tokens: float
    median_size_tokens: float
    coherence_score: Optional[float] = None
    boundary_quality: Optional[float] = None
    citation_coverage: Optional[float] = None
    total_citations: Optional[int] = None
    chunks_with_citations: Optional[int] = None

    def to_dict(self) -> Dict:
        """Convert metrics to dictionary for JSON serialization."""
        return {
            "strategy_name": self.strategy_name,
            "total_chunks": self.total_chunks,
            "mean_size_chars": round(self.mean_size_chars, 1),
            "median_size_chars": round(self.median_size_chars, 1),
            "std_size_chars": round(self.std_size_chars, 1),
            "min_size_chars": self.min_size_chars,
            "max_size_chars": self.max_size_chars,
            "mean_size_tokens": round(self.mean_size_tokens, 1),
            "median_size_tokens": round(self.median_size_tokens, 1),
            "coherence_score": round(self.coherence_score, 3) if self.coherence_score else None,
            "boundary_quality": (
                round(self.boundary_quality, 3) if self.boundary_quality else None
            ),
            "citation_coverage": (
                round(self.citation_coverage, 3) if self.citation_coverage else None
            ),
            "total_citations": self.total_citations,
            "chunks_with_citations": self.chunks_with_citations,
        }


def calculate_chunk_statistics(
    chunks: List, tokenizer_encode_fn: Optional[callable] = None
) -> Dict[str, float]:
    """
    Calculate statistical metrics for a list of chunks.

    Args:
        chunks: List of chunk objects with 'text' attribute
        tokenizer_encode_fn: Optional function to encode text to tokens

    Returns:
        Dictionary containing statistical measures
    """
    if not chunks:
        return {
            "count": 0,
            "mean_chars": 0,
            "median_chars": 0,
            "std_chars": 0,
            "min_chars": 0,
            "max_chars": 0,
            "mean_tokens": 0,
            "median_tokens": 0,
        }

    char_lengths = [len(chunk.text) for chunk in chunks]

    # Calculate token lengths if tokenizer provided
    if tokenizer_encode_fn:
        token_lengths = [len(tokenizer_encode_fn(chunk.text)) for chunk in chunks]
    else:
        # Approximate token count (1 token ≈ 4 characters)
        token_lengths = [len(chunk.text) // 4 for chunk in chunks]

    return {
        "count": len(chunks),
        "mean_chars": float(np.mean(char_lengths)),
        "median_chars": float(np.median(char_lengths)),
        "std_chars": float(np.std(char_lengths)),
        "min_chars": int(np.min(char_lengths)),
        "max_chars": int(np.max(char_lengths)),
        "mean_tokens": float(np.mean(token_lengths)),
        "median_tokens": float(np.median(token_lengths)),
    }


def calculate_coherence_score(
    chunk_text: str, embedding_fn: callable, min_sentences: int = 2
) -> float:
    """
    Calculate semantic coherence within a chunk using embeddings.

    Coherence is measured as the average cosine similarity between
    sentence embeddings within the chunk. Higher scores indicate
    more semantically cohesive chunks.

    Args:
        chunk_text: Text content of the chunk
        embedding_fn: Function that takes List[str] and returns numpy array of embeddings
        min_sentences: Minimum number of sentences required

    Returns:
        Coherence score (0-1), or 1.0 if fewer than min_sentences
    """
    # Split into sentences
    sentences = re.split(r"[.!?]+\s+", chunk_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

    if len(sentences) < min_sentences:
        return 1.0  # Perfect coherence for single/few sentences

    try:
        # Get embeddings
        embeddings = embedding_fn(sentences)

        # Calculate pairwise similarities
        similarities = cosine_similarity(embeddings)

        # Average similarity (excluding diagonal)
        mask = ~np.eye(similarities.shape[0], dtype=bool)
        avg_similarity = float(similarities[mask].mean())

        return avg_similarity

    except Exception as e:
        logger.warning(f"Error calculating coherence: {e}")
        return 0.0


def calculate_boundary_quality(
    chunks: List, embedding_fn: callable, num_samples: int = 10
) -> List[float]:
    """
    Evaluate chunk boundary quality by measuring semantic discontinuity.

    Compares the last sentence of one chunk with the first sentence of
    the next chunk. Lower similarity indicates cleaner semantic boundaries.

    Args:
        chunks: List of chunk objects with 'text' attribute
        embedding_fn: Function that takes List[str] and returns numpy array
        num_samples: Number of random chunk pairs to sample

    Returns:
        List of boundary similarity scores (lower is better)
    """
    if len(chunks) < 2:
        return []

    boundary_scores = []
    sample_size = min(num_samples, len(chunks) - 1)

    for _ in range(sample_size):
        try:
            # Random consecutive pair
            idx = np.random.randint(0, len(chunks) - 1)
            chunk1 = chunks[idx]
            chunk2 = chunks[idx + 1]

            # Extract boundary sentences
            sentences1 = re.split(r"[.!?]+\s+", chunk1.text)
            sentences2 = re.split(r"[.!?]+\s+", chunk2.text)

            if not sentences1 or not sentences2:
                continue

            last_sent = sentences1[-1].strip()
            first_sent = sentences2[0].strip()

            if len(last_sent) < 20 or len(first_sent) < 20:
                continue

            # Get embeddings and calculate similarity
            embeddings = embedding_fn([last_sent, first_sent])
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            boundary_scores.append(float(similarity))

        except Exception as e:
            logger.warning(f"Error calculating boundary quality: {e}")
            continue

    return boundary_scores


def count_citations(text: str) -> int:
    """
    Count citation markers in text.

    Supports various citation formats:
    - LaTeX footnotes: $^{53}$
    - Bracket citations: [1]
    - Parenthesis citations: (1)

    Args:
        text: Text to search for citations

    Returns:
        Total number of citations found
    """
    patterns = [
        r"\$\^\{\d+\}\$",  # LaTeX footnotes: $^{53}$
        r"\[\d+\]",  # Bracket citations: [1]
        r"\(\d+\)",  # Parentheses citations: (1)
    ]

    total = 0
    for pattern in patterns:
        matches = re.findall(pattern, text)
        total += len(matches)

    return total


def evaluate_citation_integrity(chunks: List) -> Dict[str, any]:
    """
    Evaluate how well citations are preserved within chunks.

    Higher citation coverage indicates better preservation of
    reference context, which is critical for academic RAG systems.

    Args:
        chunks: List of chunk objects with 'text' attribute

    Returns:
        Dictionary with citation statistics
    """
    total_citations = 0
    chunks_with_citations = 0
    citation_densities = []  # Citations per 1000 characters

    for chunk in chunks:
        n_citations = count_citations(chunk.text)
        total_citations += n_citations

        if n_citations > 0:
            chunks_with_citations += 1
            density = (n_citations / len(chunk.text)) * 1000
            citation_densities.append(density)

    citation_coverage = (chunks_with_citations / len(chunks)) if chunks else 0.0

    return {
        "total_citations": total_citations,
        "chunks_with_citations": chunks_with_citations,
        "citation_coverage": citation_coverage,
        "mean_citation_density": float(np.mean(citation_densities))
        if citation_densities
        else 0.0,
        "total_chunks": len(chunks),
    }


def calculate_overlap_efficiency(chunks: List) -> Dict[str, float]:
    """
    Measure how efficiently overlap is used (future enhancement).

    Args:
        chunks: List of chunk objects

    Returns:
        Dictionary with overlap metrics
    """
    # Placeholder for future implementation
    # Could measure: redundancy vs. information gain in overlaps
    return {"overlap_efficiency": 0.0}


def normalize_score(
    score: float, min_val: float, max_val: float, invert: bool = False
) -> float:
    """
    Normalize a score to 0-1 range.

    Args:
        score: Raw score value
        min_val: Minimum possible value
        max_val: Maximum possible value
        invert: If True, invert score (for metrics where lower is better)

    Returns:
        Normalized score in [0, 1]
    """
    if max_val == min_val:
        return 0.5

    normalized = (score - min_val) / (max_val - min_val)
    if invert:
        normalized = 1 - normalized

    return float(np.clip(normalized, 0, 1))
