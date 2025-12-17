"""
Generate comprehensive chunking strategy evaluation report.

This script performs end-to-end benchmarking of different chunking strategies
and generates an interactive HTML report with visualizations and recommendations.

Usage:
    python scripts/generate_chunking_report.py --num-papers 10 --output-dir ./reports
    python scripts/generate_chunking_report.py --num-papers 50 --with-embeddings
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List
import json
import logging
from tqdm.auto import tqdm
import numpy as np
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_pipeline.rag.markdown_chunker import MarkdownChunker
from scripts.utils.markdown_s3_loader import S3MarkdownLoader
from rag_pipeline.benchmarking import (
    calculate_chunk_statistics,
    calculate_coherence_score,
    calculate_boundary_quality,
    evaluate_citation_integrity,
    ChunkMetrics,
    create_size_distribution_plot,
    create_comparison_heatmap,
    create_coherence_boxplot,
    create_boundary_quality_plot,
    create_citation_analysis_plot,
    create_comprehensive_dashboard,
    ReportGenerator,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_embedding_function(use_openai: bool = False):
    """Get embedding function for coherence/boundary analysis."""
    if use_openai:
        try:
            from openai import OpenAI

            client = OpenAI()

            def embed_fn(texts: List[str]) -> np.ndarray:
                response = client.embeddings.create(
                    model="text-embedding-3-small", input=texts
                )
                return np.array([item.embedding for item in response.data])

            return embed_fn
        except Exception as e:
            logger.warning(f"OpenAI embedding failed: {e}. Using mock embeddings.")

    # Mock embedding function (for testing without API)
    def mock_embed_fn(texts: List[str]) -> np.ndarray:
        np.random.seed(42)
        return np.random.rand(len(texts), 384)

    return mock_embed_fn


def evaluate_strategy(
    strategy_name: str,
    chunker: MarkdownChunker,
    papers: List[Dict],
    embedding_fn: callable,
    evaluate_coherence: bool = True,
) -> Dict:
    """
    Evaluate a single chunking strategy.

    Args:
        strategy_name: Name of the strategy
        chunker: MarkdownChunker instance
        papers: List of paper dicts (markdown, metadata, etc.)
        embedding_fn: Function to generate embeddings
        evaluate_coherence: Whether to run expensive coherence analysis

    Returns:
        Dictionary with all evaluation results
    """
    logger.info(f"Evaluating {strategy_name} strategy...")

    all_coarse_chunks = []
    chunk_sizes = []

    # Generate chunks for all papers
    for paper in tqdm(papers, desc=f"{strategy_name}: Chunking"):
        result = chunker.chunk_document(
            paper["markdown"], paper["paper_id"], paper["title"], create_both_types=False
        )
        coarse_chunks = result["coarse"]
        all_coarse_chunks.extend(coarse_chunks)
        chunk_sizes.extend([len(c.text) for c in coarse_chunks])

    # Calculate statistics
    stats = calculate_chunk_statistics(all_coarse_chunks)

    # Citation analysis
    citation_stats = evaluate_citation_integrity(all_coarse_chunks)

    # Coherence analysis (optional - expensive)
    coherence_scores = []
    if evaluate_coherence and len(all_coarse_chunks) > 0:
        sample_size = min(20, len(all_coarse_chunks))
        sample_indices = np.random.choice(len(all_coarse_chunks), sample_size, replace=False)

        for idx in tqdm(
            sample_indices, desc=f"{strategy_name}: Coherence", leave=False
        ):
            chunk = all_coarse_chunks[idx]
            score = calculate_coherence_score(chunk.text, embedding_fn)
            coherence_scores.append(score)

    # Boundary quality analysis (optional - expensive)
    boundary_scores = []
    if evaluate_coherence and len(all_coarse_chunks) > 1:
        boundary_scores = calculate_boundary_quality(
            all_coarse_chunks, embedding_fn, num_samples=15
        )

    # Create ChunkMetrics object
    metrics = ChunkMetrics(
        strategy_name=strategy_name,
        total_chunks=stats["count"],
        mean_size_chars=stats["mean_chars"],
        median_size_chars=stats["median_chars"],
        std_size_chars=stats["std_chars"],
        min_size_chars=stats["min_chars"],
        max_size_chars=stats["max_chars"],
        mean_size_tokens=stats["mean_tokens"],
        median_size_tokens=stats["median_tokens"],
        coherence_score=float(np.mean(coherence_scores)) if coherence_scores else None,
        boundary_quality=float(np.mean(boundary_scores)) if boundary_scores else None,
        citation_coverage=citation_stats["citation_coverage"],
        total_citations=citation_stats["total_citations"],
        chunks_with_citations=citation_stats["chunks_with_citations"],
    )

    return {
        "metrics": metrics,
        "chunk_sizes": chunk_sizes,
        "coherence_scores": coherence_scores,
        "boundary_scores": boundary_scores,
        "citation_stats": citation_stats,
    }


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Generate chunking strategy evaluation report"
    )
    parser.add_argument(
        "--num-papers", type=int, default=10, help="Number of papers to analyze"
    )
    parser.add_argument(
        "--output-dir", default="./reports", help="Output directory for reports"
    )
    parser.add_argument(
        "--with-embeddings",
        action="store_true",
        help="Use OpenAI embeddings for coherence analysis (requires API key)",
    )
    parser.add_argument(
        "--skip-coherence",
        action="store_true",
        help="Skip coherence/boundary analysis (faster)",
    )
    parser.add_argument(
        "--bucket", default="cs433-rag-project2", help="S3 bucket name"
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("CHUNKING STRATEGY EVALUATION")
    logger.info("=" * 80)
    logger.info(f"Papers to analyze: {args.num_papers}")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Using embeddings: {args.with_embeddings}")
    logger.info("")

    # Load papers from S3
    logger.info("Loading papers from S3...")
    loader = S3MarkdownLoader(bucket_name=args.bucket)
    paper_ids = loader.list_paper_ids()[: args.num_papers]

    papers = []
    for paper_id in tqdm(paper_ids, desc="Loading papers"):
        result = loader.load_paper(paper_id)
        if result:
            markdown_text, metadata = result
            title = loader.extract_title_from_metadata(metadata)
            papers.append(
                {"paper_id": paper_id, "title": title, "markdown": markdown_text}
            )

    logger.info(f"✓ Loaded {len(papers)} papers")

    # Initialize strategies
    strategies = {
        "hybrid": MarkdownChunker(
            coarse_target_size=2100,
            coarse_max_size=2600,
            coarse_overlap_pct=0.15,
            fine_target_size=350,
            fine_max_size=500,
            fine_overlap_pct=0.25,
        ),
        "fixed": MarkdownChunker(
            coarse_target_size=2000,
            coarse_max_size=2000,
            coarse_overlap_pct=0.10,
        ),
        "semantic": MarkdownChunker(
            coarse_target_size=5000,
            coarse_max_size=10000,
            coarse_overlap_pct=0.05,
        ),
    }

    # Get embedding function
    embedding_fn = get_embedding_function(use_openai=args.with_embeddings)

    # Evaluate all strategies
    results = {}
    for strategy_name, chunker in strategies.items():
        results[strategy_name] = evaluate_strategy(
            strategy_name,
            chunker,
            papers,
            embedding_fn,
            evaluate_coherence=not args.skip_coherence,
        )

    logger.info("\n" + "=" * 80)
    logger.info("EVALUATION COMPLETE - GENERATING VISUALIZATIONS")
    logger.info("=" * 80)

    # Prepare data for visualizations
    metrics_dict = {
        name: result["metrics"].to_dict() for name, result in results.items()
    }
    size_data = {name: result["chunk_sizes"] for name, result in results.items()}
    coherence_data = {
        name: result["coherence_scores"] for name, result in results.items()
    }
    boundary_data = {name: result["boundary_scores"] for name, result in results.items()}
    citation_data = {
        name: result["citation_stats"] for name, result in results.items()
    }

    # Create visualizations
    logger.info("Creating visualizations...")
    plots = {
        "dashboard": create_comprehensive_dashboard(metrics_dict, size_data),
        "size_distribution": create_size_distribution_plot(size_data),
        "coherence_plot": create_coherence_boxplot(coherence_data)
        if not args.skip_coherence
        else None,
        "boundary_plot": create_boundary_quality_plot(boundary_data)
        if not args.skip_coherence
        else None,
        "citation_plot": create_citation_analysis_plot(citation_data),
    }

    # Filter out None plots
    plots = {k: v for k, v in plots.items() if v is not None}

    # Generate HTML report
    logger.info("Generating HTML report...")
    report_data = {
        "strategies": metrics_dict,
        "metadata": {"num_papers": len(papers), "evaluation_type": "comprehensive"},
    }

    generator = ReportGenerator(output_dir=args.output_dir)
    report_path = generator.generate_report(report_data, plots)

    logger.info("\n" + "=" * 80)
    logger.info("REPORT GENERATION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"✓ Report saved to: {report_path}")
    logger.info(f"✓ Open in browser: file://{report_path.absolute()}")

    # Save raw data as JSON
    json_path = report_path.with_suffix(".json")
    with open(json_path, "w") as f:
        json.dump(
            {
                "strategies": metrics_dict,
                "size_data": {k: [int(v) for v in vals] for k, vals in size_data.items()},
                "coherence_data": {
                    k: [float(v) for v in vals] for k, vals in coherence_data.items()
                },
                "boundary_data": {
                    k: [float(v) for v in vals] for k, vals in boundary_data.items()
                },
                "citation_data": citation_data,
            },
            f,
            indent=2,
        )
    logger.info(f"✓ Raw data saved to: {json_path}")

    # Print summary table
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY STATISTICS")
    logger.info("=" * 80)

    for strategy_name, result in results.items():
        metrics = result["metrics"]
        logger.info(f"\n{strategy_name.upper()}:")
        logger.info(f"  Total chunks: {metrics.total_chunks}")
        logger.info(
            f"  Mean size: {metrics.mean_size_chars:.0f} chars ({metrics.mean_size_tokens:.0f} tokens)"
        )
        logger.info(f"  Size std dev: {metrics.std_size_chars:.0f}")
        if metrics.coherence_score:
            logger.info(f"  Coherence: {metrics.coherence_score:.3f}")
        if metrics.boundary_quality:
            logger.info(f"  Boundary quality: {metrics.boundary_quality:.3f}")
        logger.info(f"  Citation coverage: {metrics.citation_coverage * 100:.1f}%")

    logger.info("\n✅ Done! Open the HTML report to view detailed analysis.")


if __name__ == "__main__":
    main()
