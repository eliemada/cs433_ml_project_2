"""
Main pipeline orchestrator for PDF parsing.
"""

from pathlib import Path
from typing import Optional

from PIL import Image

from rag_pipeline.pdf_parsing.config import PDFParsingConfig
from rag_pipeline.pdf_parsing.core.interfaces import DocumentParser
from rag_pipeline.pdf_parsing.model.dolphin import DolphinModel
from rag_pipeline.pdf_parsing.data_models import DocumentResult, PageResult
from rag_pipeline.pdf_parsing.processors import (
    ElementRecognizer,
    ImageExtractor,
    LayoutParser,
    MarkdownConverter,
)


class PDFParsingPipeline(DocumentParser):
    """
    Main pipeline orchestrator for PDF parsing.

    Coordinates the flow of data through all processing stages:
    PDF → Images → Layout Detection → Element Recognition → Markdown/JSON
    """

    def __init__(self, config: PDFParsingConfig, model: Optional[DolphinModel] = None):
        """
        Initialize pipeline.

        Args:
            config: Pipeline configuration
            model: Optional pre-loaded Dolphin model (will create if not provided)
        """
        self.config = config

        # Initialize or use provided model
        self.model = model or DolphinModel(config.model)

        # Initialize processors
        self.image_extractor = ImageExtractor(config.processing)
        self.layout_parser = LayoutParser(self.model)
        self.markdown_converter = MarkdownConverter(config.output)

        # Element recognizer needs the figures directory
        self.element_recognizer = ElementRecognizer(
            model=self.model,
            config=config.processing,
            save_dir=config.output.get_figures_dir(),
        )

    def parse_document(self, document_path: Path) -> DocumentResult:
        """
        Parse complete PDF document.

        Args:
            document_path: Path to PDF file

        Returns:
            Complete document parsing results
        """
        print(f"\n{'='*60}")
        print(f"Parsing document: {document_path.name}")
        print(f"{'='*60}\n")

        # Stage 1: Extract images from PDF
        print("Stage 1: Extracting images from PDF...")
        images = self.image_extractor.process(document_path)
        print(f"  ✓ Extracted {len(images)} page(s)\n")

        # Stage 2: Parse each page
        print("Stage 2: Parsing pages...")
        pages = []
        for page_num, image in enumerate(images, start=1):
            print(f"  Processing page {page_num}/{len(images)}...")
            page_result = self.parse_page(image, page_num)
            pages.append(page_result)
            print(f"    ✓ Found {len(page_result.elements)} element(s)")

        print(f"\n  ✓ Parsed all {len(pages)} page(s)\n")

        # Stage 3: Create document result
        doc_result = DocumentResult(
            source_file=document_path, total_pages=len(pages), pages=pages
        )

        # Stage 4: Generate outputs
        print("Stage 3: Generating outputs...")
        self.markdown_converter.process(doc_result)
        print(f"\n{'='*60}")
        print("✓ Parsing complete!")
        print(f"{'='*60}\n")

        return doc_result

    def parse_page(self, image: Image.Image, page_num: int) -> PageResult:
        """
        Parse a single page.

        Args:
            image: Page image
            page_num: Page number (1-indexed)

        Returns:
            Page parsing results
        """
        # Stage 1: Detect layout elements
        layout_elements = self.layout_parser.process(image)

        # Stage 2: Recognize content of each element
        parsed_elements = self.element_recognizer.process((image, layout_elements))

        return PageResult(page_number=page_num, elements=parsed_elements)

    def unload_model(self) -> None:
        """Unload the Dolphin model from memory."""
        if self.model:
            self.model.unload()