"""
Pydantic data models for PDF parsing pipeline.
"""

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Bounding box coordinates."""

    x1: int = Field(ge=0, description="Left x coordinate")
    y1: int = Field(ge=0, description="Top y coordinate")
    x2: int = Field(ge=0, description="Right x coordinate")
    y2: int = Field(ge=0, description="Bottom y coordinate")

    def width(self) -> int:
        """Calculate width of bounding box."""
        return self.x2 - self.x1

    def height(self) -> int:
        """Calculate height of bounding box."""
        return self.y2 - self.y1

    def area(self) -> int:
        """Calculate area of bounding box."""
        return self.width() * self.height()


class ImageDimensions(BaseModel):
    """Image dimension information for coordinate mapping."""

    original_width: int = Field(ge=1, description="Original image width")
    original_height: int = Field(ge=1, description="Original image height")
    padded_width: int = Field(ge=1, description="Padded (square) image width")
    padded_height: int = Field(ge=1, description="Padded (square) image height")


class LayoutElement(BaseModel):
    """Detected layout element from stage 1 (layout parsing)."""

    bbox: BoundingBox
    label: str = Field(description="Element type (text, title, tab, equ, code, fig, header, footer, etc.)")
    reading_order: int = Field(ge=0, description="Reading order in document")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ParsedElement(BaseModel):
    """Fully parsed element with content from stage 2 (element recognition)."""

    bbox: BoundingBox
    label: str = Field(description="Element type (text, title, tab, equ, code, fig, header, footer, etc.)")
    reading_order: int = Field(ge=0, description="Reading order in document")
    text: str = Field(description="Extracted text content")
    figure_path: Optional[Path] = Field(default=None, description="Path to saved figure (if label=fig)")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = {
            "bbox": [self.bbox.x1, self.bbox.y1, self.bbox.x2, self.bbox.y2],
            "label": self.label,
            "reading_order": self.reading_order,
            "text": self.text,
        }
        if self.figure_path:
            data["figure_path"] = str(self.figure_path)
        return data


class PageResult(BaseModel):
    """Results for a single page."""

    page_number: int = Field(ge=1, description="Page number (1-indexed)")
    elements: List[ParsedElement] = Field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "page_number": self.page_number,
            "elements": [elem.to_dict() for elem in self.elements],
        }


class DocumentResult(BaseModel):
    """Complete document parsing results."""

    source_file: Path
    total_pages: int = Field(ge=1)
    pages: List[PageResult] = Field(default_factory=list)
    metadata: Optional[dict] = Field(default=None, description="Optional document metadata")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "source_file": str(self.source_file),
            "total_pages": self.total_pages,
            "pages": [page.to_dict() for page in self.pages],
            "metadata": self.metadata or {},
        }

    def get_all_elements(self) -> List[ParsedElement]:
        """Get all parsed elements across all pages."""
        elements = []
        for page in self.pages:
            elements.extend(page.elements)
        return elements
