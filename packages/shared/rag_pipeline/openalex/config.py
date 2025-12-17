"""Configuration management using Pydantic Settings."""

from pathlib import Path
from typing import Dict, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAlexConfig(BaseSettings):
    """Configuration for OpenAlex fetcher."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="OPENALEX_",
        case_sensitive=False,
    )

    # API Configuration
    api_base_url: str = Field(
        default="https://api.openalex.org/works",
        description="Base URL for OpenAlex API"
    )

    email: Optional[str] = Field(
        default=None,
        description="Email for polite pool (faster API access)"
    )

    # Rate Limiting
    request_delay: float = Field(
        default=0.1,
        ge=0.0,
        le=5.0,
        description="Delay between API requests in seconds"
    )

    download_delay: float = Field(
        default=0.5,
        ge=0.0,
        le=10.0,
        description="Delay between PDF downloads in seconds"
    )

    # Pagination
    per_page: int = Field(
        default=200,
        ge=1,
        le=200,
        description="Number of results per page (max 200)"
    )

    # Output Configuration
    output_dir: Path = Field(
        default=Path("openalex_data"),
        description="Base output directory for all data"
    )

    pdfs_dir_name: str = Field(
        default="pdfs",
        description="Subdirectory name for PDFs"
    )

    metadata_dir_name: str = Field(
        default="metadata",
        description="Subdirectory name for metadata JSON files"
    )

    parquet_filename: str = Field(
        default="openalex_works.parquet",
        description="Filename for the main parquet file"
    )

    # Filtering
    filters: Dict[str, str] = Field(
        default_factory=lambda: {
            "primary_topic.id": "t10856",
            "open_access.is_oa": "true"
        },
        description="OpenAlex API filters"
    )

    # Download Options
    save_individual_metadata: bool = Field(
        default=True,
        description="Save individual JSON metadata files alongside PDFs"
    )

    include_full_json_in_parquet: bool = Field(
        default=True,
        description="Include full JSON in parquet file"
    )

    skip_existing_pdfs: bool = Field(
        default=True,
        description="Skip downloading PDFs that already exist"
    )

    enable_scihub_fallback: bool = Field(
        default=False,
        description="Use Sci-Hub fallback when PDF download fails or no PDF URL is available"
    )

    scihub_base_url: str = Field(
        default="https://sci-hub.ru/",
        description="Base URL for Sci-Hub fallback downloads"
    )

    # Parquet Options
    parquet_compression: str = Field(
        default="snappy",
        description="Compression algorithm for parquet (snappy, gzip, brotli, zstd)"
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )

    log_file: Optional[Path] = Field(
        default=None,
        description="Log file path (None for stdout only)"
    )

    # Validation
    validate_pdf_content_type: bool = Field(
        default=True,
        description="Check Content-Type header to ensure it's a PDF"
    )

    max_filename_length: int = Field(
        default=200,
        ge=50,
        le=255,
        description="Maximum length for PDF filenames"
    )

    # Timeouts
    request_timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Timeout for HTTP requests in seconds"
    )

    @field_validator("output_dir", mode="before")
    @classmethod
    def validate_output_dir(cls, v):
        """Convert string to Path if needed."""
        if isinstance(v, str):
            return Path(v)
        return v

    @field_validator("log_file", mode="before")
    @classmethod
    def validate_log_file(cls, v):
        """Convert string to Path if needed."""
        if v and isinstance(v, str):
            return Path(v)
        return v

    @property
    def pdfs_dir(self) -> Path:
        """Get full path to PDFs directory."""
        return self.output_dir / self.pdfs_dir_name

    @property
    def metadata_dir(self) -> Path:
        """Get full path to metadata directory."""
        return self.output_dir / self.metadata_dir_name

    @property
    def parquet_path(self) -> Path:
        """Get full path to parquet file."""
        return self.output_dir / self.parquet_filename

    @property
    def filter_string(self) -> str:
        """Get formatted filter string for API."""
        return ",".join([f"{k}:{v}" for k, v in self.filters.items()])

    def create_directories(self) -> None:
        """Create all necessary output directories."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.pdfs_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def get_api_params(self, cursor: str = "*") -> Dict[str, any]:
        """Get API request parameters."""
        params = {
            "filter": self.filter_string,
            "per-page": self.per_page,
            "cursor": cursor
        }

        if self.email:
            params["mailto"] = self.email

        return params
