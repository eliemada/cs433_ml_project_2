"""Utility functions for OpenAlex fetcher."""

import re
from pathlib import Path
from typing import Optional

from loguru import logger


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Create a safe filename from a string.

    Args:
        filename: Original filename
        max_length: Maximum length for the filename

    Returns:
        Sanitized filename safe for filesystem
    """
    # Remove or replace invalid characters
    invalid_chars = r'<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")

    # Replace multiple spaces/underscores with single underscore
    filename = re.sub(r"[_\s]+", "_", filename)

    # Remove leading/trailing whitespace and underscores
    filename = filename.strip(" _")

    # Truncate if too long (leave room for extension)
    if len(filename) > max_length:
        filename = filename[:max_length]

    # Ensure not empty
    if not filename:
        filename = "untitled"

    return filename


def create_pdf_filename(
    index: int, openalex_id: str, title: Optional[str], max_length: int = 200
) -> str:
    """
    Create a standardized PDF filename.

    Format: {index:05d}_{openalex_id}_{sanitized_title}.pdf

    Args:
        index: Sequential index number
        openalex_id: OpenAlex work ID
        title: Work title
        max_length: Maximum length for title portion

    Returns:
        Standardized filename
    """
    # Calculate space available for title
    prefix = f"{index:05d}_{openalex_id}_"
    available_length = max_length - len(prefix) - 4  # 4 for ".pdf"

    # Sanitize and truncate title
    safe_title = sanitize_filename(title or "untitled", max_length=available_length)

    return f"{prefix}{safe_title}.pdf"


def format_bytes(bytes_size: int) -> str:
    """
    Format bytes to human-readable string.

    Args:
        bytes_size: Size in bytes

    Returns:
        Formatted string (e.g., "1.23 MB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "1h 23m 45s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes = int(seconds // 60)
    seconds = int(seconds % 60)

    if minutes < 60:
        return f"{minutes}m {seconds}s"

    hours = minutes // 60
    minutes = minutes % 60

    return f"{hours}h {minutes}m {seconds}s"


def setup_logging(log_level: str = "INFO", log_file: Optional[Path] = None) -> None:
    """
    Configure Loguru logging.

    Args:
        log_level: Logging level
        log_file: Optional log file path
    """
    # Remove default handler
    logger.remove()

    # Add console handler with custom format
    logger.add(
        sink=lambda msg: print(msg, end=""),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=log_level,
        colorize=True,
    )

    # Add file handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            sink=log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
            level=log_level,
            rotation="10 MB",
            retention="1 week",
            compression="zip",
        )

    logger.info(f"Logging initialized at {log_level} level")
    if log_file:
        logger.info(f"Log file: {log_file}")


def validate_pdf_content(content_type: str, url: str) -> bool:
    """
    Validate that content type indicates a PDF.

    Args:
        content_type: Content-Type header value
        url: URL being checked (for extension checking)

    Returns:
        True if content appears to be PDF, False otherwise
    """
    # Check content type
    if "pdf" in content_type.lower():
        return True

    # Check URL extension as fallback
    if url.lower().endswith(".pdf"):
        return True

    return False


def extract_openalex_id(openalex_url: str) -> str:
    """
    Extract short ID from OpenAlex URL.

    Args:
        openalex_url: Full OpenAlex URL (e.g., https://openalex.org/W123456789)

    Returns:
        Short ID (e.g., W123456789)
    """
    return openalex_url.split("/")[-1] if openalex_url else ""


def calculate_progress_eta(current: int, total: int, elapsed_seconds: float) -> tuple[float, float]:
    """
    Calculate progress percentage and estimated time remaining.

    Args:
        current: Current progress count
        total: Total items
        elapsed_seconds: Time elapsed so far

    Returns:
        Tuple of (percentage_complete, eta_seconds)
    """
    if total == 0:
        return 0.0, 0.0

    percentage = (current / total) * 100

    if current == 0:
        return 0.0, 0.0

    rate = current / elapsed_seconds
    remaining = total - current
    eta = remaining / rate if rate > 0 else 0.0

    return percentage, eta
