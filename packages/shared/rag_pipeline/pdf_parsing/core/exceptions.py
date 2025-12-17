"""
Custom exceptions for PDF parsing pipeline.
"""


class PDFParsingError(Exception):
    """Base exception for PDF parsing errors."""

    pass


class ModelLoadError(PDFParsingError):
    """Error loading the Dolphin model."""

    pass


class ImageExtractionError(PDFParsingError):
    """Error extracting images from PDF."""

    pass


class LayoutParsingError(PDFParsingError):
    """Error parsing document layout."""

    pass


class ElementRecognitionError(PDFParsingError):
    """Error recognizing element content."""

    pass


class OutputGenerationError(PDFParsingError):
    """Error generating output files."""

    pass


class ValidationError(PDFParsingError):
    """Data validation error."""

    pass