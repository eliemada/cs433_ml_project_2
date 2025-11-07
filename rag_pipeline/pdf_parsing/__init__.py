"""
PDF Parsing Pipeline

A modular, pipeline-based system for converting PDF documents to structured Markdown
using the ByteDance Dolphin multimodal model.

Usage:
    from pathlib import Path
    from rag_pipeline.pdf_parsing import PDFParsingPipeline, PDFParsingConfig, OutputConfig

    # Configure pipeline
    config = PDFParsingConfig(
        output=OutputConfig(output_dir=Path("./output"))
    )

    # Create and run pipeline
    pipeline = PDFParsingPipeline(config)
    result = pipeline.parse_document(Path("document.pdf"))

    # Access results
    for page in result.pages:
        for element in page.elements:
            print(f"{element.label}: {element.text}")
"""

from rag_pipeline.pdf_parsing.config import (
    DolphinModelConfig,
    OutputConfig,
    PDFParsingConfig,
    ProcessingConfig,
)
from rag_pipeline.pdf_parsing.core.pipeline import PDFParsingPipeline
from rag_pipeline.pdf_parsing.data_models import (
    BoundingBox,
    DocumentResult,
    ImageDimensions,
    LayoutElement,
    PageResult,
    ParsedElement,
)
from rag_pipeline.pdf_parsing.factories import ProcessorFactory
from rag_pipeline.pdf_parsing.model import DolphinModel

__version__ = "1.0.0"

__all__ = [
    # Main pipeline
    "PDFParsingPipeline",
    # Configuration
    "PDFParsingConfig",
    "DolphinModelConfig",
    "ProcessingConfig",
    "OutputConfig",
    # Data models
    "DocumentResult",
    "PageResult",
    "ParsedElement",
    "LayoutElement",
    "BoundingBox",
    "ImageDimensions",
    # Model
    "DolphinModel",
    # Factory
    "ProcessorFactory",
]