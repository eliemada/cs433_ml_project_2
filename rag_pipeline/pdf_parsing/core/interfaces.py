"""
Abstract interfaces for PDF parsing pipeline components.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, List, TypeVar

from PIL import Image

from rag_pipeline.pdf_parsing.data_models import DocumentResult, PageResult

# Type variables for generic processor types
InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class Processor(ABC, Generic[InputT, OutputT]):
    """Abstract base class for all pipeline processors."""

    @abstractmethod
    def process(self, input_data: InputT) -> OutputT:
        """
        Process input and return output.

        Args:
            input_data: Input data to process

        Returns:
            Processed output data
        """
        pass

    def process_batch(self, inputs: List[InputT]) -> List[OutputT]:
        """
        Process multiple inputs in batch.

        Default implementation processes sequentially.
        Override for true batch optimization.

        Args:
            inputs: List of inputs to process

        Returns:
            List of processed outputs
        """
        return [self.process(input_data) for input_data in inputs]

    def validate_input(self, input_data: InputT) -> None:
        """
        Optional validation hook for input data.

        Args:
            input_data: Input data to validate

        Raises:
            ValidationError: If input is invalid
        """
        pass


class DocumentParser(ABC):
    """Abstract interface for document parsers."""

    @abstractmethod
    def parse_document(self, document_path: Path) -> DocumentResult:
        """
        Parse a complete document.

        Args:
            document_path: Path to document file

        Returns:
            Complete document parsing results
        """
        pass

    @abstractmethod
    def parse_page(self, image: Image.Image, page_num: int) -> PageResult:
        """
        Parse a single page.

        Args:
            image: Page image
            page_num: Page number (1-indexed)

        Returns:
            Page parsing results
        """
        pass


class ModelWrapper(ABC):
    """Abstract interface for ML model wrappers."""

    @abstractmethod
    def load(self) -> None:
        """Load model into memory."""
        pass

    @abstractmethod
    def unload(self) -> None:
        """Unload model from memory."""
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        """
        Check if model is loaded.

        Returns:
            True if model is loaded, False otherwise
        """
        pass

    @abstractmethod
    def infer(self, prompt: str, image: Image.Image) -> str:
        """
        Single inference.

        Args:
            prompt: Text prompt for the model
            image: Input image

        Returns:
            Model output text
        """
        pass

    @abstractmethod
    def infer_batch(self, prompts: List[str], images: List[Image.Image]) -> List[str]:
        """
        Batch inference.

        Args:
            prompts: List of text prompts
            images: List of input images

        Returns:
            List of model output texts
        """
        pass