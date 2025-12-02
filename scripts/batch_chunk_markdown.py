"""
Batch process all papers in S3: chunk and save results.

Usage:
    python batch_chunk_papers.py --output-dir ./chunks --num-papers 10
    python batch_chunk_papers.py --save-to-s3 --chunk-type both
"""

import argparse
import json
import sys
from pathlib import Path
from tqdm.auto import tqdm
import time

from rag_pipeline.rag.markdown_chunker import MarkdownChunker
from scripts.utils.markdown_s3_loader import S3MarkdownLoader


def chunk_all_papers(
    bucket_name: str,
    output_dir: str = None,
    save_to_s3: bool = False,
    s3_output_prefix: str = "chunks/",
    chunk_type: str = "both",  # "coarse", "fine", or "both"
    num_papers: int = None,
    start_index: int = 0,
    coarse_target_size: int = 2000,
    fine_target_size: int = 300,
):
    """
    Batch process papers: load from S3, chunk, and save results.

    Args:
        bucket_name: S3 bucket name
        output_dir: Local directory to save chunks (if not saving to S3)
        save_to_s3: If True, save chunks back to S3
        s3_output_prefix: S3 prefix for output chunks
        chunk_type: "coarse", "fine", or "both"
        num_papers: Number of papers to process (None = all)
        start_index: Starting index in paper list
        coarse_target_size: Target size for coarse chunks
        fine_target_size: Target size for fine chunks
    """
    # Initialize loader and chunker
    loader = S3MarkdownLoader(bucket_name=bucket_name)
    chunker = MarkdownChunker(
        coarse_target_size=coarse_target_size,
        fine_target_size=fine_target_size
    )

    # Get paper IDs
    all_paper_ids = loader.list_paper_ids()
    print(f"Found {len(all_paper_ids)} papers in S3")

    # Select subset
    if num_papers is not None:
        end_index = min(start_index + num_papers, len(all_paper_ids))
        paper_ids = all_paper_ids[start_index:end_index]
        print(f"Processing papers {start_index} to {end_index-1} ({len(paper_ids)} papers)")
    else:
        paper_ids = all_paper_ids[start_index:]
        print(f"Processing all papers from index {start_index} ({len(paper_ids)} papers)")

    # Setup output directory if saving locally
    if output_dir and not save_to_s3:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        print(f"Saving chunks to: {output_path}")

    # Process papers
    stats = {
        'processed': 0,
        'failed': 0,
        'total_coarse_chunks': 0,
        'total_fine_chunks': 0,
        'errors': []
    }

    start_time = time.time()

    for paper_id in tqdm(paper_ids, desc="Processing papers"):
        try:
            # Load paper
            result = loader.load_paper(paper_id)
            if not result:
                stats['failed'] += 1
                stats['errors'].append({'paper_id': paper_id, 'error': 'Failed to load'})
                continue

            markdown_text, metadata = result
            title = loader.extract_title_from_metadata(metadata)

            # Chunk document
            create_both = (chunk_type == "both")
            chunks_result = chunker.chunk_document(
                markdown_text,
                paper_id,
                title,
                create_both_types=create_both
            )

            # Convert chunks to dicts for JSON serialization
            coarse_chunks = [chunk.to_dict() for chunk in chunks_result['coarse']]
            fine_chunks = [chunk.to_dict() for chunk in chunks_result['fine']]

            stats['total_coarse_chunks'] += len(coarse_chunks)
            stats['total_fine_chunks'] += len(fine_chunks)

            # Save results
            if save_to_s3:
                # Save to S3
                if chunk_type in ["coarse", "both"]:
                    loader.save_chunks_to_s3(coarse_chunks, paper_id, "coarse", s3_output_prefix)
                if chunk_type in ["fine", "both"]:
                    loader.save_chunks_to_s3(fine_chunks, paper_id, "fine", s3_output_prefix)
            else:
                # Save locally
                paper_output_dir = output_path / paper_id
                paper_output_dir.mkdir(exist_ok=True)

                if chunk_type in ["coarse", "both"]:
                    with open(paper_output_dir / "coarse_chunks.json", 'w') as f:
                        json.dump(coarse_chunks, f, indent=2)

                if chunk_type in ["fine", "both"]:
                    with open(paper_output_dir / "fine_chunks.json", 'w') as f:
                        json.dump(fine_chunks, f, indent=2)

            stats['processed'] += 1

        except Exception as e:
            stats['failed'] += 1
            stats['errors'].append({'paper_id': paper_id, 'error': str(e)})
            print(f"\n❌ Error processing {paper_id}: {e}")
            continue

    # Print summary
    elapsed_time = time.time() - start_time
    print("\n" + "=" * 80)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 80)
    print(f"Processed: {stats['processed']} papers")
    print(f"Failed: {stats['failed']} papers")
    print(f"Total coarse chunks: {stats['total_coarse_chunks']}")
    print(f"Total fine chunks: {stats['total_fine_chunks']}")
    print(f"Time elapsed: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")
    print(f"Avg time per paper: {elapsed_time/max(stats['processed'], 1):.2f} seconds")

    if stats['errors']:
        print(f"\n⚠️  {len(stats['errors'])} errors occurred:")
        for error in stats['errors'][:10]:  # Show first 10
            print(f"  - {error['paper_id']}: {error['error']}")

    # Save summary
    summary_file = Path(output_dir or ".") / "batch_processing_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"\nSummary saved to: {summary_file}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Batch chunk papers from S3")
    parser.add_argument(
        "--bucket",
        default="cs433-rag-project2",
        help="S3 bucket name"
    )
    parser.add_argument(
        "--output-dir",
        default="./chunks",
        help="Local directory to save chunks"
    )
    parser.add_argument(
        "--save-to-s3",
        action="store_true",
        help="Save chunks to S3 instead of locally"
    )
    parser.add_argument(
        "--s3-output-prefix",
        default="chunks/",
        help="S3 prefix for output chunks"
    )
    parser.add_argument(
        "--chunk-type",
        choices=["coarse", "fine", "both"],
        default="both",
        help="Type of chunks to create"
    )
    parser.add_argument(
        "--num-papers",
        type=int,
        default=None,
        help="Number of papers to process (default: all)"
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="Starting index in paper list"
    )
    parser.add_argument(
        "--coarse-size",
        type=int,
        default=2000,
        help="Target size for coarse chunks"
    )
    parser.add_argument(
        "--fine-size",
        type=int,
        default=300,
        help="Target size for fine chunks"
    )

    args = parser.parse_args()

    print("Starting batch processing with configuration:")
    print(f"  Bucket: {args.bucket}")
    print(f"  Output: {'S3: ' + args.s3_output_prefix if args.save_to_s3 else 'Local: ' + args.output_dir}")
    print(f"  Chunk type: {args.chunk_type}")
    print(f"  Num papers: {args.num_papers or 'all'}")
    print(f"  Start index: {args.start_index}")
    print(f"  Coarse size: {args.coarse_size} chars")
    print(f"  Fine size: {args.fine_size} chars")
    print()

    stats = chunk_all_papers(
        bucket_name=args.bucket,
        output_dir=args.output_dir,
        save_to_s3=args.save_to_s3,
        s3_output_prefix=args.s3_output_prefix,
        chunk_type=args.chunk_type,
        num_papers=args.num_papers,
        start_index=args.start_index,
        coarse_target_size=args.coarse_size,
        fine_target_size=args.fine_size
    )

    # Exit with error code if failures
    if stats['failed'] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
