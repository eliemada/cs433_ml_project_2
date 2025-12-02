#!/usr/bin/env python3
"""
Test the retriever pipeline.

Usage:
    python scripts/test_retriever.py
    python scripts/test_retriever.py --query "your custom query"
"""

import sys
import os
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_pipeline.rag.retriever import HybridRetriever, FAISSRetriever


BUCKET_NAME = "cs433-rag-project2"

TEST_QUERIES = [
    "What are the effects of climate change on agriculture?",
    "How does machine learning improve healthcare outcomes?",
    "What are the main challenges in renewable energy adoption?",
]


def main():
    parser = argparse.ArgumentParser(description="Test the retriever")
    parser.add_argument("--query", type=str, help="Custom query to test")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    parser.add_argument("--no-rerank", action="store_true", help="Skip reranking")
    args = parser.parse_args()

    # Check API key
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)

    zeroentropy_key = os.environ.get("ZEROENTROPY_API_KEY")

    print("=" * 60)
    print("Retriever Test")
    print("=" * 60)

    # Load retriever
    print("\nLoading FAISS index from S3...")

    try:
        if zeroentropy_key and not args.no_rerank:
            print("ZeroEntropy API key found - reranking enabled")
            retriever = HybridRetriever.from_s3(
                bucket_name=BUCKET_NAME,
                openai_api_key=openai_key,
                zeroentropy_api_key=zeroentropy_key,
                chunk_type="coarse"
            )
        else:
            print("Using FAISS-only retrieval (no reranking)")
            faiss_retriever = FAISSRetriever.from_s3(
                bucket_name=BUCKET_NAME,
                chunk_type="coarse",
                openai_api_key=openai_key
            )
            retriever = HybridRetriever(faiss_retriever, reranker=None)
    except Exception as e:
        print(f"\nERROR loading index: {e}")
        sys.exit(1)

    print("\nIndex loaded successfully!")

    # Run queries
    queries = [args.query] if args.query else TEST_QUERIES

    for query in queries:
        print("\n" + "=" * 60)
        print(f"QUERY: {query}")
        print("=" * 60)

        try:
            results = retriever.search(query, top_k=args.top_k, use_reranker=not args.no_rerank)

            if not results:
                print("No results found!")
                continue

            for i, r in enumerate(results, 1):
                print(f"\n--- Result {i} (score: {r.score:.4f}) ---")
                print(f"Paper: {r.paper_title[:80]}...")
                print(f"Section: {' > '.join(r.section_hierarchy)}")
                print(f"Text: {r.text[:300]}...")

        except Exception as e:
            print(f"ERROR: {e}")

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
