"""
Regenerate plots from existing chunking evaluation JSON file.

This script takes an existing chunking evaluation JSON and regenerates
the HTML report with updated plot sizes and text formatting.

Usage:
    python scripts/regenerate_plots.py reports/chunking_evaluation_20251115_195422.json
    python scripts/regenerate_plots.py reports/chunking_evaluation_20251115_195422.json --plots-only
"""

import argparse
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_pipeline.benchmarking import (
    create_size_distribution_plot,
    create_coherence_boxplot,
    create_boundary_quality_plot,
    create_citation_analysis_plot,
    create_comprehensive_dashboard,
    ReportGenerator,
)


def main():
    parser = argparse.ArgumentParser(description="Regenerate plots from existing evaluation JSON")
    parser.add_argument(
        "json_file",
        type=str,
        help="Path to existing chunking evaluation JSON file",
    )
    parser.add_argument(
        "--output-dir",
        default="./reports",
        help="Output directory for new report",
    )
    parser.add_argument(
        "--plots-only",
        action="store_true",
        help="Only save plots as standalone files, skip HTML report",
    )
    parser.add_argument(
        "--plots-dir",
        default="./reports/plots",
        help="Directory to save standalone plot files",
    )

    args = parser.parse_args()

    # Load JSON data
    json_path = Path(args.json_file)
    if not json_path.exists():
        print(f"Error: JSON file not found: {json_path}")
        sys.exit(1)

    with open(json_path, "r") as f:
        data = json.load(f)

    print(f"Loaded data from {json_path}")

    # Extract data
    metrics_dict = data.get("strategies", {})
    size_data = data.get("size_data", {})
    coherence_data = data.get("coherence_data", {})
    boundary_data = data.get("boundary_data", {})
    citation_data = data.get("citation_data", {})

    # Determine num_papers from metadata if available
    # Otherwise estimate from size of data
    num_papers = len(size_data.get("hybrid", [])) // 10 if size_data else 10

    print("Creating visualizations with larger fonts...")

    # Create visualizations
    plots = {
        "dashboard": create_comprehensive_dashboard(metrics_dict, size_data),
        "size_distribution": create_size_distribution_plot(size_data),
        "coherence_plot": create_coherence_boxplot(coherence_data) if coherence_data else None,
        "boundary_plot": create_boundary_quality_plot(boundary_data) if boundary_data else None,
        "citation_plot": create_citation_analysis_plot(citation_data),
    }

    # Filter out None plots
    plots = {k: v for k, v in plots.items() if v is not None}

    # Save plots as standalone files
    plots_dir = Path(args.plots_dir)
    plots_dir.mkdir(parents=True, exist_ok=True)

    print(f"Saving plots to {plots_dir}...")
    plot_files = {}
    for plot_name, fig in plots.items():
        # Save as HTML (interactive)
        html_path = plots_dir / f"{plot_name}.html"
        fig.write_html(str(html_path))
        plot_files[f"{plot_name}.html"] = html_path

        # Save as PNG (static, high resolution)
        png_path = plots_dir / f"{plot_name}.png"
        fig.write_image(str(png_path), width=1200, height=800, scale=2)
        plot_files[f"{plot_name}.png"] = png_path

        # Save as PDF (vector, publication quality)
        pdf_path = plots_dir / f"{plot_name}.pdf"
        fig.write_image(str(pdf_path))
        plot_files[f"{plot_name}.pdf"] = pdf_path

    print(f"✓ Saved {len(plots)} plots in 3 formats (HTML, PNG, PDF)")

    if not args.plots_only:
        # Generate HTML report
        print("\nGenerating HTML report...")
        report_data = {
            "strategies": metrics_dict,
            "metadata": {"num_papers": num_papers, "evaluation_type": "comprehensive"},
        }

        generator = ReportGenerator(output_dir=args.output_dir)
        report_path = generator.generate_report(report_data, plots)

        print("\n" + "=" * 80)
        print("REPORT REGENERATION COMPLETE")
        print("=" * 80)
        print(f"✓ Report saved to: {report_path}")
        print(f"✓ Open in browser: file://{report_path.absolute()}")
    else:
        print("\n" + "=" * 80)
        print("PLOTS EXPORT COMPLETE")
        print("=" * 80)

    print(f"\n✓ Plots directory: {plots_dir.absolute()}")
    print("\nGenerated files:")
    for filename in sorted(plot_files.keys()):
        print(f"  - {filename}")


if __name__ == "__main__":
    main()
