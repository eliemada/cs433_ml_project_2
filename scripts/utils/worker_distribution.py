"""Worker distribution utilities for parallel PDF processing."""

from typing import List
from pathlib import Path


def get_worker_pdfs(all_pdfs: List[str], worker_id: int, total_workers: int) -> List[str]:
    """
    Get the list of PDFs assigned to a specific worker using modulo distribution.

    Args:
        all_pdfs: List of all PDF keys
        worker_id: ID of this worker (0-indexed)
        total_workers: Total number of parallel workers

    Returns:
        List of PDF keys assigned to this worker
    """
    worker_pdfs = []

    for i, pdf in enumerate(all_pdfs):
        if i % total_workers == worker_id:
            worker_pdfs.append(pdf)

    return worker_pdfs


def extract_pdf_id(pdf_path: str) -> str:
    """
    Extract PDF ID from filename.

    The ID is the first two underscore-separated parts of the filename.
    Example: '00002_W2122361802_Navigating_the_Patent_Thicket.pdf' -> '00002_W2122361802'

    Args:
        pdf_path: PDF file path or key

    Returns:
        PDF ID (e.g., '00002_W2122361802')
    """
    # Get just the filename, not the full path
    filename = Path(pdf_path).name

    # Remove .pdf extension
    name_without_ext = filename.replace(".pdf", "")

    # Split by underscore and take first two parts
    parts = name_without_ext.split("_")
    if len(parts) >= 2:
        return f"{parts[0]}_{parts[1]}"

    # Fallback: return the whole name if pattern doesn't match
    return name_without_ext


def get_output_key(pdf_key: str, input_prefix: str, output_prefix: str) -> str:
    """
    Convert PDF S3 key to markdown output key.

    Creates folder structure: processed/{PDF_ID}/document.md

    Args:
        pdf_key: S3 key of PDF file (e.g., 'raw_pdfs/00002_W2122361802_Title.pdf')
        input_prefix: Prefix to remove (e.g., 'raw_pdfs/')
        output_prefix: Prefix to add (e.g., 'processed/')

    Returns:
        Output key: 'processed/00002_W2122361802/document.md'
    """
    # Extract PDF ID from filename
    pdf_id = extract_pdf_id(pdf_key)

    # Create output path: {output_prefix}/{pdf_id}/document.md
    return f"{output_prefix}{pdf_id}/document.md"
