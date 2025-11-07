"""
Element recognition processor for extracting content from layout elements.
"""

from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image

from rag_pipeline.pdf_parsing.config import ProcessingConfig
from rag_pipeline.pdf_parsing.core.exceptions import ElementRecognitionError
from rag_pipeline.pdf_parsing.model.dolphin import DolphinModel
from rag_pipeline.pdf_parsing.data_models import BoundingBox, LayoutElement, ParsedElement
from rag_pipeline.pdf_parsing.processors.base import BaseProcessor
from rag_pipeline.pdf_parsing.utils.coordinate_utils import process_coordinates
from rag_pipeline.pdf_parsing.utils.image_utils import crop_image_region, prepare_image, save_image


class ElementRecognizer(BaseProcessor[Tuple[Image.Image, List[LayoutElement]], List[ParsedElement]]):
    """
    Processor that recognizes content of layout elements.

    Extracts text, tables, equations, code, and figures from detected layout regions.
    Uses batch processing for efficiency.
    """

    # Element-specific prompts
    PROMPTS = {
        "tab": "Parse the table in the image.",
        "equ": "Read formula in the image.",
        "code": "Read code in the image.",
        "text": "Read text in the image.",
        "title": "Read text in the image.",
    }

    def __init__(self, model: DolphinModel, config: ProcessingConfig, save_dir: Path = None):
        """
        Initialize element recognizer.

        Args:
            model: Dolphin model instance
            config: Processing configuration
            save_dir: Directory to save figures (optional)
        """
        self.model = model
        self.save_dir = save_dir
        super().__init__(config)

    def process(self, input_data: Tuple[Image.Image, List[LayoutElement]]) -> List[ParsedElement]:
        """
        Recognize content of all layout elements.

        Args:
            input_data: Tuple of (page_image, layout_elements)

        Returns:
            List of parsed elements with extracted content

        Raises:
            ElementRecognitionError: If element recognition fails
        """
        try:
            image, layout_elements = input_data

            if not layout_elements:
                return []

            # Prepare image with padding
            padded_image, dims = prepare_image(image)

            # Group elements by type for batch processing
            elements_by_type = self._group_elements_by_type(layout_elements, padded_image, dims)

            # Process each type in batches
            parsed_elements = []

            # Handle figures separately (no model inference needed)
            if "fig" in elements_by_type:
                parsed_elements.extend(self._process_figures(elements_by_type["fig"]))

            # Process other element types with model
            for element_type, elements in elements_by_type.items():
                if element_type == "fig":
                    continue

                prompt = self.PROMPTS.get(element_type, self.PROMPTS["text"])
                batch_results = self._process_element_batch(elements, prompt)
                parsed_elements.extend(batch_results)

            # Sort by reading order
            parsed_elements.sort(key=lambda x: x.reading_order)

            return parsed_elements

        except Exception as e:
            raise ElementRecognitionError(f"Failed to recognize elements: {str(e)}")

    def _group_elements_by_type(
        self, layout_elements: List[LayoutElement], padded_image, dims
    ) -> Dict[str, List[dict]]:
        """Group layout elements by type and prepare for processing."""
        elements_by_type = {}
        previous_box = None

        for element in layout_elements:
            try:
                # Get normalized coordinates from layout element
                coords = [element.bbox.x1, element.bbox.y1, element.bbox.x2, element.bbox.y2]

                # Process coordinates
                x1, y1, x2, y2, orig_x1, orig_y1, orig_x2, orig_y2, previous_box = process_coordinates(
                    coords, padded_image, dims, previous_box
                )

                # Crop element from padded image
                pil_crop = crop_image_region(padded_image, x1, y1, x2, y2)

                # Store element info
                element_info = {
                    "crop": pil_crop,
                    "label": element.label,
                    "bbox": BoundingBox(x1=orig_x1, y1=orig_y1, x2=orig_x2, y2=orig_y2),
                    "reading_order": element.reading_order,
                }

                # Group by label
                if element.label not in elements_by_type:
                    elements_by_type[element.label] = []
                elements_by_type[element.label].append(element_info)

            except Exception as e:
                print(f"Error processing element {element.reading_order}: {str(e)}")
                continue

        return elements_by_type

    def _process_element_batch(self, elements: List[dict], prompt: str) -> List[ParsedElement]:
        """Process a batch of elements of the same type."""
        results = []
        # Get batch size from model config, default to 16
        batch_size = getattr(self.model.config, 'max_batch_size', 16)

        # Process in batches
        for i in range(0, len(elements), batch_size):
            batch_elements = elements[i : i + batch_size]
            crops_list = [elem["crop"] for elem in batch_elements]

            # Use same prompt for all elements in batch
            prompts_list = [prompt] * len(crops_list)

            # Batch inference
            batch_results = self.model.infer_batch(prompts_list, crops_list)

            # Create ParsedElement objects
            for j, text in enumerate(batch_results):
                elem = batch_elements[j]
                parsed = ParsedElement(
                    label=elem["label"],
                    bbox=elem["bbox"],
                    text=text.strip(),
                    reading_order=elem["reading_order"],
                )
                results.append(parsed)

        return results

    def _process_figures(self, figures: List[dict]) -> List[ParsedElement]:
        """Process figure elements by saving them to disk."""
        results = []

        for fig_info in figures:
            crop = fig_info["crop"]
            reading_order = fig_info["reading_order"]

            # Save figure if configured
            figure_path = None
            if self.config.save_figures and self.save_dir:
                figure_filename = f"figure_{reading_order:03d}.png"
                figure_path = self.save_dir / figure_filename

                try:
                    save_image(crop, figure_path)
                    # Create markdown-style reference
                    text = f"![Figure](figures/{figure_filename})"
                except Exception as e:
                    print(f"Error saving figure {reading_order}: {str(e)}")
                    text = f"[Figure {reading_order}]"
            else:
                text = f"[Figure {reading_order}]"

            parsed = ParsedElement(
                label=fig_info["label"],
                bbox=fig_info["bbox"],
                text=text,
                reading_order=reading_order,
                figure_path=figure_path,
            )
            results.append(parsed)

        return results

    def validate_input(self, input_data: Tuple[Image.Image, List[LayoutElement]]) -> None:
        """Validate input data."""
        if input_data is None:
            raise ValueError("Input data cannot be None")

        if not isinstance(input_data, tuple) or len(input_data) != 2:
            raise TypeError("Input must be a tuple of (Image, List[LayoutElement])")

        image, elements = input_data

        if not isinstance(image, Image.Image):
            raise TypeError(f"Expected PIL Image, got {type(image)}")

        if not isinstance(elements, list):
            raise TypeError(f"Expected list of LayoutElements, got {type(elements)}")