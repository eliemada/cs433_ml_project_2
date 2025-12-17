"""Command-line interface for RAG pipeline."""

import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from typing import Optional
from loguru import logger

from rag_pipeline import PDFDownloader
from rag_pipeline.openalex.config import OpenAlexConfig

app = typer.Typer(
    name="rag-pipeline",
    help="RAG Pipeline for Academic Papers with OpenAlex and Dolphin",
    add_completion=False,
)

console = Console()


@app.command()
def fetch_metadata(
    filters: Optional[str] = typer.Option(
        "primary_topic.id:t10856,open_access.is_oa:true",
        "--filter",
        "-f",
        help="Comma-separated filters (e.g., 'primary_topic.id:t10856,open_access.is_oa:true')",
    ),
    output_dir: Path = typer.Option(
        "data/openalex", "--output", "-o", help="Output directory for metadata"
    ),
    email: Optional[str] = typer.Option(
        None, "--email", "-e", help="Email for polite pool (faster API)"
    ),
    per_page: int = typer.Option(200, "--per-page", help="Results per page (max 200)"),
):
    """Fetch metadata from OpenAlex API.

    Example:
        rag-pipeline fetch-metadata --filter "primary_topic.id:t10856,open_access.is_oa:true"
    """
    from .openalex.config import OpenAlexConfig
    from .openalex.fetcher import MetadataFetcher

    # Parse filters into dictionary
    filter_dict = {}
    if filters:
        for filter_pair in filters.split(","):
            if ":" in filter_pair:
                key, value = filter_pair.split(":", 1)
                filter_dict[key.strip()] = value.strip()

    console.print("[bold blue]Fetching metadata from OpenAlex[/bold blue]")
    console.print(f"[dim]Filters: {filter_dict}[/dim]")

    config = OpenAlexConfig(
        email=email,
        per_page=per_page,
        output_dir=output_dir,
        filters=filter_dict,
    )

    fetcher = MetadataFetcher(config)

    try:
        df = fetcher.run()

        console.print(f"\n[bold green]✓ Successfully fetched {len(df)} works![/bold green]")
        console.print(f"[dim]Saved to: {config.parquet_path}[/dim]")

        # Show summary
        table = Table(title="Fetch Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Works", str(len(df)))
        table.add_row("With PDFs", str(df["has_any_pdf"].sum() if "has_any_pdf" in df else "N/A"))
        table.add_row("Open Access", str(df["is_oa"].sum() if "is_oa" in df else "N/A"))

        if "oa_status" in df:
            oa_counts = df["oa_status"].value_counts()
            top_3_oa = oa_counts.head(3)
            table.add_row(
                "Top OA Status",
                f"{top_3_oa.index[0]}: {top_3_oa.iloc[0]}" if len(top_3_oa) > 0 else "N/A",
            )

        console.print(table)

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        logger.exception("Fatal error during fetch")
        raise typer.Exit(1)


@app.command()
def download_pdfs(
    metadata_file: Path = typer.Argument(..., help="Path to metadata parquet file"),
    output_dir: Path = typer.Option(
        "data/openalex/pdfs", "--output", "-o", help="Output directory for PDFs"
    ),
    max_pdfs: Optional[int] = typer.Option(
        None, "--max", "-m", help="Maximum number of PDFs to download"
    ),
    workers: int = typer.Option(5, "--workers", "-w", help="Number of concurrent downloads"),
    only_with_pdfs: bool = typer.Option(
        True, "--only-with-pdfs/--all", help="Only download works that have PDFs available"
    ),
    scihub_fallback: bool = typer.Option(
        False,
        "--scihub-fallback/--no-scihub-fallback",
        help="Attempt Sci-Hub fallback when PDF download fails or is unavailable",
    ),
    scihub_url: str = typer.Option(
        "https://sci-hub.ru/",
        "--scihub-url",
        help="Sci-Hub base URL to use for fallback downloads",
    ),
):
    """Download PDFs from OpenAlex metadata."""

    console.print(f"[bold blue]Downloading PDFs from:[/bold blue] {metadata_file}")

    if not metadata_file.exists():
        console.print(f"[bold red]✗ Error:[/bold red] Metadata file not found: {metadata_file}")
        raise typer.Exit(1)

    config = OpenAlexConfig(
        output_dir=output_dir.parent if output_dir.name == "pdfs" else output_dir,
        enable_scihub_fallback=scihub_fallback,
        scihub_base_url=scihub_url,
    )

    downloader = PDFDownloader(config)

    try:
        # Filter for works with PDFs if requested
        filter_func = None
        if only_with_pdfs:
            console.print("[dim]Filtering for works with PDFs...[/dim]")

            def filter_func(df):
                return df["has_any_pdf"]

        # Download PDFs with specified number of workers
        # Note: max_pdfs option is not yet implemented
        stats = downloader.download_from_parquet(
            metadata_file, filter_func=filter_func, workers=workers
        )

        console.print("\n[bold green]✓ Download complete![/bold green]")
        console.print(f"[dim]Saved to: {config.pdfs_dir}[/dim]")

        # Show summary
        table = Table(title="Download Summary")
        table.add_column("Status", style="cyan")
        table.add_column("Count", style="green")

        table.add_row("Successful", str(stats.pdfs_downloaded))
        table.add_row("Failed", str(stats.pdfs_failed))
        table.add_row("Skipped", str(stats.pdfs_skipped))
        table.add_row("Total", str(stats.total_works))

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        logger.exception("Fatal error during download")
        raise typer.Exit(1)


@app.command()
def parse_pdfs(
    input_dir: Path = typer.Argument(..., help="Directory containing PDFs"),
    output_dir: Path = typer.Option(
        "data/parsed", "--output", "-o", help="Output directory for parsed markdown"
    ),
    model_path: str = typer.Option("ByteDance/Dolphin", "--model", "-m", help="Dolphin model path"),
    device: str = typer.Option("cuda", "--device", "-d", help="Device to use (cuda, cpu, mps)"),
):
    """Parse PDFs to markdown using Dolphin model."""
    from .pdf_parsing.model.dolphin import DolphinModel
    from .pdf_parsing.core.pipeline import PDFParsingPipeline

    console.print(f"[bold blue]Parsing PDFs from:[/bold blue] {input_dir}")
    console.print(f"[dim]Model: {model_path}[/dim]")
    console.print(f"[dim]Device: {device}[/dim]")

    if not input_dir.exists():
        console.print(f"[bold red]✗ Error:[/bold red] Input directory not found: {input_dir}")
        raise typer.Exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize PDF parsing pipeline
    console.print("[yellow]Loading PDF parsing pipeline...[/yellow]")
    from .pdf_parsing.config import PDFParsingConfig, DolphinModelConfig, OutputConfig
    from pathlib import Path as PathLib

    config = PDFParsingConfig(
        model=DolphinModelConfig(model_path=PathLib(model_path)),
        output=OutputConfig(output_dir=output_dir)
    )
    pipeline = PDFParsingPipeline(config)

    pdf_files = list(input_dir.glob("*.pdf"))

    if not pdf_files:
        console.print(f"[bold red]✗ No PDF files found in {input_dir}[/bold red]")
        raise typer.Exit(1)

    console.print(f"[dim]Found {len(pdf_files)} PDF files[/dim]")

    # Process PDFs
    successful = 0
    failed = 0

    with console.status("[bold green]Processing PDFs...") as status:
        for pdf_path in pdf_files:
            try:
                status.update(f"[bold green]Processing: {pdf_path.name}")

                # Parse PDF with pipeline
                pipeline.parse_document(pdf_path)

                successful += 1
                console.print(f"[green]✓[/green] {pdf_path.name}")

            except Exception as e:
                failed += 1
                console.print(f"[red]✗[/red] {pdf_path.name}: {str(e)}")

    # Summary
    table = Table(title="Parsing Summary")
    table.add_column("Status", style="cyan")
    table.add_column("Count", style="green")

    table.add_row("Successful", str(successful))
    table.add_row("Failed", str(failed))
    table.add_row("Total", str(len(pdf_files)))

    console.print(table)


@app.command()
def create_embeddings(
    input_dir: Path = typer.Argument(..., help="Directory containing parsed markdown files"),
    output_file: Path = typer.Option(
        "data/embeddings/embeddings.parquet", "--output", "-o", help="Output parquet file"
    ),
    chunk_size: int = typer.Option(1024, "--chunk-size", "-c", help="Chunk size in tokens"),
    chunk_overlap: int = typer.Option(100, "--overlap", help="Overlap between chunks"),
    model: str = typer.Option(
        "text-embedding-3-large", "--model", "-m", help="OpenAI embedding model"
    ),
):
    """Create embeddings from parsed markdown files."""
    from .rag.chunking import DocumentChunker
    from .rag.openai_embedder import OpenAIEmbedder

    console.print(f"[bold blue]Creating embeddings from:[/bold blue] {input_dir}")
    console.print(f"[dim]Model: {model}[/dim]")
    console.print(f"[dim]Chunk size: {chunk_size}, Overlap: {chunk_overlap}[/dim]")

    if not input_dir.exists():
        console.print(f"[bold red]✗ Error:[/bold red] Input directory not found: {input_dir}")
        raise typer.Exit(1)

    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Initialize chunker and embedder
    chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    embedder = OpenAIEmbedder(model=model)

    markdown_files = list(input_dir.glob("*.md"))

    if not markdown_files:
        console.print(f"[bold red]✗ No markdown files found in {input_dir}[/bold red]")
        raise typer.Exit(1)

    console.print(f"[dim]Found {len(markdown_files)} markdown files[/dim]")

    # Process files
    all_chunks = []

    with console.status("[bold green]Creating chunks and embeddings...") as status:
        for md_file in markdown_files:
            status.update(f"[bold green]Processing: {md_file.name}")

            text = md_file.read_text()
            chunks = chunker.semantic_chunking(text)

            # Add metadata
            for chunk in chunks:
                chunk["source_file"] = md_file.name
                chunk["document_id"] = md_file.stem

            all_chunks.extend(chunks)

    console.print(f"[dim]Created {len(all_chunks)} chunks total[/dim]")

    # Generate embeddings
    console.print("[yellow]Generating embeddings...[/yellow]")
    embeddings_data = embedder.generate_chunks_with_embeddings(all_chunks)

    # Save to parquet
    import pandas as pd

    df = pd.DataFrame(embeddings_data)
    df.to_parquet(output_file)

    console.print("\n[bold green]✓ Embeddings created successfully![/bold green]")
    console.print(f"[dim]Saved to: {output_file}[/dim]")


@app.command()
def info():
    """Show information about the RAG pipeline."""

    console.print("[bold cyan]RAG Pipeline Information[/bold cyan]\n")

    table = Table(show_header=False, box=None)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Version", "0.1.0")
    table.add_row("Python Package", "rag-pipeline")
    table.add_row("", "")
    table.add_row("Components", "")
    table.add_row("  - OpenAlex Fetcher", "✓")
    table.add_row("  - Dolphin Parser", "✓")
    table.add_row("  - Embeddings", "✓ (OpenAI)")
    table.add_row("  - Vector DB", "Weaviate/Pinecone")

    console.print(table)


if __name__ == "__main__":
    app()
