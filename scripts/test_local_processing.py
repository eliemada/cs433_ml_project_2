#!/usr/bin/env python3
"""Local test script for PDF processing (without S3)."""

from pathlib import Path

from rag_pipeline.pdf_parsing import (
    PDFParsingConfig,
    PDFParsingPipeline,
    DolphinModelConfig,
    OutputConfig,
)


def main():
    """Test PDF parsing locally."""
    # Select a sample PDF
    pdf_path = Path("data/openalex/pdfs/00347_W3004748802_Small_firms_and_patenting_revisited.pdf")

    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        print("\nAvailable PDFs:")
        pdfs_dir = Path("data/openalex/pdfs")
        for pdf in sorted(pdfs_dir.glob("*.pdf"))[:5]:
            print(f"  - {pdf.name}")
        return

    # Configure pipeline
    output_dir = Path("output/test_local_processing")

    print(f"Testing PDF: {pdf_path.name}")
    print(f"Output directory: {output_dir}\n")

    # Use local model path (should be downloaded via git clone or model download)
    model_path = Path("rag_pipeline/pdf_parsing/models")
    if not model_path.exists():
        print(f"Warning: Model not found at {model_path}")
        print("The pipeline will attempt to download it automatically.")

    config = PDFParsingConfig(
        model=DolphinModelConfig(model_path=model_path),
        output=OutputConfig(output_dir=output_dir),
    )

    # Create pipeline
    print("Initializing PDF parsing pipeline...")
    try:
        pipeline = PDFParsingPipeline(config)
    except Exception as e:
        print(f"Failed to initialize pipeline: {e}")
        print("\nNote: Dolphin model requires significant memory and GPU (if available).")
        return

    # Parse document
    try:
        print(f"Processing: {pdf_path.name}")
        result = pipeline.parse_document(pdf_path)

        # Print results summary
        print(f"\n{'='*60}")
        print("RESULTS SUMMARY")
        print(f"{'='*60}")
        print(f"Document: {result.source_file.name}")
        print(f"Total pages: {result.total_pages}")
        print(f"Total elements: {len(result.get_all_elements())}")
        print(f"\nOutput directory: {output_dir}")
        print(f"  - Markdown: {output_dir / 'markdown'}")
        print(f"  - JSON: {output_dir / 'recognition_json'}")
        print(f"  - Figures: {output_dir / 'markdown' / 'figures'}")

        # Show sample elements
        print(f"\n{'='*60}")
        print("SAMPLE ELEMENTS (first 5)")
        print(f"{'='*60}")
        for i, elem in enumerate(result.get_all_elements()[:5], 1):
            print(f"\n{i}. [{elem.label}] (reading order: {elem.reading_order})")
            print(f"   Text: {elem.text[:100]}{'...' if len(elem.text) > 100 else ''}")

        print(f"\n{'='*60}")
        print("SUCCESS! Local processing test passed.")
        print(f"{'='*60}")

    except Exception as e:
        print(f"\nError during parsing: {e}")
        import traceback
        traceback.print_exc()
        return
    finally:
        # Clean up
        pipeline.unload_model()


if __name__ == "__main__":
    main()
