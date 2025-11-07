"""
Factory for creating processors based on configuration.
"""

from typing import Optional

from rag_pipeline.pdf_parsing.config import PDFParsingConfig, ProcessingConfig
from rag_pipeline.pdf_parsing.model.dolphin import DolphinModel
from rag_pipeline.pdf_parsing.processors import (
    ElementRecognizer,
    ImageExtractor,
    LayoutParser,
    MarkdownConverter,
)


class ProcessorFactory:
    """
    Factory for creating pipeline processors.

    Enables dependency injection and easier testing with mock processors.
    """

    @staticmethod
    def create_image_extractor(config: ProcessingConfig) -> ImageExtractor:
        """
        Create image extractor processor.

        Args:
            config: Processing configuration

        Returns:
            ImageExtractor instance
        """
        return ImageExtractor(config)

    @staticmethod
    def create_layout_parser(model: DolphinModel) -> LayoutParser:
        """
        Create layout parser processor.

        Args:
            model: Dolphin model instance

        Returns:
            LayoutParser instance
        """
        return LayoutParser(model)

    @staticmethod
    def create_element_recognizer(
        model: DolphinModel, config: ProcessingConfig, save_dir=None
    ) -> ElementRecognizer:
        """
        Create element recognizer processor.

        Args:
            model: Dolphin model instance
            config: Processing configuration
            save_dir: Directory to save figures

        Returns:
            ElementRecognizer instance
        """
        return ElementRecognizer(model, config, save_dir)

    @staticmethod
    def create_markdown_converter(config) -> MarkdownConverter:
        """
        Create markdown converter processor.

        Args:
            config: Output configuration

        Returns:
            MarkdownConverter instance
        """
        return MarkdownConverter(config)

    @classmethod
    def create_all_processors(
        cls, config: PDFParsingConfig, model: Optional[DolphinModel] = None
    ) -> dict:
        """
        Create all processors for the pipeline.

        Args:
            config: Pipeline configuration
            model: Optional Dolphin model instance

        Returns:
            Dictionary of processor instances
        """
        if model is None:
            model = DolphinModel(config.model)

        return {
            "image_extractor": cls.create_image_extractor(config.processing),
            "layout_parser": cls.create_layout_parser(model),
            "element_recognizer": cls.create_element_recognizer(
                model, config.processing, config.output.get_figures_dir()
            ),
            "markdown_converter": cls.create_markdown_converter(config.output),
        }