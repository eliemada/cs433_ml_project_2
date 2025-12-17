#!/usr/bin/env python3
"""
Embed chunks and build FAISS indexes.

Usage:
    python scripts/embed_and_index.py
    python scripts/embed_and_index.py --chunk-type coarse  # Only coarse chunks
    python scripts/embed_and_index.py --dry-run            # Estimate costs without processing
"""

import sys
import os
import json
import argparse
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
from tqdm import tqdm
import boto3
from botocore.exceptions import ClientError
import faiss

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_pipeline.rag.openai_embedder import OpenAIEmbedder


# Configuration
BUCKET_NAME = "cs433-rag-project2"
CHUNKS_PREFIX = "chunks/"
INDEX_PREFIX = "indexes/"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
BATCH_SIZE = 100


def load_all_chunks(s3_client, chunk_type: str) -> Tuple[List[Dict], List[str]]:
    """
    Load all chunks of a given type from S3.

    Returns:
        Tuple of (list of chunk dicts, list of texts for embedding)
    """
    print(f"\nLoading {chunk_type} chunks from S3...")

    # List all chunk files
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix=CHUNKS_PREFIX)

    chunk_files = []
    for page in pages:
        for obj in page.get('Contents', []):
            key = obj['Key']
            if f"_{chunk_type}.json" in key:
                chunk_files.append(key)

    print(f"Found {len(chunk_files)} {chunk_type} chunk files")

    # Load all chunks
    all_chunks = []
    all_texts = []

    for key in tqdm(chunk_files, desc=f"Loading {chunk_type} chunks"):
        try:
            response = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
            data = json.loads(response['Body'].read().decode('utf-8'))

            for chunk in data.get('chunks', []):
                # Store full chunk metadata
                all_chunks.append({
                    "chunk_id": chunk["chunk_id"],
                    "paper_id": chunk["paper_id"],
                    "paper_title": chunk["paper_title"],
                    "text": chunk["text"],
                    "section_hierarchy": chunk["section_hierarchy"],
                    "chunk_index": chunk["chunk_index"],
                    "char_start": chunk["char_start"],
                    "char_end": chunk["char_end"]
                })
                all_texts.append(chunk["text"])

        except Exception as e:
            print(f"\nError loading {key}: {e}")
            continue

    print(f"Loaded {len(all_chunks)} {chunk_type} chunks total")
    return all_chunks, all_texts


def estimate_cost(texts: List[str], embedder: OpenAIEmbedder) -> float:
    """Estimate embedding cost."""
    total_tokens = sum(embedder.calculate_tokens(text) for text in tqdm(texts[:100], desc="Estimating tokens"))
    avg_tokens = total_tokens / min(len(texts), 100)
    total_estimated_tokens = int(avg_tokens * len(texts))
    cost = embedder.calculate_cost(total_estimated_tokens)
    return cost, total_estimated_tokens


def generate_embeddings(
    texts: List[str],
    embedder: OpenAIEmbedder,
    batch_size: int = 100
) -> np.ndarray:
    """Generate embeddings for all texts with progress bar."""
    print(f"\nGenerating embeddings for {len(texts)} texts...")

    all_embeddings = []

    for i in tqdm(range(0, len(texts), batch_size), desc="Embedding batches"):
        batch = texts[i:i + batch_size]

        # Generate embeddings for batch
        batch_embeddings = embedder.generate_embeddings_batch(batch)
        all_embeddings.extend(batch_embeddings)

    # Convert to numpy array and normalize for cosine similarity
    embeddings = np.array(all_embeddings, dtype=np.float32)
    faiss.normalize_L2(embeddings)

    print(f"Generated {len(embeddings)} embeddings with shape {embeddings.shape}")
    return embeddings


def build_faiss_index(embeddings: np.ndarray) -> faiss.Index:
    """Build FAISS index from embeddings."""
    print(f"\nBuilding FAISS index...")

    # Use IndexFlatIP for cosine similarity (with normalized vectors)
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)

    # Add vectors
    index.add(embeddings)

    print(f"FAISS index built with {index.ntotal} vectors")
    return index


def save_to_s3(
    s3_client,
    index: faiss.Index,
    metadata: List[Dict],
    chunk_type: str
):
    """Save FAISS index and metadata to S3."""
    import tempfile

    # Save index to temp file then upload
    with tempfile.NamedTemporaryFile(suffix='.faiss', delete=False) as f:
        index_path = f.name

    faiss.write_index(index, index_path)

    # Upload index
    index_key = f"{INDEX_PREFIX}{chunk_type}.faiss"
    print(f"\nUploading index to s3://{BUCKET_NAME}/{index_key}...")
    s3_client.upload_file(index_path, BUCKET_NAME, index_key)
    os.unlink(index_path)

    # Save metadata (mapping index position to chunk details)
    metadata_dict = {str(i): meta for i, meta in enumerate(metadata)}
    metadata_key = f"{INDEX_PREFIX}{chunk_type}_metadata.json"

    print(f"Uploading metadata to s3://{BUCKET_NAME}/{metadata_key}...")
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=metadata_key,
        Body=json.dumps(metadata_dict, indent=2).encode('utf-8'),
        ContentType='application/json'
    )

    print(f"Saved index ({index.ntotal} vectors) and metadata to S3")


def main():
    parser = argparse.ArgumentParser(description="Embed chunks and build FAISS index")
    parser.add_argument("--chunk-type", choices=["coarse", "fine", "both"], default="both",
                        help="Which chunk type to process")
    parser.add_argument("--dry-run", action="store_true",
                        help="Estimate costs without processing")
    args = parser.parse_args()

    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    print("=" * 60)
    print("Embedding & Indexing Pipeline")
    print("=" * 60)
    print(f"Model: {EMBEDDING_MODEL}")
    print(f"Dimensions: {EMBEDDING_DIM}")

    # Initialize clients
    s3_client = boto3.client('s3')
    embedder = OpenAIEmbedder(
        api_key=api_key,
        model=EMBEDDING_MODEL,
        batch_size=BATCH_SIZE
    )

    chunk_types = ["coarse", "fine"] if args.chunk_type == "both" else [args.chunk_type]

    for chunk_type in chunk_types:
        print(f"\n{'=' * 60}")
        print(f"Processing {chunk_type.upper()} chunks")
        print("=" * 60)

        # Load chunks
        chunks, texts = load_all_chunks(s3_client, chunk_type)

        if not chunks:
            print(f"No {chunk_type} chunks found!")
            continue

        # Estimate cost
        cost, total_tokens = estimate_cost(texts, embedder)
        print(f"\nEstimated cost: ${cost:.4f} ({total_tokens:,} tokens)")

        if args.dry_run:
            print("Dry run - skipping embedding generation")
            continue

        # Confirm before proceeding
        response = input(f"\nProceed with embedding {len(texts)} {chunk_type} chunks? [y/N]: ")
        if response.lower() != 'y':
            print("Skipping...")
            continue

        # Generate embeddings
        embeddings = generate_embeddings(texts, embedder, BATCH_SIZE)

        # Build index
        index = build_faiss_index(embeddings)

        # Save to S3
        save_to_s3(s3_client, index, chunks, chunk_type)

    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)
    print(f"Indexes saved to: s3://{BUCKET_NAME}/{INDEX_PREFIX}")


if __name__ == "__main__":
    main()
