"""
Pydantic configuration models for PDF parsing pipeline.
"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class DolphinModelConfig(BaseModel):
    """Configuration for Dolphin model."""

    model_path: Path = Field(
        default=Path(__file__).parent / "models",
        description="Path to Dolphin model weights directory",
    )
    device: Literal["cuda", "cpu", "auto"] = Field(
        default="auto", description="Device to run model on"
    )
    use_fp16: bool = Field(
        default=True, description="Use half precision (FP16) on CUDA for faster inference"
    )
    max_batch_size: int = Field(
        default=16, ge=1, le=32, description="Maximum batch size for element recognition"
    )

    @field_validator("model_path")
    @classmethod
    def validate_model_path(cls, v: Path) -> Path:
        """Ensure model path is absolute."""
        return v.resolve()


class ProcessingConfig(BaseModel):
    """Configuration for document processing."""

    target_image_size: int = Field(
        default=896,
        ge=512,
        le=2048,
        description="Target size for longest dimension when converting PDF to images",
    )
    save_figures: bool = Field(default=True, description="Save extracted figures to disk")
    save_visualizations: bool = Field(
        default=False, description="Save layout visualizations with bounding boxes"
    )
    save_json: bool = Field(default=True, description="Save JSON output with parsing results")
    chunk_overlap: int = Field(
        default=100, ge=0, description="Overlap between chunks for downstream processing"
    )


class OutputConfig(BaseModel):
    """Configuration for output generation."""

    output_dir: Path = Field(description="Base directory for all outputs")
    figures_subdir: str = Field(default="figures", description="Subdirectory for extracted figures")
    json_subdir: str = Field(
        default="recognition_json", description="Subdirectory for JSON output files"
    )
    markdown_subdir: str = Field(default="markdown", description="Subdirectory for Markdown files")

    @field_validator("output_dir")
    @classmethod
    def validate_output_dir(cls, v: Path) -> Path:
        """Create output directory if it doesn't exist."""
        v = v.resolve()
        v.mkdir(parents=True, exist_ok=True)
        return v

    def get_figures_dir(self) -> Path:
        """Get the full path to figures directory."""
        return self.output_dir / self.markdown_subdir / self.figures_subdir

    def get_json_dir(self) -> Path:
        """Get the full path to JSON directory."""
        return self.output_dir / self.json_subdir

    def get_markdown_dir(self) -> Path:
        """Get the full path to Markdown directory."""
        return self.output_dir / self.markdown_subdir

    def setup_directories(self) -> None:
        """Create all output subdirectories."""
        self.get_figures_dir().mkdir(parents=True, exist_ok=True)
        self.get_json_dir().mkdir(parents=True, exist_ok=True)
        self.get_markdown_dir().mkdir(parents=True, exist_ok=True)


class PDFParsingConfig(BaseModel):
    """Main configuration for PDF parsing pipeline."""

    model: DolphinModelConfig = Field(default_factory=DolphinModelConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    output: OutputConfig

    def model_post_init(self, __context) -> None:
        """Post-initialization hook to setup directories."""
        self.output.setup_directories()