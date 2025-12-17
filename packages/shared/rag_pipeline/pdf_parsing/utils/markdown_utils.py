"""
Markdown conversion utilities.

Adapted from Dolphin project.
Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
SPDX-License-Identifier: MIT
"""

import re
from typing import Any, Dict, List


def extract_table_from_html(html_string: str) -> str:
    """Extract and clean table tags from HTML string."""
    try:
        table_pattern = re.compile(r"<table.*?>.*?</table>", re.DOTALL)
        tables = table_pattern.findall(html_string)
        tables = [re.sub(r"<table[^>]*>", "<table>", table) for table in tables]
        return "\n".join(tables)
    except Exception as e:
        print(f"extract_table_from_html error: {str(e)}")
        return f"<table><tr><td>Error extracting table: {str(e)}</td></tr></table>"


class MarkdownConverter:
    """Convert structured recognition results to Markdown format."""

    def __init__(self):
        # Define heading levels for different section types
        self.heading_levels = {
            "sec_0": "#",
            "sec_1": "##",
            "sec_2": "###",
            "sec_3": "###",
            "sec_4": "###",
            "sec_5": "###",
        }

        # Define which labels need special handling
        self.special_labels = {
            "sec_0",
            "sec_1",
            "sec_2",
            "sec_3",
            "sec_4",
            "sec_5",
            "list",
            "equ",
            "tab",
            "fig",
        }

        # Define replacements for special formulas
        self.replace_dict = {
            "\\bm": "\\mathbf ",
            "\\eqno": "\\quad ",
            "\\quad": "\\quad ",
            "\\leq": "\\leq ",
            "\\pm": "\\pm ",
            "\\varmathbb": "\\mathbb ",
            "\\in fty": "\\infty",
            "\\mu": "\\mu ",
            "\\cdot": "\\cdot ",
            "\\langle": "\\langle ",
        }

    def try_remove_newline(self, text: str) -> str:
        """Process text to handle line breaks intelligently."""
        try:
            text = text.strip()
            text = text.replace("-\n", "")

            def is_chinese(char):
                return "\u4e00" <= char <= "\u9fff"

            lines = text.split("\n")
            processed_lines = []

            for i in range(len(lines) - 1):
                current_line = lines[i].strip()
                next_line = lines[i + 1].strip()

                if current_line:
                    if next_line:
                        if is_chinese(current_line[-1]) and is_chinese(next_line[0]):
                            processed_lines.append(current_line)
                        else:
                            processed_lines.append(current_line + " ")
                    else:
                        processed_lines.append(current_line + "\n")
                else:
                    processed_lines.append("\n")

            if lines and lines[-1].strip():
                processed_lines.append(lines[-1].strip())

            return "".join(processed_lines)

        except Exception as e:
            print(f"try_remove_newline error: {str(e)}")
            return text

    def _handle_text(self, text: str) -> str:
        """Process regular text content, preserving paragraph structure."""
        try:
            if not text:
                return ""

            text = self._process_formulas_in_text(text)
            text = self.try_remove_newline(text)
            return text
        except Exception as e:
            print(f"_handle_text error: {str(e)}")
            return text

    def _process_formulas_in_text(self, text: str) -> str:
        """Process mathematical formulas in text."""
        try:
            text = text.replace(r"\upmu", r"\mu")
            for key, value in self.replace_dict.items():
                text = text.replace(key, value)
            return text

        except Exception as e:
            print(f"_process_formulas_in_text error: {str(e)}")
            return text

    def _remove_newline_in_heading(self, text: str) -> str:
        """Remove newline in heading."""
        try:

            def is_chinese(char):
                return "\u4e00" <= char <= "\u9fff"

            if any(is_chinese(char) for char in text):
                return text.replace("\n", "")
            else:
                return text.replace("\n", " ")

        except Exception as e:
            print(f"_remove_newline_in_heading error: {str(e)}")
            return text

    def _handle_heading(self, text: str, label: str) -> str:
        """Convert section headings to appropriate markdown format."""
        try:
            level = self.heading_levels.get(label, "#")
            text = text.strip()
            text = self._remove_newline_in_heading(text)
            text = self._handle_text(text)
            return f"{level} {text}\n\n"

        except Exception as e:
            print(f"_handle_heading error: {str(e)}")
            return f"# Error processing heading: {text}\n\n"

    def _handle_list_item(self, text: str) -> str:
        """Convert list items to markdown list format."""
        try:
            return f"- {text.strip()}\n"
        except Exception as e:
            print(f"_handle_list_item error: {str(e)}")
            return f"- Error processing list item: {text}\n"

    def _handle_figure(self, text: str, section_count: int) -> str:
        """Handle figure content."""
        try:
            # Check if it's already a markdown format image link
            if text.startswith("!["):
                return f"{text}\n\n"

            # If it's a base64 or data URI
            if text.startswith("data:image/"):
                return f"![Figure {section_count}]({text})\n\n"
            elif ";" in text and "," in text:
                return f"![Figure {section_count}]({text})\n\n"
            else:
                # Assume it's raw base64
                img_format = "png"
                data_uri = f"data:image/{img_format};base64,{text}"
                return f"![Figure {section_count}]({data_uri})\n\n"

        except Exception as e:
            print(f"_handle_figure error: {str(e)}")
            return f"*[Error processing figure: {str(e)}]*\n\n"

    def _handle_table(self, text: str) -> str:
        """Convert table content to markdown format."""
        try:
            markdown_content = []
            markdown_table = extract_table_from_html(text)
            markdown_content.append(markdown_table + "\n")
            return "\n".join(markdown_content) + "\n\n"

        except Exception as e:
            print(f"_handle_table error: {str(e)}")
            return f"*[Error processing table: {str(e)}]*\n\n"

    def _handle_formula(self, text: str) -> str:
        """Handle formula-specific content."""
        try:
            text = text.strip("$").rstrip("\\ ").replace(r"\upmu", r"\mu")
            for key, value in self.replace_dict.items():
                text = text.replace(key, value)
            processed_text = "$$" + text + "$$"
            return f"{processed_text}\n\n"

        except Exception as e:
            print(f"_handle_formula error: {str(e)}")
            return f"*[Error processing formula: {str(e)}]*\n\n"

    def convert(self, recognition_results: List[Dict[str, Any]]) -> str:
        """Convert recognition results to markdown format."""
        try:
            markdown_content = []

            for section_count, result in enumerate(recognition_results):
                try:
                    label = result.get("label", "")
                    text = result.get("text", "").strip()

                    if not text:
                        continue

                    # Handle different content types
                    if label in {"sec_0", "sec_1", "sec_2", "sec_3", "sec_4", "sec_5"}:
                        markdown_content.append(self._handle_heading(text, label))
                    elif label == "fig":
                        markdown_content.append(self._handle_figure(text, section_count))
                    elif label == "tab":
                        markdown_content.append(self._handle_table(text))
                    elif label == "equ":
                        markdown_content.append(self._handle_formula(text))
                    elif label == "list":
                        markdown_content.append(self._handle_list_item(text))
                    elif label == "code":
                        markdown_content.append(f"```bash\n{text}\n```\n\n")
                    else:
                        # Handle regular text
                        processed_text = self._handle_text(text)
                        markdown_content.append(f"{processed_text}\n\n")

                except Exception as e:
                    print(f"Error processing item {section_count}: {str(e)}")
                    markdown_content.append("*[Error processing content]*\n\n")

            result = "".join(markdown_content)
            return result

        except Exception as e:
            print(f"convert error: {str(e)}")
            return f"Error generating markdown content: {str(e)}"