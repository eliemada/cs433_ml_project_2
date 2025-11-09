"""Worker distribution utilities for parallel PDF processing."""

from typing import List


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


def get_output_key(pdf_key: str, input_prefix: str, output_prefix: str) -> str:
    """
    Convert PDF S3 key to markdown output key.

    Args:
        pdf_key: S3 key of PDF file (e.g., 'pdfs/paper.pdf')
        input_prefix: Prefix to remove (e.g., 'pdfs/')
        output_prefix: Prefix to add (e.g., 'processed/')

    Returns:
        Output key with .md extension
    """
    # Remove input prefix
    relative_path = pdf_key.removeprefix(input_prefix)

    # Replace .pdf with .md
    markdown_path = relative_path.replace('.pdf', '.md')

    # Add output prefix
    return output_prefix + markdown_path
