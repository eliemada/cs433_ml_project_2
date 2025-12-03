"""
Interactive visualizations for chunking strategy evaluation using Plotly.

This module provides publication-quality, interactive visualizations for
comparing and analyzing different chunking strategies.
"""

from typing import List, Dict, Optional
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd


# Color scheme for consistent branding
COLORS = {
    "hybrid": "#2E86AB",  # Blue
    "fixed": "#A23B72",  # Purple
    "semantic": "#F18F01",  # Orange
    "primary": "#06A77D",  # Green
    "secondary": "#D741A7",  # Pink
}

STRATEGY_NAMES = {"hybrid": "Hybrid Semantic", "fixed": "Fixed-Size", "semantic": "Pure Semantic"}


def create_size_distribution_plot(
    strategy_data: Dict[str, List], title: str = "Chunk Size Distribution by Strategy"
) -> go.Figure:
    """
    Create interactive histogram showing chunk size distributions.

    Args:
        strategy_data: Dict mapping strategy names to lists of chunk sizes
        title: Plot title

    Returns:
        Plotly Figure object
    """
    fig = go.Figure()

    for strategy_name, sizes in strategy_data.items():
        display_name = STRATEGY_NAMES.get(strategy_name, strategy_name.capitalize())
        color = COLORS.get(strategy_name, COLORS["primary"])

        fig.add_trace(
            go.Histogram(
                x=sizes,
                name=display_name,
                marker_color=color,
                opacity=0.7,
                nbinsx=30,
                hovertemplate="<b>%{x:.0f} chars</b><br>Count: %{y}<extra></extra>",
            )
        )

    fig.update_layout(
        title={
            "text": title,
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 20, "family": "Arial, sans-serif"},
        },
        xaxis_title="Chunk Size (characters)",
        yaxis_title="Frequency",
        barmode="overlay",
        template="plotly_white",
        hovermode="x unified",
        font={"family": "Arial, sans-serif", "size": 12},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
        height=500,
    )

    return fig


def create_comparison_heatmap(
    metrics_df: pd.DataFrame, title: str = "Chunking Strategy Comparison Matrix"
) -> go.Figure:
    """
    Create heatmap comparing all metrics across strategies.

    Args:
        metrics_df: DataFrame with strategies as rows and metrics as columns
        title: Plot title

    Returns:
        Plotly Figure object
    """
    # Normalize metrics to 0-1 scale for comparison
    normalized_df = metrics_df.copy()

    # Invert metrics where lower is better
    invert_metrics = ["std_size_chars", "boundary_quality"]

    for col in normalized_df.columns:
        if col != "strategy_name":
            min_val = normalized_df[col].min()
            max_val = normalized_df[col].max()

            if max_val > min_val:
                if col in invert_metrics:
                    # Lower is better - invert normalization
                    normalized_df[col] = 1 - (
                        (normalized_df[col] - min_val) / (max_val - min_val)
                    )
                else:
                    normalized_df[col] = (normalized_df[col] - min_val) / (max_val - min_val)

    # Prepare data for heatmap
    strategies = normalized_df["strategy_name"].tolist()
    metrics = [col for col in normalized_df.columns if col != "strategy_name"]
    values = normalized_df[metrics].values

    fig = go.Figure(
        data=go.Heatmap(
            z=values,
            x=[m.replace("_", " ").title() for m in metrics],
            y=strategies,
            colorscale="RdYlGn",
            text=values,
            texttemplate="%{text:.2f}",
            textfont={"size": 10},
            hovertemplate="<b>%{y}</b><br>%{x}: %{z:.3f}<extra></extra>",
            colorbar=dict(title="Score<br>(Normalized)"),
        )
    )

    fig.update_layout(
        title={
            "text": title,
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 20, "family": "Arial, sans-serif"},
        },
        xaxis_title="Metrics",
        yaxis_title="Strategy",
        template="plotly_white",
        font={"family": "Arial, sans-serif", "size": 12},
        height=400,
    )

    return fig


def create_coherence_boxplot(
    coherence_data: Dict[str, List[float]], title: str = "Semantic Coherence by Strategy"
) -> go.Figure:
    """
    Create box plot comparing semantic coherence across strategies.

    Args:
        coherence_data: Dict mapping strategy names to lists of coherence scores
        title: Plot title

    Returns:
        Plotly Figure object
    """
    fig = go.Figure()

    for strategy_name, scores in coherence_data.items():
        display_name = STRATEGY_NAMES.get(strategy_name, strategy_name.capitalize())
        color = COLORS.get(strategy_name, COLORS["primary"])

        fig.add_trace(
            go.Box(
                y=scores,
                name=display_name,
                marker_color=color,
                boxmean="sd",  # Show mean and standard deviation
                hovertemplate="<b>%{y:.3f}</b><extra></extra>",
            )
        )

    fig.update_layout(
        title={
            "text": title,
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 20, "family": "Arial, sans-serif"},
        },
        yaxis_title="Coherence Score (Cosine Similarity)",
        xaxis_title="Strategy",
        template="plotly_white",
        font={"family": "Arial, sans-serif", "size": 12},
        showlegend=False,
        height=500,
    )

    # Add reference line at median
    fig.add_hline(
        y=np.median([score for scores in coherence_data.values() for score in scores]),
        line_dash="dash",
        line_color="gray",
        annotation_text="Overall Median",
        annotation_position="right",
    )

    return fig


def create_boundary_quality_plot(
    boundary_data: Dict[str, List[float]],
    title: str = "Chunk Boundary Quality (Lower is Better)",
) -> go.Figure:
    """
    Create violin plot showing boundary quality distributions.

    Args:
        boundary_data: Dict mapping strategy names to boundary similarity scores
        title: Plot title

    Returns:
        Plotly Figure object
    """
    fig = go.Figure()

    for strategy_name, scores in boundary_data.items():
        display_name = STRATEGY_NAMES.get(strategy_name, strategy_name.capitalize())
        color = COLORS.get(strategy_name, COLORS["primary"])

        fig.add_trace(
            go.Violin(
                y=scores,
                name=display_name,
                marker_color=color,
                box_visible=True,
                meanline_visible=True,
                hovertemplate="<b>%{y:.3f}</b><extra></extra>",
            )
        )

    fig.update_layout(
        title={
            "text": title,
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 20, "family": "Arial, sans-serif"},
        },
        yaxis_title="Boundary Similarity (Lower = Better Splits)",
        xaxis_title="Strategy",
        template="plotly_white",
        font={"family": "Arial, sans-serif", "size": 12},
        showlegend=False,
        height=500,
    )

    return fig


def create_citation_analysis_plot(
    citation_data: Dict[str, Dict], title: str = "Citation Preservation Analysis"
) -> go.Figure:
    """
    Create grouped bar chart showing citation metrics.

    Args:
        citation_data: Dict mapping strategy names to citation statistics
        title: Plot title

    Returns:
        Plotly Figure object
    """
    strategies = list(citation_data.keys())
    display_names = [STRATEGY_NAMES.get(s, s.capitalize()) for s in strategies]

    total_citations = [citation_data[s]["total_citations"] for s in strategies]
    coverage_pct = [citation_data[s]["citation_coverage"] * 100 for s in strategies]

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Total Citations Found", "Citation Coverage (%)"),
        specs=[[{"type": "bar"}, {"type": "bar"}]],
    )

    # Total citations
    fig.add_trace(
        go.Bar(
            x=display_names,
            y=total_citations,
            name="Total Citations",
            marker_color=[COLORS.get(s, COLORS["primary"]) for s in strategies],
            hovertemplate="<b>%{x}</b><br>Citations: %{y}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # Coverage percentage
    fig.add_trace(
        go.Bar(
            x=display_names,
            y=coverage_pct,
            name="Coverage %",
            marker_color=[COLORS.get(s, COLORS["primary"]) for s in strategies],
            hovertemplate="<b>%{x}</b><br>Coverage: %{y:.1f}%<extra></extra>",
        ),
        row=1,
        col=2,
    )

    fig.update_xaxes(title_text="Strategy", row=1, col=1)
    fig.update_xaxes(title_text="Strategy", row=1, col=2)
    fig.update_yaxes(title_text="Count", row=1, col=1)
    fig.update_yaxes(title_text="Percentage", row=1, col=2)

    fig.update_layout(
        title={
            "text": title,
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 20, "family": "Arial, sans-serif"},
        },
        template="plotly_white",
        font={"family": "Arial, sans-serif", "size": 12},
        showlegend=False,
        height=500,
    )

    return fig


def create_comprehensive_dashboard(
    all_metrics: Dict[str, Dict], size_data: Dict[str, List[int]]
) -> go.Figure:
    """
    Create comprehensive dashboard with all key metrics.

    Args:
        all_metrics: Dict mapping strategy names to all metrics
        size_data: Dict mapping strategy names to chunk sizes

    Returns:
        Plotly Figure object with subplots
    """
    strategies = list(all_metrics.keys())
    display_names = [STRATEGY_NAMES.get(s, s.capitalize()) for s in strategies]
    colors_list = [COLORS.get(s, COLORS["primary"]) for s in strategies]

    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Mean Chunk Size",
            "Size Variance (Std Dev)",
            "Semantic Coherence",
            "Citation Coverage",
        ),
        specs=[[{"type": "bar"}, {"type": "bar"}], [{"type": "bar"}, {"type": "bar"}]],
        vertical_spacing=0.12,
        horizontal_spacing=0.1,
    )

    # Mean size
    fig.add_trace(
        go.Bar(
            x=display_names,
            y=[all_metrics[s]["mean_size_chars"] for s in strategies],
            marker_color=colors_list,
            hovertemplate="<b>%{x}</b><br>Mean: %{y:.0f} chars<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # Variance
    fig.add_trace(
        go.Bar(
            x=display_names,
            y=[all_metrics[s]["std_size_chars"] for s in strategies],
            marker_color=colors_list,
            hovertemplate="<b>%{x}</b><br>Std Dev: %{y:.0f}<extra></extra>",
        ),
        row=1,
        col=2,
    )

    # Coherence
    fig.add_trace(
        go.Bar(
            x=display_names,
            y=[
                all_metrics[s].get("coherence_score", 0) or 0
                for s in strategies
            ],
            marker_color=colors_list,
            hovertemplate="<b>%{x}</b><br>Coherence: %{y:.3f}<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # Citation coverage
    fig.add_trace(
        go.Bar(
            x=display_names,
            y=[
                (all_metrics[s].get("citation_coverage", 0) or 0) * 100
                for s in strategies
            ],
            marker_color=colors_list,
            hovertemplate="<b>%{x}</b><br>Coverage: %{y:.1f}%<extra></extra>",
        ),
        row=2,
        col=2,
    )

    # Update axes
    fig.update_yaxes(title_text="Characters", row=1, col=1)
    fig.update_yaxes(title_text="Characters", row=1, col=2)
    fig.update_yaxes(title_text="Score", row=2, col=1)
    fig.update_yaxes(title_text="Percentage", row=2, col=2)

    fig.update_layout(
        title={
            "text": "Chunking Strategy Performance Dashboard",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 22, "family": "Arial, sans-serif", "weight": "bold"},
        },
        template="plotly_white",
        font={"family": "Arial, sans-serif", "size": 12},
        showlegend=False,
        height=800,
    )

    return fig


def create_radar_chart(metrics_df: pd.DataFrame, title: str = "Strategy Comparison Radar") -> go.Figure:
    """
    Create radar chart comparing strategies across normalized metrics.

    Args:
        metrics_df: DataFrame with metrics for each strategy
        title: Plot title

    Returns:
        Plotly Figure object
    """
    # Select key metrics for radar chart
    radar_metrics = [
        "mean_size_chars",
        "coherence_score",
        "citation_coverage",
        "boundary_quality",
    ]

    fig = go.Figure()

    for _, row in metrics_df.iterrows():
        strategy = row["strategy_name"]
        display_name = STRATEGY_NAMES.get(strategy, strategy.capitalize())
        color = COLORS.get(strategy, COLORS["primary"])

        # Normalize values to 0-1
        values = []
        for metric in radar_metrics:
            if metric in row and row[metric] is not None:
                # Normalize (simplified - would need min/max from all strategies)
                values.append(row[metric])
            else:
                values.append(0)

        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=[m.replace("_", " ").title() for m in radar_metrics],
                fill="toself",
                name=display_name,
                line_color=color,
            )
        )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title={
            "text": title,
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 20, "family": "Arial, sans-serif"},
        },
        template="plotly_white",
        font={"family": "Arial, sans-serif", "size": 12},
        height=600,
    )

    return fig
