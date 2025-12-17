"""
Layout parsing processor for detecting document structure.
"""

from typing import List

from PIL import Image

from rag_pipeline.pdf_parsing.core.exceptions import LayoutParsingError
from rag_pipeline.pdf_parsing.model.dolphin import DolphinModel
from rag_pipeline.pdf_parsing.data_models import BoundingBox, LayoutElement
from rag_pipeline.pdf_parsing.processors.base import BaseProcessor
from rag_pipeline.pdf_parsing.utils.coordinate_utils import parse_layout_string


class LayoutParser(BaseProcessor[Image.Image, List[LayoutElement]]):
    """
    Processor that detects layout elements in document images.

    Uses Dolphin model to identify text regions, tables, figures, equations, etc.
    """

    LAYOUT_PROMPT = "Parse the reading order of this document."

    def __init__(self, model: DolphinModel):
        """
        Initialize layout parser.

        Args:
            model: Dolphin model instance
        """
        self.model = model
        super().__init__(config=None)

    def process(self, image: Image.Image) -> List[LayoutElement]:
        """
        Parse layout of document image.

        Args:
            image: PIL Image of document page

        Returns:
            List of detected layout elements with bounding boxes

        Raises:
            LayoutParsingError: If layout parsing fails
        """
        try:
            # Ensure model is loaded
            if not self.model.is_loaded():
                self.model.load()

            # Get layout output from Dolphin
            layout_output = self.model.infer(self.LAYOUT_PROMPT, image)

            # Parse layout string to extract bounding boxes and labels
            parsed_layout = parse_layout_string(layout_output)

            # Convert to LayoutElement objects
            elements = []
            for reading_order, (coords, label) in enumerate(parsed_layout):
                # Create bounding box (coords are in normalized 896x896 space)
                bbox = BoundingBox(
                    x1=int(coords[0]), y1=int(coords[1]), x2=int(coords[2]), y2=int(coords[3])
                )

                element = LayoutElement(bbox=bbox, label=label, reading_order=reading_order)
                elements.append(element)

            return elements

        except Exception as e:
            raise LayoutParsingError(f"Failed to parse layout: {str(e)}")

    def validate_input(self, image: Image.Image) -> None:
        """Validate image input."""
        if image is None:
            raise ValueError("Image cannot be None")
        if not isinstance(image, Image.Image):
            raise TypeError(f"Expected PIL Image, got {type(image)}")