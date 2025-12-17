"""
Base processor implementation with common functionality.
"""

from typing import Any, Generic, List, TypeVar

from rag_pipeline.pdf_parsing.core.interfaces import Processor

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class BaseProcessor(Processor[InputT, OutputT], Generic[InputT, OutputT]):
    """Base implementation with common functionality for all processors."""

    def __init__(self, config: Any = None):
        """
        Initialize processor.

        Args:
            config: Processor-specific configuration object
        """
        self.config = config
        self._setup()

    def _setup(self) -> None:
        """
        Override for processor-specific setup.

        Called during __init__ after config is set.
        """
        pass

    def process_batch(self, inputs: List[InputT]) -> List[OutputT]:
        """
        Default batch processing implementation.

        Processes each input sequentially.
        Override this method for true batch optimization.

        Args:
            inputs: List of inputs to process

        Returns:
            List of processed outputs
        """
        return [self.process(input_data) for input_data in inputs]

    def validate_input(self, input_data: InputT) -> None:
        """
        Default validation implementation.

        Args:
            input_data: Input to validate

        Raises:
            ValueError: If input is None
        """
        if input_data is None:
            raise ValueError("Input cannot be None")

    def _validate_and_process(self, input_data: InputT) -> OutputT:
        """
        Validate and process input.

        Args:
            input_data: Input to validate and process

        Returns:
            Processed output
        """
        self.validate_input(input_data)
        return self.process(input_data)