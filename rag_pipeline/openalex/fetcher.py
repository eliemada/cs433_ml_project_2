"""Metadata fetcher service for OpenAlex API."""

import time
from datetime import datetime
from typing import List, Optional

import pandas as pd
import requests
from loguru import logger
from pydantic import ValidationError

from .config import OpenAlexConfig
from .models import OpenAlexWork, FlatWork
from .utils import format_duration


class MetadataFetcher:
    """Fetches metadata from OpenAlex API and saves to Parquet."""

    def __init__(self, config: OpenAlexConfig):
        """
        Initialize the metadata fetcher.

        Args:
            config: OpenAlex configuration object
        """
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"OpenAlexFetcher/1.0 ({config.email or 'no-email-provided'})"
        })

    def fetch_page(self, cursor: str = "*") -> tuple[List[dict], Optional[str]]:
        """
        Fetch a single page of results from OpenAlex API.

        Args:
            cursor: Cursor for pagination

        Returns:
            Tuple of (results list, next_cursor)

        Raises:
            requests.exceptions.RequestException: If API request fails
        """
        params = self.config.get_api_params(cursor=cursor)

        logger.debug(f"Fetching page with cursor: {cursor[:20]}...")

        response = self.session.get(
            self.config.api_base_url,
            params=params,
            timeout=self.config.request_timeout
        )
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])
        meta = data.get("meta", {})
        next_cursor = meta.get("next_cursor")

        return results, next_cursor

    def fetch_all_works(self) -> List[OpenAlexWork]:
        """
        Fetch all works matching the configured filters.

        Returns:
            List of OpenAlexWork objects

        Raises:
            requests.exceptions.RequestException: If API request fails
        """
        all_works: List[OpenAlexWork] = []
        cursor = "*"
        page = 0
        start_time = datetime.now()

        logger.info("Starting metadata fetch from OpenAlex API")
        logger.info(f"Filters: {self.config.filter_string}")
        logger.info(f"Results per page: {self.config.per_page}")

        while cursor:
            page += 1

            try:
                # Fetch page
                results, next_cursor = self.fetch_page(cursor)

                # Parse results into Pydantic models
                page_works = []
                for i, result in enumerate(results):
                    try:
                        work = OpenAlexWork(**result)
                        page_works.append(work)
                    except ValidationError as e:
                        logger.warning(
                            f"Failed to parse work on page {page}, item {i}: {e}"
                        )
                        logger.debug(f"Problematic data: {result.get('id', 'unknown')}")

                all_works.extend(page_works)

                # Calculate progress
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = len(all_works) / elapsed if elapsed > 0 else 0

                logger.info(
                    f"📄 Page {page:4d}: {len(page_works):3d} works | "
                    f"Total: {len(all_works):5d} | "
                    f"Rate: {rate:.1f} works/sec | "
                    f"Elapsed: {format_duration(elapsed)}"
                )

                # Update cursor
                cursor = next_cursor

                # Rate limiting
                if cursor:  # Don't delay after last page
                    time.sleep(self.config.request_delay)

                # Stop if no more results
                if not results:
                    logger.info("No more results available")
                    break

            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to fetch page {page}: {e}")
                logger.warning("Stopping pagination due to error")
                break
            except KeyboardInterrupt:
                logger.warning("Fetch interrupted by user")
                break

        total_time = (datetime.now() - start_time).total_seconds()
        logger.success(
            f"✅ Fetched {len(all_works)} works in {format_duration(total_time)}"
        )
        logger.info(f"   Average: {len(all_works)/total_time:.1f} works/sec")

        return all_works

    def works_to_dataframe(
        self,
        works: List[OpenAlexWork],
        include_full_json: bool = True
    ) -> pd.DataFrame:
        """
        Convert list of works to pandas DataFrame.

        Args:
            works: List of OpenAlexWork objects
            include_full_json: Include full JSON in dataframe

        Returns:
            DataFrame with flattened work data
        """
        logger.info(f"Converting {len(works)} works to DataFrame...")

        flat_works = []
        for work in works:
            try:
                flat = FlatWork.from_work(work, include_full_json=include_full_json)
                flat_works.append(flat.model_dump())
            except Exception as e:
                logger.warning(f"Failed to flatten work {work.openalex_id}: {e}")

        df = pd.DataFrame(flat_works)
        logger.success(f"✅ Created DataFrame with {len(df)} rows and {len(df.columns)} columns")

        return df

    def optimize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Optimize DataFrame dtypes for efficient storage.

        Args:
            df: Input DataFrame

        Returns:
            Optimized DataFrame
        """
        logger.info("Optimizing DataFrame dtypes...")

        # Convert numeric columns
        numeric_cols = [
            "publication_year", "cited_by_count", "num_locations",
            "num_pdf_urls", "num_oa_locations", "num_authors",
            "concept_1_score", "concept_2_score", "concept_3_score"
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Convert boolean columns
        bool_cols = [
            "is_retracted", "is_paratext", "is_oa",
            "any_repository_has_fulltext", "has_any_pdf"
        ]
        for col in bool_cols:
            if col in df.columns:
                df[col] = df[col].astype(bool)

        # Convert categorical columns (saves memory)
        categorical_cols = [
            "oa_status", "type", "language", "best_oa_source_type",
            "primary_source_type", "topic_domain", "topic_field"
        ]
        for col in categorical_cols:
            if col in df.columns and df[col].notna().any():
                df[col] = df[col].astype('category')

        logger.success("✅ DataFrame optimization complete")

        return df

    def save_to_parquet(self, df: pd.DataFrame) -> None:
        """
        Save DataFrame to Parquet file.

        Args:
            df: DataFrame to save
        """
        logger.info(f"Saving DataFrame to {self.config.parquet_path}...")

        # Optimize before saving
        df = self.optimize_dataframe(df)

        # Save to parquet
        df.to_parquet(
            self.config.parquet_path,
            index=False,
            compression=self.config.parquet_compression
        )

        # Log file info
        size_bytes = self.config.parquet_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)

        logger.success(f"✅ Saved {len(df)} rows to {self.config.parquet_path}")
        logger.info(f"   File size: {size_mb:.2f} MB")
        logger.info(f"   Columns: {len(df.columns)}")

    def generate_summary_stats(self, df: pd.DataFrame) -> dict:
        """
        Generate summary statistics from DataFrame.

        Args:
            df: DataFrame to analyze

        Returns:
            Dictionary with summary statistics
        """
        stats = {
            "total_works": len(df),
            "date_generated": datetime.now().isoformat(),
        }

        # Open Access breakdown
        if "oa_status" in df.columns:
            stats["oa_status_counts"] = df["oa_status"].value_counts().to_dict()

        # PDF availability
        stats["pdf_availability"] = {
            "works_with_pdf": int(df["has_any_pdf"].sum()) if "has_any_pdf" in df.columns else 0,
            "works_without_pdf": int((~df["has_any_pdf"]).sum()) if "has_any_pdf" in df.columns else 0,
            "works_with_best_oa_pdf": int(df["best_oa_pdf_url"].notna().sum()),
            "works_with_primary_pdf": int(df["primary_pdf_url"].notna().sum()),
        }

        # DOI availability
        if "doi" in df.columns:
            stats["doi_availability"] = {
                "with_doi": int(df["doi"].notna().sum()),
                "without_doi": int(df["doi"].isna().sum()),
            }

        # Publication years
        if "publication_year" in df.columns:
            stats["publication_years"] = {
                "min": int(df["publication_year"].min()) if df["publication_year"].notna().any() else None,
                "max": int(df["publication_year"].max()) if df["publication_year"].notna().any() else None,
                "mean": float(df["publication_year"].mean()) if df["publication_year"].notna().any() else None,
            }

        # Citations
        if "cited_by_count" in df.columns:
            stats["citations"] = {
                "total": int(df["cited_by_count"].sum()),
                "mean": float(df["cited_by_count"].mean()),
                "median": float(df["cited_by_count"].median()),
                "max": int(df["cited_by_count"].max()),
            }

        # Top sources
        if "best_oa_source" in df.columns:
            stats["top_sources"] = df["best_oa_source"].value_counts().head(10).to_dict()

        # Source types
        if "best_oa_source_type" in df.columns:
            stats["source_types"] = df["best_oa_source_type"].value_counts().to_dict()

        return stats

    def save_summary_stats(self, df: pd.DataFrame) -> None:
        """
        Generate and save summary statistics.

        Args:
            df: DataFrame to analyze
        """
        import json

        logger.info("Generating summary statistics...")

        stats = self.generate_summary_stats(df)

        # Save as JSON
        stats_file = self.config.output_dir / "summary_stats.json"
        with open(stats_file, "w") as f:
            json.dump(stats, f, indent=2)

        logger.success(f"✅ Summary statistics saved to {stats_file}")

        # Also save as text for easy reading
        txt_file = self.config.output_dir / "summary_stats.txt"
        with open(txt_file, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("OpenAlex Metadata Summary\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Total works: {stats['total_works']:,}\n")
            f.write(f"Generated: {stats['date_generated']}\n\n")

            # PDF availability
            if "pdf_availability" in stats:
                pdf = stats["pdf_availability"]
                f.write("PDF Availability:\n")
                f.write(f"  Works with PDF URLs:      {pdf['works_with_pdf']:6,} ({pdf['works_with_pdf']/stats['total_works']*100:5.1f}%)\n")
                f.write(f"  Works without PDF URLs:   {pdf['works_without_pdf']:6,} ({pdf['works_without_pdf']/stats['total_works']*100:5.1f}%)\n")
                f.write(f"  Works with best_oa PDF:   {pdf['works_with_best_oa_pdf']:6,} ({pdf['works_with_best_oa_pdf']/stats['total_works']*100:5.1f}%)\n")
                f.write(f"  Works with primary PDF:   {pdf['works_with_primary_pdf']:6,} ({pdf['works_with_primary_pdf']/stats['total_works']*100:5.1f}%)\n\n")

            # OA Status
            if "oa_status_counts" in stats:
                f.write("Open Access Status:\n")
                for status, count in stats["oa_status_counts"].items():
                    f.write(f"  {status:15s}: {count:6,} ({count/stats['total_works']*100:5.1f}%)\n")
                f.write("\n")

            # Citations
            if "citations" in stats:
                cit = stats["citations"]
                f.write("Citations:\n")
                f.write(f"  Total:  {cit['total']:,}\n")
                f.write(f"  Mean:   {cit['mean']:.2f}\n")
                f.write(f"  Median: {cit['median']:.0f}\n")
                f.write(f"  Max:    {cit['max']:,}\n\n")

            # Top sources
            if "top_sources" in stats:
                f.write("Top 10 Open Access Sources:\n")
                for source, count in stats["top_sources"].items():
                    f.write(f"  {source[:50]:50s}: {count:6,}\n")
                f.write("\n")

        logger.success(f"✅ Summary text saved to {txt_file}")

    def run(self) -> pd.DataFrame:
        """
        Run the complete metadata fetching pipeline.

        Returns:
            DataFrame with all works
        """
        logger.info("=" * 80)
        logger.info("OpenAlex Metadata Fetcher")
        logger.info("=" * 80)

        # Create directories
        self.config.create_directories()
        logger.info(f"Output directory: {self.config.output_dir.absolute()}")

        # Fetch all works
        works = self.fetch_all_works()

        if not works:
            logger.warning("No works fetched!")
            return pd.DataFrame()

        # Convert to DataFrame
        df = self.works_to_dataframe(
            works,
            include_full_json=self.config.include_full_json_in_parquet
        )

        # Save to parquet
        self.save_to_parquet(df)

        # Generate and save summary stats
        self.save_summary_stats(df)

        logger.success("=" * 80)
        logger.success("✅ Metadata fetch complete!")
        logger.success("=" * 80)

        return df