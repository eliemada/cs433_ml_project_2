"""
Test script for PDF parsing pipeline.
"""

from pathlib import Path

from rag_pipeline.pdf_parsing import PDFParsingPipeline, PDFParsingConfig, OutputConfig


def main():
    """Test the PDF parsing pipeline with a sample PDF."""
    # Select a sample PDF
    pdf_path = Path("data/openalex/pdfs/00347_W3004748802_Small_firms_and_patenting_revisited.pdf")

    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        return

    # Configure pipeline
    output_dir = Path("output/pdf_parsing_test")
    config = PDFParsingConfig(output=OutputConfig(output_dir=output_dir))

    # Create pipeline
    print("Initializing PDF parsing pipeline...")
    pipeline = PDFParsingPipeline(config)

    # Parse document
    try:
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

    except Exception as e:
        print(f"\nError during parsing: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Clean up
        pipeline.unload_model()


if __name__ == "__main__":
    main()