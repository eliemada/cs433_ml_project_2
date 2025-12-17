"""
Image extraction processor for converting PDFs to images.
"""

from pathlib import Path
from typing import List

from PIL import Image

from rag_pipeline.pdf_parsing.config import ProcessingConfig
from rag_pipeline.pdf_parsing.core.exceptions import ImageExtractionError
from rag_pipeline.pdf_parsing.processors.base import BaseProcessor
from rag_pipeline.pdf_parsing.utils.image_utils import convert_pdf_to_images


class ImageExtractor(BaseProcessor[Path, List[Image.Image]]):
    """
    Processor that extracts images from PDF files.

    Converts each PDF page to a PIL Image.
    """

    def __init__(self, config: ProcessingConfig):
        """
        Initialize image extractor.

        Args:
            config: Processing configuration
        """
        super().__init__(config)

    def process(self, pdf_path: Path) -> List[Image.Image]:
        """
        Extract images from PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of PIL Images, one per page

        Raises:
            ImageExtractionError: If PDF cannot be converted
        """
        try:
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")

            if pdf_path.suffix.lower() != ".pdf":
                raise ValueError(f"Not a PDF file: {pdf_path}")

            images = convert_pdf_to_images(pdf_path, target_size=self.config.target_image_size)

            if not images:
                raise ImageExtractionError(f"No pages extracted from PDF: {pdf_path}")

            return images

        except Exception as e:
            raise ImageExtractionError(f"Failed to extract images from PDF: {str(e)}")

    def validate_input(self, pdf_path: Path) -> None:
        """Validate PDF path."""
        if pdf_path is None:
            raise ValueError("PDF path cannot be None")
        if not isinstance(pdf_path, Path):
            raise TypeError(f"Expected Path, got {type(pdf_path)}")