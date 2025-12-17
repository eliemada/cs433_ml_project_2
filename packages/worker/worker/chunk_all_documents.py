#!/usr/bin/env python3
"""
Chunk all processed markdown documents from S3 using hybrid strategy.

Usage:
    python scripts/chunk_all_documents.py
    python scripts/chunk_all_documents.py --limit 10  # Process only 10 papers
    python scripts/chunk_all_documents.py --force     # Re-chunk existing papers
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from tqdm import tqdm
import boto3
from botocore.exceptions import ClientError

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_pipeline.rag.markdown_chunker import MarkdownChunker, Chunk
from scripts.utils.markdown_s3_loader import S3MarkdownLoader


# Configuration
BUCKET_NAME = "cs433-rag-project2"
INPUT_PREFIX = "processed/"
OUTPUT_PREFIX = "chunks/"


def check_chunks_exist(s3_client, bucket: str, paper_id: str) -> bool:
    """Check if chunks already exist for a paper."""
    coarse_key = f"{OUTPUT_PREFIX}{paper_id}_coarse.json"
    try:
        s3_client.head_object(Bucket=bucket, Key=coarse_key)
        return True
    except ClientError:
        return False


def save_chunks(
    s3_client,
    bucket: str,
    paper_id: str,
    paper_title: str,
    chunks: List[Chunk],
    chunk_type: str
) -> None:
    """Save chunks to S3 as JSON."""
    key = f"{OUTPUT_PREFIX}{paper_id}_{chunk_type}.json"

    data = {
        "paper_id": paper_id,
        "paper_title": paper_title,
        "chunk_type": chunk_type,
        "total_chunks": len(chunks),
        "chunks": [chunk.to_dict() for chunk in chunks]
    }

    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(data, indent=2).encode('utf-8'),
        ContentType='application/json'
    )


def process_paper(
    loader: S3MarkdownLoader,
    chunker: MarkdownChunker,
    s3_client,
    paper_id: str
) -> Optional[Dict]:
    """Process a single paper and return stats."""
    try:
        # Load document and metadata
        result = loader.load_paper(paper_id)
        if result is None:
            return None

        markdown_text, metadata = result

        # Extract title
        paper_title = loader.extract_title_from_metadata(metadata)

        # Chunk the document
        chunks = chunker.chunk_document(
            markdown_text=markdown_text,
            paper_id=paper_id,
            paper_title=paper_title,
            create_both_types=True
        )

        coarse_chunks = chunks['coarse']
        fine_chunks = chunks['fine']

        # Save to S3
        save_chunks(s3_client, BUCKET_NAME, paper_id, paper_title, coarse_chunks, "coarse")
        save_chunks(s3_client, BUCKET_NAME, paper_id, paper_title, fine_chunks, "fine")

        return {
            "paper_id": paper_id,
            "coarse_count": len(coarse_chunks),
            "fine_count": len(fine_chunks),
            "doc_length": len(markdown_text)
        }

    except Exception as e:
        print(f"\nError processing {paper_id}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Chunk all documents from S3")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of papers to process")
    parser.add_argument("--force", action="store_true", help="Re-chunk papers that already have chunks")
    args = parser.parse_args()

    print("=" * 60)
    print("Hybrid Chunking Pipeline")
    print("=" * 60)

    # Initialize clients
    s3_client = boto3.client('s3')
    loader = S3MarkdownLoader(bucket_name=BUCKET_NAME, prefix=INPUT_PREFIX)
    chunker = MarkdownChunker()

    # List all papers
    print("\nListing papers from S3...")
    paper_ids = loader.list_paper_ids()
    print(f"Found {len(paper_ids)} papers in S3")

    # Apply limit if specified
    if args.limit:
        paper_ids = paper_ids[:args.limit]
        print(f"Processing limited to {args.limit} papers")

    # Filter out already processed papers
    if not args.force:
        print("\nChecking for existing chunks...")
        papers_to_process = []
        for paper_id in tqdm(paper_ids, desc="Checking existing"):
            if not check_chunks_exist(s3_client, BUCKET_NAME, paper_id):
                papers_to_process.append(paper_id)

        skipped = len(paper_ids) - len(papers_to_process)
        if skipped > 0:
            print(f"Skipping {skipped} papers with existing chunks")
        paper_ids = papers_to_process

    if not paper_ids:
        print("\nNo papers to process!")
        return

    print(f"\nProcessing {len(paper_ids)} papers...")
    print("-" * 60)

    # Process papers
    stats = {
        "processed": 0,
        "failed": 0,
        "total_coarse": 0,
        "total_fine": 0,
        "failed_papers": []
    }

    for paper_id in tqdm(paper_ids, desc="Chunking papers"):
        result = process_paper(loader, chunker, s3_client, paper_id)

        if result:
            stats["processed"] += 1
            stats["total_coarse"] += result["coarse_count"]
            stats["total_fine"] += result["fine_count"]
        else:
            stats["failed"] += 1
            stats["failed_papers"].append(paper_id)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Papers processed: {stats['processed']}")
    print(f"Papers failed:    {stats['failed']}")
    print(f"Total coarse chunks: {stats['total_coarse']}")
    print(f"Total fine chunks:   {stats['total_fine']}")
    print(f"\nChunks saved to: s3://{BUCKET_NAME}/{OUTPUT_PREFIX}")

    if stats["failed_papers"]:
        print(f"\nFailed papers: {stats['failed_papers'][:10]}")
        if len(stats["failed_papers"]) > 10:
            print(f"  ... and {len(stats['failed_papers']) - 10} more")


if __name__ == "__main__":
    main()
