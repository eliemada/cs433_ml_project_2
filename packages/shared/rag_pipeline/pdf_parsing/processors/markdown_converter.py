"""
Markdown conversion processor for generating output files.
"""

import json
from pathlib import Path

from rag_pipeline.pdf_parsing.config import OutputConfig
from rag_pipeline.pdf_parsing.core.exceptions import OutputGenerationError
from rag_pipeline.pdf_parsing.data_models import DocumentResult
from rag_pipeline.pdf_parsing.processors.base import BaseProcessor
from rag_pipeline.pdf_parsing.utils.markdown_utils import MarkdownConverter as MarkdownConverterUtil


class MarkdownConverter(BaseProcessor[DocumentResult, None]):
    """
    Processor that converts parsed document results to Markdown and JSON.

    Generates output files in configured directories.
    """

    def __init__(self, config: OutputConfig):
        """
        Initialize markdown converter.

        Args:
            config: Output configuration
        """
        super().__init__(config)
        self.converter = MarkdownConverterUtil()

    def process(self, doc_result: DocumentResult) -> None:
        """
        Convert document result to Markdown and save outputs.

        Args:
            doc_result: Complete document parsing results

        Raises:
            OutputGenerationError: If output generation fails
        """
        try:
            base_name = doc_result.source_file.stem

            # Generate JSON output
            if self.config.output_dir:
                self._save_json(doc_result, base_name)

            # Generate Markdown output
            self._save_markdown(doc_result, base_name)

        except Exception as e:
            raise OutputGenerationError(f"Failed to generate outputs: {str(e)}")

    def _save_json(self, doc_result: DocumentResult, base_name: str) -> Path:
        """Save JSON output."""
        try:
            json_path = self.config.get_json_dir() / f"{base_name}.json"

            # Convert to dictionary
            output_data = doc_result.to_dict()

            # Save JSON
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            print(f"JSON saved to: {json_path}")
            return json_path

        except Exception as e:
            raise OutputGenerationError(f"Failed to save JSON: {str(e)}")

    def _save_markdown(self, doc_result: DocumentResult, base_name: str) -> Path:
        """Save Markdown output."""
        try:
            markdown_path = self.config.get_markdown_dir() / f"{base_name}.md"

            # Combine all elements across pages
            all_elements = []
            for page_idx, page in enumerate(doc_result.pages):
                # Add page separator if not first page
                if page_idx > 0:
                    all_elements.append(
                        {"label": "page_separator", "text": "\n\n---\n\n", "reading_order": len(all_elements)}
                    )

                # Convert ParsedElement to dict for markdown converter
                for elem in page.elements:
                    all_elements.append(elem.to_dict())

            # Generate markdown
            markdown_content = self.converter.convert(all_elements)

            # Save markdown
            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            print(f"Markdown saved to: {markdown_path}")
            return markdown_path

        except Exception as e:
            raise OutputGenerationError(f"Failed to save Markdown: {str(e)}")

    def validate_input(self, doc_result: DocumentResult) -> None:
        """Validate document result."""
        if doc_result is None:
            raise ValueError("Document result cannot be None")
        if not isinstance(doc_result, DocumentResult):
            raise TypeError(f"Expected DocumentResult, got {type(doc_result)}")