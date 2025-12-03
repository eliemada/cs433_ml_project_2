"""
Benchmarking module for chunking strategies evaluation.

This module provides comprehensive evaluation tools for comparing different
text chunking strategies in the context of RAG systems.
"""

from .metrics import (
    ChunkMetrics,
    calculate_chunk_statistics,
    calculate_coherence_score,
    calculate_boundary_quality,
    evaluate_citation_integrity,
)
from .visualizations import (
    create_size_distribution_plot,
    create_comparison_heatmap,
    create_coherence_boxplot,
    create_boundary_quality_plot,
    create_citation_analysis_plot,
    create_comprehensive_dashboard,
)
from .report_generator import ReportGenerator

__all__ = [
    # Metrics
    "ChunkMetrics",
    "calculate_chunk_statistics",
    "calculate_coherence_score",
    "calculate_boundary_quality",
    "evaluate_citation_integrity",
    # Visualizations
    "create_size_distribution_plot",
    "create_comparison_heatmap",
    "create_coherence_boxplot",
    "create_boundary_quality_plot",
    "create_citation_analysis_plot",
    "create_comprehensive_dashboard",
    # Report Generation
    "ReportGenerator",
]

__version__ = "0.1.0"
