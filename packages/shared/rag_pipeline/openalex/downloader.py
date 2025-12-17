"""PDF downloader service for OpenAlex works."""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import List, Optional, Callable

import pandas as pd
import requests
from loguru import logger

from .config import OpenAlexConfig
from .models import DownloadStats, OpenAlexWork
from .utils import (
    create_pdf_filename,
    validate_pdf_content,
    format_duration,
    calculate_progress_eta,
    format_bytes,
)
from .test import PdfNotFoundError, download_from_scihub


class PDFDownloader:
    """Downloads PDFs from OpenAlex works data."""

    def __init__(self, config: OpenAlexConfig):
        """
        Initialize the PDF downloader.

        Args:
            config: OpenAlex configuration object
        """
        self.config = config
        self.session = requests.Session()

        # Use realistic browser headers to avoid 403 Forbidden errors
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
            }
        )
        self.stats = DownloadStats()
        self.stats_lock = Lock()  # Thread-safe stats updates

    def download_pdf(self, url: str, filepath: Path, work_id: str) -> bool:
        """
        Download a single PDF from URL.

        Args:
            url: PDF URL
            filepath: Destination file path
            work_id: OpenAlex work ID for logging

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.debug(f"Downloading PDF from {url}")

            # Add referer for the specific request to look more like a browser
            from urllib.parse import urlparse

            parsed_url = urlparse(url)
            referer = f"{parsed_url.scheme}://{parsed_url.netloc}/"

            response = self.session.get(
                url,
                stream=True,
                timeout=self.config.request_timeout,
                allow_redirects=True,
                headers={
                    "Referer": referer,
                },
            )
            response.raise_for_status()

            # Validate content type
            content_type = response.headers.get("content-type", "")
            if self.config.validate_pdf_content_type:
                if not validate_pdf_content(content_type, url):
                    logger.warning(f"Invalid content type: {content_type} for {work_id}")
                    return False

            # Save PDF
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            # Verify file was written
            if not filepath.exists() or filepath.stat().st_size == 0:
                logger.error(f"Failed to write PDF file: {filepath}")
                return False

            logger.debug(f"Successfully downloaded {format_bytes(filepath.stat().st_size)}")
            return True

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout downloading {work_id}: {url}")
            return False
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.warning(f"403 Forbidden (blocked): {work_id} - URL: {url[:80]}...")
            elif e.response.status_code == 404:
                logger.debug(f"404 Not Found: {work_id}")
            else:
                logger.warning(f"HTTP {e.response.status_code}: {work_id} - {url[:80]}...")
            return False
        except requests.exceptions.RequestException as e:
            logger.warning(f"Download error for {work_id}: {e}")
            return False
        except IOError as e:
            logger.error(f"File write error for {work_id}: {e}")
            return False

    def save_metadata(self, work: OpenAlexWork, metadata_file: Path) -> None:
        """
        Save work metadata as JSON.

        Args:
            work: OpenAlex work object
            metadata_file: Destination file path
        """
        try:
            with open(metadata_file, "w") as f:
                json.dump(work.model_dump(), f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save metadata for {work.openalex_id}: {e}")

    def download_work(self, work: OpenAlexWork, index: int, skip_delay: bool = False) -> bool:
        """
        Download PDF for a single work.

        Args:
            work: OpenAlex work object
            index: Sequential index for the work
            skip_delay: Skip download delay (for multi-threaded mode)

        Returns:
            True if successful, False otherwise
        """
        pdf_url = work.best_pdf_url
        can_use_scihub = self._can_use_scihub(work)

        if not pdf_url and not can_use_scihub:
            logger.debug(f"[{index:5d}] No PDF URL available: {work.openalex_id}")
            return False

        # Create filename
        filename = create_pdf_filename(
            index=index,
            openalex_id=work.openalex_id,
            title=work.title or work.display_name,
            max_length=self.config.max_filename_length,
        )
        filepath = self.config.pdfs_dir / filename

        # Skip if already exists
        if self.config.skip_existing_pdfs and filepath.exists():
            logger.debug(f"[{index:5d}] ⏭️  Already exists: {filename}")
            with self.stats_lock:
                self.stats.pdfs_skipped += 1
            return True

        with self.stats_lock:
            self.stats.pdfs_found += 1

        if pdf_url:
            success = self.download_pdf(pdf_url, filepath, work.openalex_id)

            if success:
                logger.info(f"[{index:5d}] ✅ {filename}")
                self._record_success(work, index, skip_delay)
                return True

            logger.debug(
                f"[{index:5d}] Direct download failed, trying fallback if enabled: {work.openalex_id}"
            )
        else:
            logger.debug(f"[{index:5d}] No direct PDF URL, checking fallback: {work.openalex_id}")

        if can_use_scihub:
            fallback_success = self.download_via_scihub(work, filepath, index, filename, skip_delay)
            if fallback_success:
                return True

        with self.stats_lock:
            self.stats.pdfs_failed += 1
        logger.debug(f"[{index:5d}] ❌ Failed: {work.openalex_id}")
        return False

    def _record_success(self, work: OpenAlexWork, index: int, skip_delay: bool = False) -> None:
        """Update stats/metadata bookkeeping after a successful download."""
        with self.stats_lock:
            self.stats.pdfs_downloaded += 1

        if self.config.save_individual_metadata:
            metadata_file = self.config.metadata_dir / f"{index:05d}_{work.openalex_id}.json"
            self.save_metadata(work, metadata_file)

        # Skip delay when using multiple workers for max speed
        if not skip_delay:
            time.sleep(self.config.download_delay)

    def _can_use_scihub(self, work: OpenAlexWork) -> bool:
        """Determine if Sci-Hub fallback is allowed for this work."""
        return self.config.enable_scihub_fallback and bool(work.doi)

    def download_via_scihub(
        self,
        work: OpenAlexWork,
        filepath: Path,
        index: int,
        filename: str,
        skip_delay: bool = False,
    ) -> bool:
        """Attempt to fetch the PDF via Sci-Hub fallback."""
        if not work.doi:
            return False

        logger.info(f"[{index:5d}] 🔁 Sci-Hub fallback for {work.openalex_id} ({work.doi})")

        try:
            download_from_scihub(
                doi=work.doi,
                output_path=filepath,
                scihub_url=self.config.scihub_base_url,
                log_hook=lambda msg: logger.debug(f"[Sci-Hub:{work.openalex_id}] {msg}"),
            )
            logger.info(f"[{index:5d}] ✅ Sci-Hub: {filename}")
            self._record_success(work, index, skip_delay)
            return True
        except PdfNotFoundError as e:
            logger.warning(f"Sci-Hub PDF not available for {work.doi}: {e}")
        except Exception as e:
            logger.warning(f"Sci-Hub fallback failed for {work.doi}: {e}")

        return False

    def download_from_works_list(
        self, works: List[OpenAlexWork], workers: int = 1
    ) -> DownloadStats:
        """
        Download PDFs from a list of OpenAlexWork objects.

        Args:
            works: List of OpenAlexWork objects
            workers: Number of concurrent download threads (default: 1)

        Returns:
            Download statistics
        """
        from rich.progress import (
            Progress,
            SpinnerColumn,
            BarColumn,
            TextColumn,
            TimeRemainingColumn,
        )

        logger.info("=" * 80)
        logger.info("Starting PDF Downloads")
        logger.info("=" * 80)
        logger.info(f"Total works: {len(works)}")
        logger.info(f"Workers: {workers}")
        logger.info(f"Output directory: {self.config.pdfs_dir}")
        logger.info("")

        self.stats.total_works = len(works)
        start_time = datetime.now()
        skip_delay = workers > 1  # Skip delays when using multiple workers

        # Sequential mode (workers = 1)
        if workers == 1:
            for index, work in enumerate(works, 1):
                try:
                    self.download_work(work, index, skip_delay=False)

                    # Progress update every 50 works
                    if index % 50 == 0:
                        elapsed = (datetime.now() - start_time).total_seconds()
                        pct, eta = calculate_progress_eta(index, len(works), elapsed)
                        logger.info(
                            f"Progress: {index}/{len(works)} ({pct:.1f}%) | "
                            f"Downloaded: {self.stats.pdfs_downloaded} | "
                            f"Failed: {self.stats.pdfs_failed} | "
                            f"ETA: {format_duration(eta)}"
                        )

                except KeyboardInterrupt:
                    logger.warning("Download interrupted by user")
                    break
                except Exception as e:
                    logger.error(f"Unexpected error for work {index}: {e}")
                    continue

        # Parallel mode (workers > 1)
        else:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total})"),
                TimeRemainingColumn(),
            ) as progress:
                task = progress.add_task(
                    f"[cyan]Downloading with {workers} workers...", total=len(works)
                )

                with ThreadPoolExecutor(max_workers=workers) as executor:
                    # Submit all download tasks
                    future_to_work = {
                        executor.submit(self.download_work, work, index, skip_delay): (index, work)
                        for index, work in enumerate(works, 1)
                    }

                    try:
                        # Process completions
                        for future in as_completed(future_to_work):
                            index, work = future_to_work[future]
                            try:
                                future.result()
                            except Exception as e:
                                logger.error(f"Unexpected error for work {index}: {e}")

                            # Update progress
                            progress.update(task, advance=1)

                            # Update progress description with stats
                            progress.update(
                                task,
                                description=f"[cyan]Downloaded: {self.stats.pdfs_downloaded} | "
                                f"Failed: {self.stats.pdfs_failed} | "
                                f"Skipped: {self.stats.pdfs_skipped}",
                            )

                    except KeyboardInterrupt:
                        logger.warning("\nDownload interrupted by user. Shutting down workers...")
                        executor.shutdown(wait=False, cancel_futures=True)
                        raise

        self.stats.end_time = datetime.now()
        return self.stats

    def download_from_parquet(
        self, parquet_file: Path, filter_func: Optional[Callable] = None, workers: int = 1
    ) -> DownloadStats:
        """
        Download PDFs from a parquet file.

        Args:
            parquet_file: Path to parquet file
            filter_func: Optional function to filter DataFrame
            workers: Number of concurrent download threads (default: 1)

        Returns:
            Download statistics
        """
        logger.info(f"Loading works from {parquet_file}...")
        df = pd.read_parquet(parquet_file)
        logger.success(f"✅ Loaded {len(df)} works")

        # Apply filter if provided
        if filter_func:
            logger.info("Applying filter...")
            df = df[filter_func(df)]
            logger.info(f"✅ Filtered to {len(df)} works")

        # Convert to OpenAlexWork objects
        logger.info("Parsing work objects...")
        works = []

        for _, row in df.iterrows():
            try:
                # If full_json is available, use it
                if "full_json" in row and pd.notna(row["full_json"]):
                    work_data = json.loads(row["full_json"])
                    work = OpenAlexWork(**work_data)
                else:
                    # Reconstruct from flat data (limited information)
                    # This is a simplified reconstruction
                    logger.warning("No full_json available, using limited reconstruction")
                    work = self._reconstruct_work_from_row(row)

                works.append(work)
            except Exception as e:
                logger.warning(f"Failed to parse work {row.get('openalex_id', 'unknown')}: {e}")

        logger.success(f"✅ Parsed {len(works)} work objects")

        # Download PDFs
        return self.download_from_works_list(works, workers=workers)

    def _reconstruct_work_from_row(self, row: pd.Series) -> OpenAlexWork:
        """
        Reconstruct OpenAlexWork from flat DataFrame row.

        This provides limited information compared to full JSON.

        Args:
            row: DataFrame row

        Returns:
            OpenAlexWork object
        """
        from .models import OpenAccess, Location, Source

        # Build best OA location
        best_oa_location = None
        if pd.notna(row.get("best_oa_pdf_url")):
            best_oa_location = Location(
                is_oa=True,
                pdf_url=row.get("best_oa_pdf_url"),
                landing_page_url=row.get("best_oa_landing_page"),
                version=row.get("best_oa_version"),
                license=row.get("best_oa_license"),
                source=Source(
                    display_name=row.get("best_oa_source"), type=row.get("best_oa_source_type")
                )
                if pd.notna(row.get("best_oa_source"))
                else None,
            )

        # Build primary location
        primary_location = None
        if pd.notna(row.get("primary_pdf_url")):
            primary_location = Location(
                is_oa=row.get("is_oa", False),
                pdf_url=row.get("primary_pdf_url"),
                landing_page_url=row.get("primary_landing_page"),
                version=row.get("primary_version"),
                license=row.get("primary_license"),
                source=Source(
                    display_name=row.get("primary_source"), type=row.get("primary_source_type")
                )
                if pd.notna(row.get("primary_source"))
                else None,
            )

        # Build work
        return OpenAlexWork(
            id=row.get("id", row.get("openalex_url", "")),
            doi=row.get("doi") if pd.notna(row.get("doi")) else None,
            title=row.get("title"),
            publication_year=int(row.get("publication_year"))
            if pd.notna(row.get("publication_year"))
            else None,
            publication_date=row.get("publication_date")
            if pd.notna(row.get("publication_date"))
            else None,
            type=row.get("type"),
            open_access=OpenAccess(
                is_oa=row.get("is_oa", False),
                oa_status=row.get("oa_status"),
                oa_url=row.get("oa_url") if pd.notna(row.get("oa_url")) else None,
                any_repository_has_fulltext=row.get("any_repository_has_fulltext", False),
            ),
            best_oa_location=best_oa_location,
            primary_location=primary_location,
            cited_by_count=int(row.get("cited_by_count", 0)),
            is_retracted=row.get("is_retracted", False),
            is_paratext=row.get("is_paratext", False),
            language=row.get("language") if pd.notna(row.get("language")) else None,
        )

    def print_stats(self) -> None:
        """Print download statistics."""
        logger.info("")
        logger.info("=" * 80)
        logger.info("Download Statistics")
        logger.info("=" * 80)
        logger.info(f"Total works:            {self.stats.total_works:,}")
        logger.info(f"PDFs found:             {self.stats.pdfs_found:,}")
        logger.info(f"PDFs downloaded:        {self.stats.pdfs_downloaded:,}")
        logger.info(f"PDFs skipped (exists):  {self.stats.pdfs_skipped:,}")
        logger.info(f"PDFs failed:            {self.stats.pdfs_failed:,}")
        logger.info(f"Success rate:           {self.stats.success_rate:.1f}%")
        logger.info(f"Duration:               {format_duration(self.stats.duration_seconds)}")
        logger.info("=" * 80)

    def save_stats(self) -> None:
        """Save download statistics to JSON."""
        stats_file = self.config.output_dir / "download_stats.json"
        with open(stats_file, "w") as f:
            json.dump(self.stats.model_dump(mode="json"), f, indent=2, default=str)
        logger.success(f"✅ Statistics saved to {stats_file}")

    def run(
        self, parquet_file: Optional[Path] = None, filter_func: Optional[Callable] = None
    ) -> DownloadStats:
        """
        Run the complete PDF download pipeline.

        Args:
            parquet_file: Path to parquet file (uses config default if None)
            filter_func: Optional function to filter DataFrame

        Returns:
            Download statistics
        """
        # Create directories
        self.config.create_directories()

        # Use default parquet file if not specified
        if parquet_file is None:
            parquet_file = self.config.parquet_path

        if not parquet_file.exists():
            logger.error(f"Parquet file not found: {parquet_file}")
            logger.error("Please run metadata fetch first!")
            return self.stats

        # Download PDFs
        self.download_from_parquet(parquet_file, filter_func)

        # Print and save stats
        self.print_stats()
        self.save_stats()

        return self.stats
