"""Pydantic models for OpenAlex data structures."""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, field_validator


class OAStatus(str, Enum):
    """Open Access status types."""

    DIAMOND = "diamond"
    GOLD = "gold"
    GREEN = "green"
    HYBRID = "hybrid"
    BRONZE = "bronze"
    CLOSED = "closed"


class SourceType(str, Enum):
    """Source types for publications."""

    JOURNAL = "journal"
    REPOSITORY = "repository"
    PUBLISHER = "publisher"
    CONFERENCE = "conference"
    OTHER = "other"


class Source(BaseModel):
    """Publication source information."""

    id: Optional[str] = None
    display_name: Optional[str] = None
    issn_l: Optional[str] = None
    issn: Optional[List[str]] = None
    host_organization: Optional[str] = None
    type: Optional[str] = None

    class Config:
        use_enum_values = True


class Location(BaseModel):
    """Location where the work is available."""

    is_oa: bool = False
    landing_page_url: Optional[str] = None
    pdf_url: Optional[str] = None
    source: Optional[Source] = None
    license: Optional[str] = None
    version: Optional[str] = None
    is_accepted: bool = False
    is_published: bool = False

    @field_validator("pdf_url", "landing_page_url", mode="before")
    @classmethod
    def validate_url(cls, v):
        """Ensure URLs are valid or None."""
        if v and not v.startswith(("http://", "https://")):
            return None
        return v

    @field_validator("is_oa", "is_accepted", "is_published", mode="before")
    @classmethod
    def validate_bool(cls, v):
        """Convert None to False for boolean fields."""
        if v is None:
            return False
        return v


class OpenAccess(BaseModel):
    """Open access information for a work."""

    is_oa: bool = False
    oa_status: Optional[OAStatus] = None
    oa_url: Optional[str] = None
    any_repository_has_fulltext: bool = False

    @field_validator("is_oa", "any_repository_has_fulltext", mode="before")
    @classmethod
    def validate_bool(cls, v):
        """Convert None to False for boolean fields."""
        if v is None:
            return False
        return v


class Author(BaseModel):
    """Author information."""

    id: Optional[str] = None
    display_name: Optional[str] = None
    orcid: Optional[str] = None


class Authorship(BaseModel):
    """Authorship with author and institutional info."""

    author_position: Optional[str] = None
    author: Optional[Author] = None
    institutions: Optional[List[Dict[str, Any]]] = None
    raw_affiliation_string: Optional[str] = None


class Concept(BaseModel):
    """Concept/topic tag."""

    id: Optional[str] = None
    wikidata: Optional[str] = None
    display_name: Optional[str] = None
    level: Optional[int] = None
    score: Optional[float] = None


class Topic(BaseModel):
    """Primary topic information."""

    id: Optional[str] = None
    display_name: Optional[str] = None
    subfield: Optional[Dict[str, Any]] = None
    field: Optional[Dict[str, Any]] = None
    domain: Optional[Dict[str, Any]] = None


class OpenAlexWork(BaseModel):
    """Complete OpenAlex work object."""

    id: str
    doi: Optional[str] = None
    title: Optional[str] = None
    display_name: Optional[str] = None  # Alias for title
    publication_year: Optional[int] = None
    publication_date: Optional[str] = None
    type: Optional[str] = None
    type_crossref: Optional[str] = None

    # Open Access
    open_access: OpenAccess

    # Locations
    primary_location: Optional[Location] = None
    best_oa_location: Optional[Location] = None
    locations: List[Location] = Field(default_factory=list)

    # Authors and topics
    authorships: List[Authorship] = Field(default_factory=list)
    primary_topic: Optional[Topic] = None
    topics: List[Topic] = Field(default_factory=list)
    concepts: List[Concept] = Field(default_factory=list)

    # Keywords and abstract
    keywords: List[Dict[str, Any]] = Field(default_factory=list)
    abstract_inverted_index: Optional[Dict[str, List[int]]] = None

    # Metrics
    cited_by_count: int = 0
    cited_by_api_url: Optional[str] = None
    counts_by_year: List[Dict[str, Any]] = Field(default_factory=list)

    # Flags
    is_retracted: bool = False
    is_paratext: bool = False

    # Language
    language: Optional[str] = None

    # Related works
    referenced_works: List[str] = Field(default_factory=list)
    related_works: List[str] = Field(default_factory=list)

    # Metadata
    created_date: Optional[str] = None
    updated_date: Optional[str] = None

    class Config:
        use_enum_values = True

    @field_validator("is_retracted", "is_paratext", mode="before")
    @classmethod
    def validate_bool(cls, v):
        """Convert None to False for boolean fields."""
        if v is None:
            return False
        return v

    @property
    def openalex_id(self) -> str:
        """Extract short OpenAlex ID from full URL."""
        return self.id.split("/")[-1] if self.id else ""

    @property
    def has_pdf_url(self) -> bool:
        """Check if any location has a PDF URL."""
        if self.best_oa_location and self.best_oa_location.pdf_url:
            return True
        if self.primary_location and self.primary_location.pdf_url:
            return True
        return any(loc.pdf_url for loc in self.locations)

    @property
    def all_pdf_urls(self) -> List[str]:
        """Get all available PDF URLs."""
        urls = []
        if self.best_oa_location and self.best_oa_location.pdf_url:
            urls.append(self.best_oa_location.pdf_url)
        if self.primary_location and self.primary_location.pdf_url:
            if self.primary_location.pdf_url not in urls:
                urls.append(self.primary_location.pdf_url)
        for loc in self.locations:
            if loc.pdf_url and loc.pdf_url not in urls:
                urls.append(loc.pdf_url)
        return urls

    @property
    def best_pdf_url(self) -> Optional[str]:
        """Get the best available PDF URL."""
        if self.best_oa_location and self.best_oa_location.pdf_url:
            return self.best_oa_location.pdf_url
        if self.primary_location and self.primary_location.pdf_url:
            return self.primary_location.pdf_url
        for loc in self.locations:
            if loc.is_oa and loc.pdf_url:
                return loc.pdf_url
        return None

    @property
    def author_names(self) -> List[str]:
        """Get list of author names."""
        return [
            auth.author.display_name
            for auth in self.authorships
            if auth.author and auth.author.display_name
        ]

    @property
    def first_author(self) -> Optional[str]:
        """Get first author name."""
        names = self.author_names
        return names[0] if names else None


class FlatWork(BaseModel):
    """Flattened work for DataFrame storage."""

    # IDs
    id: str
    openalex_id: str
    doi: Optional[str] = None

    # Basic info
    title: Optional[str] = None
    publication_year: Optional[int] = None
    publication_date: Optional[str] = None
    type: Optional[str] = None
    language: Optional[str] = None

    # Open Access
    is_oa: bool = False
    oa_status: Optional[str] = None
    oa_url: Optional[str] = None
    any_repository_has_fulltext: bool = False

    # Best OA Location
    best_oa_pdf_url: Optional[str] = None
    best_oa_landing_page: Optional[str] = None
    best_oa_version: Optional[str] = None
    best_oa_license: Optional[str] = None
    best_oa_source: Optional[str] = None
    best_oa_source_type: Optional[str] = None

    # Primary Location
    primary_pdf_url: Optional[str] = None
    primary_landing_page: Optional[str] = None
    primary_version: Optional[str] = None
    primary_license: Optional[str] = None
    primary_source: Optional[str] = None
    primary_source_type: Optional[str] = None

    # PDF availability
    num_locations: int = 0
    num_pdf_urls: int = 0
    num_oa_locations: int = 0
    all_pdf_urls: Optional[str] = None  # Pipe-separated
    has_any_pdf: bool = False

    # Topic
    topic_id: Optional[str] = None
    topic_name: Optional[str] = None
    topic_subfield: Optional[str] = None
    topic_field: Optional[str] = None
    topic_domain: Optional[str] = None

    # Authors
    num_authors: int = 0
    first_author: Optional[str] = None
    author_names: Optional[str] = None  # Pipe-separated

    # Top concepts
    concept_1_name: Optional[str] = None
    concept_1_score: Optional[float] = None
    concept_2_name: Optional[str] = None
    concept_2_score: Optional[float] = None
    concept_3_name: Optional[str] = None
    concept_3_score: Optional[float] = None

    # Keywords
    keywords: Optional[str] = None  # Pipe-separated

    # Metrics
    cited_by_count: int = 0

    # Flags
    is_retracted: bool = False
    is_paratext: bool = False

    # URLs
    openalex_url: str
    cited_by_api_url: Optional[str] = None

    # Original JSON (optional)
    full_json: Optional[str] = None

    @field_validator(
        "is_oa",
        "any_repository_has_fulltext",
        "has_any_pdf",
        "is_retracted",
        "is_paratext",
        mode="before",
    )
    @classmethod
    def validate_bool(cls, v):
        """Convert None to False for boolean fields."""
        if v is None:
            return False
        return v

    @classmethod
    def from_work(cls, work: OpenAlexWork, include_full_json: bool = True) -> "FlatWork":
        """Create flattened work from OpenAlexWork."""
        import json

        # Extract best OA location info
        best_oa = work.best_oa_location
        best_oa_data = {
            "best_oa_pdf_url": best_oa.pdf_url if best_oa else None,
            "best_oa_landing_page": best_oa.landing_page_url if best_oa else None,
            "best_oa_version": best_oa.version if best_oa else None,
            "best_oa_license": best_oa.license if best_oa else None,
            "best_oa_source": best_oa.source.display_name if best_oa and best_oa.source else None,
            "best_oa_source_type": best_oa.source.type if best_oa and best_oa.source else None,
        }

        # Extract primary location info
        primary = work.primary_location
        primary_data = {
            "primary_pdf_url": primary.pdf_url if primary else None,
            "primary_landing_page": primary.landing_page_url if primary else None,
            "primary_version": primary.version if primary else None,
            "primary_license": primary.license if primary else None,
            "primary_source": primary.source.display_name if primary and primary.source else None,
            "primary_source_type": primary.source.type if primary and primary.source else None,
        }

        # Extract topic info
        topic = work.primary_topic
        topic_data = {
            "topic_id": topic.id.split("/")[-1] if topic and topic.id else None,
            "topic_name": topic.display_name if topic else None,
            "topic_subfield": topic.subfield.get("display_name")
            if topic and topic.subfield
            else None,
            "topic_field": topic.field.get("display_name") if topic and topic.field else None,
            "topic_domain": topic.domain.get("display_name") if topic and topic.domain else None,
        }

        # Extract concepts
        concepts_data = {}
        for i, concept in enumerate(work.concepts[:3], 1):
            concepts_data[f"concept_{i}_name"] = concept.display_name
            concepts_data[f"concept_{i}_score"] = concept.score

        # Keywords
        keywords_str = (
            "|".join(k.get("display_name", "") for k in work.keywords if k.get("display_name"))
            or None
        )

        # PDF URLs
        all_pdf_urls = work.all_pdf_urls

        return cls(
            # IDs
            id=work.id,
            openalex_id=work.openalex_id,
            doi=work.doi,
            # Basic info
            title=work.title or work.display_name,
            publication_year=work.publication_year,
            publication_date=work.publication_date,
            type=work.type,
            language=work.language,
            # Open Access
            is_oa=work.open_access.is_oa,
            oa_status=work.open_access.oa_status,
            oa_url=work.open_access.oa_url,
            any_repository_has_fulltext=work.open_access.any_repository_has_fulltext,
            # Locations
            **best_oa_data,
            **primary_data,
            # PDF info
            num_locations=len(work.locations),
            num_pdf_urls=len(all_pdf_urls),
            num_oa_locations=sum(1 for loc in work.locations if loc.is_oa),
            all_pdf_urls="|".join(all_pdf_urls) if all_pdf_urls else None,
            has_any_pdf=work.has_pdf_url,
            # Topic
            **topic_data,
            # Authors
            num_authors=len(work.authorships),
            first_author=work.first_author,
            author_names="|".join(work.author_names) if work.author_names else None,
            # Concepts
            **concepts_data,
            # Keywords
            keywords=keywords_str,
            # Metrics
            cited_by_count=work.cited_by_count,
            # Flags
            is_retracted=work.is_retracted,
            is_paratext=work.is_paratext,
            # URLs
            openalex_url=work.id,
            cited_by_api_url=work.cited_by_api_url,
            # Full JSON
            full_json=json.dumps(work.model_dump()) if include_full_json else None,
        )


class DownloadStats(BaseModel):
    """Statistics for download operations."""

    total_works: int = 0
    pdfs_found: int = 0
    pdfs_downloaded: int = 0
    pdfs_skipped: int = 0
    pdfs_failed: int = 0
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """Calculate download success rate."""
        if self.pdfs_found == 0:
            return 0.0
        return (self.pdfs_downloaded / self.pdfs_found) * 100

    @property
    def duration_seconds(self) -> float:
        """Calculate duration in seconds."""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
