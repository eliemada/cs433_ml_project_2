import re
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup


class PdfNotFoundError(Exception):
    pass


DEFAULT_SCIHUB_URL = "https://sci-hub.ru/"


def normalize_doi(raw_doi: str) -> str:
    """
    Accepts either a DOI string or a DOI URL and returns the DOI identifier.
    """
    if not raw_doi:
        return ""

    doi = raw_doi.strip()

    # Remove common prefixes such as "doi:"
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.IGNORECASE)

    # Extract portion after doi.org/ (case-insensitive)
    match = re.search(r"doi\.org/(.+)", doi, flags=re.IGNORECASE)
    if match:
        doi = match.group(1)

    # Drop query/fragment components if present
    doi = doi.split("?", 1)[0]
    doi = doi.split("#", 1)[0]

    return doi.strip().strip("/")


def download_from_scihub(
    doi: str,
    save_dir: str | Path = ".",
    scihub_url: str = DEFAULT_SCIHUB_URL,
    *,
    output_path: Optional[Path] = None,
    timeout: int = 20,
    log_hook: Optional[Callable[[str], None]] = None,
) -> Path:
    """
    Given a DOI, fetches and downloads the corresponding PDF from Sci-Hub.

    Args:
        doi: DOI of the paper to download.
        save_dir: Directory where the PDF should be saved (ignored when ``output_path`` is provided).
        scihub_url: Base Sci-Hub URL to use.
        output_path: Optional explicit file path for the downloaded PDF.
        timeout: Request timeout in seconds.
        log_hook: Optional callable used for logging messages instead of ``print``.

    Returns:
        Path: Location of the downloaded PDF file.

    Raises:
        PdfNotFoundError: If the PDF could not be located or downloaded.
        Exception: For general network or parsing errors.
    """

    def _log(message: str) -> None:
        if log_hook:
            log_hook(message)
        else:
            print(message)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 11_3_1 like Mac OS X) "
            "AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 "
            "Mobile/14E304 Safari/602.1"
        )
    }

    normalized_doi = normalize_doi(doi)
    if not normalized_doi:
        raise ValueError("A DOI or DOI URL must be provided.")

    doi_encoded = quote(normalized_doi)
    full_url = urljoin(scihub_url, doi_encoded)
    _log(f"[*] Fetching page: {full_url}")

    response = requests.get(full_url, headers=headers, timeout=timeout)
    if response.status_code != 200:
        raise Exception(f"Sci-Hub returned HTTP {response.status_code}")

    soup = BeautifulSoup(response.content, "html.parser")

    # Try both old (#pdf iframe) and new (embed src) formats
    pdf_src = None
    iframe = soup.select_one("iframe#pdf")
    embed = soup.select_one("embed#pdf")

    if iframe and iframe.get("src"):
        pdf_src = iframe["src"]
    elif embed and embed.get("src"):
        pdf_src = embed["src"]

    if not pdf_src:
        # Detect if PDF not found or CAPTCHA
        if re.search(r"not found|try again|статья не найдена", soup.text, re.IGNORECASE):
            raise PdfNotFoundError(f"PDF not available for DOI: {doi}")
        raise Exception("Captcha or unknown response from Sci-Hub page.")

    # Fix relative URLs
    if pdf_src.startswith("//"):
        pdf_src = "https:" + pdf_src
    elif not pdf_src.startswith("http"):
        pdf_src = urljoin(scihub_url, pdf_src)

    _log(f"[*] Found PDF: {pdf_src}")

    # Download PDF
    pdf_response = requests.get(pdf_src, headers=headers, stream=True, timeout=timeout)
    if pdf_response.status_code != 200 or "pdf" not in pdf_response.headers.get("Content-Type", ""):
        raise PdfNotFoundError(f"Could not download PDF from {pdf_src}")

    # Determine output location
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        filename = re.sub(r"[^\w\-_.]", "_", normalized_doi) + ".pdf"
        path = save_dir / filename

    # Save file
    with open(path, "wb") as f:
        for chunk in pdf_response.iter_content(1024 * 32):
            f.write(chunk)

    _log(f"[+] PDF saved as: {path}")
    return path


# Example usage
if __name__ == "__main__":
    doi = "10.1371/journal.pbio.1002060"  # Example DOI
    try:
        download_from_scihub(doi)
    except PdfNotFoundError as e:
        print(f"[!] {e}")
    except Exception as e:
        print(f"[X] Error: {e}")
