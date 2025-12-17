"""
Test script for chunking system.
Verifies that chunking and S3 loading work correctly.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_pipeline.rag.markdown_chunker import MarkdownChunker
from scripts.utils.markdown_s3_loader import S3MarkdownLoader


def test_local_chunking():
    """Test chunking on local markdown file"""
    print("=" * 80)
    print("TEST 1: Local Markdown Chunking")
    print("=" * 80)

    # Use the example file you provided
    local_md_path = "/Users/eliebruno/Desktop/code/project-2-rag/gaetan/02026_W42569266/document.md"

    if not Path(local_md_path).exists():
        print(f"❌ File not found: {local_md_path}")
        return False

    # Load markdown
    with open(local_md_path, 'r', encoding='utf-8') as f:
        markdown_text = f.read()

    print(f"✓ Loaded markdown: {len(markdown_text)} characters")

    # Initialize chunker
    chunker = MarkdownChunker(
        coarse_target_size=2000,
        coarse_max_size=2500,
        fine_target_size=300,
        fine_max_size=450,
        coarse_overlap_pct=0.10,
        fine_overlap_pct=0.20
    )
    print("✓ Initialized chunker")

    # Create chunks
    paper_id = "02026_W42569266"
    paper_title = "Intellectual Property and Human Security"

    results = chunker.chunk_document(markdown_text, paper_id, paper_title, create_both_types=True)

    coarse_chunks = results['coarse']
    fine_chunks = results['fine']

    print(f"✓ Created {len(coarse_chunks)} coarse chunks")
    print(f"✓ Created {len(fine_chunks)} fine chunks")

    # Print statistics
    coarse_stats = chunker.get_chunk_stats(coarse_chunks)
    fine_stats = chunker.get_chunk_stats(fine_chunks)

    print("\nCoarse Chunk Statistics:")
    print(f"  Mean size: {coarse_stats['mean_chars']:.0f} chars ({coarse_stats['mean_tokens']:.0f} tokens)")
    print(f"  Range: {coarse_stats['min_chars']} - {coarse_stats['max_chars']} chars")

    print("\nFine Chunk Statistics:")
    print(f"  Mean size: {fine_stats['mean_chars']:.0f} chars ({fine_stats['mean_tokens']:.0f} tokens)")
    print(f"  Range: {fine_stats['min_chars']} - {fine_stats['max_chars']} chars")

    # Show sample chunks
    print("\n" + "-" * 80)
    print("SAMPLE COARSE CHUNK:")
    print("-" * 80)
    print(f"ID: {coarse_chunks[0].chunk_id}")
    print(f"Section: {' > '.join(coarse_chunks[0].section_hierarchy)}")
    print(f"Size: {len(coarse_chunks[0].text)} chars")
    print(f"\nText preview:\n{coarse_chunks[0].text[:300]}...")

    print("\n" + "-" * 80)
    print("SAMPLE FINE CHUNK:")
    print("-" * 80)
    print(f"ID: {fine_chunks[0].chunk_id}")
    print(f"Section: {' > '.join(fine_chunks[0].section_hierarchy)}")
    print(f"Size: {len(fine_chunks[0].text)} chars")
    print(f"\nText:\n{fine_chunks[0].text}")

    print("\n✅ Test 1 PASSED\n")
    return True


def test_s3_loading():
    """Test S3 document loading"""
    print("=" * 80)
    print("TEST 2: S3 Document Loading")
    print("=" * 80)

    try:
        # Initialize loader
        loader = S3MarkdownLoader(bucket_name="cs433-rag-project2")
        print("✓ Initialized S3 loader")

        # List papers
        paper_ids = loader.list_paper_ids()
        print(f"✓ Found {len(paper_ids)} papers in S3")
        print(f"  First 5 papers: {paper_ids[:5]}")

        # Load first paper
        if paper_ids:
            test_paper_id = paper_ids[0]
            result = loader.load_paper(test_paper_id)

            if result:
                markdown_text, metadata = result
                title = loader.extract_title_from_metadata(metadata)

                print(f"\n✓ Loaded paper: {test_paper_id}")
                print(f"  Title: {title}")
                print(f"  Markdown size: {len(markdown_text)} chars")
                print(f"  Total pages: {metadata.get('total_pages', 'N/A')}")

                print("\n✅ Test 2 PASSED\n")
                return True
            else:
                print("❌ Failed to load paper")
                return False
        else:
            print("❌ No papers found")
            return False

    except Exception as e:
        print(f"❌ Test 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_s3_chunking_integration():
    """Test end-to-end: Load from S3 and chunk"""
    print("=" * 80)
    print("TEST 3: S3 + Chunking Integration")
    print("=" * 80)

    try:
        # Load from S3
        loader = S3MarkdownLoader(bucket_name="cs433-rag-project2")
        paper_ids = loader.list_paper_ids()

        if not paper_ids:
            print("❌ No papers found in S3")
            return False

        test_paper_id = paper_ids[0]
        result = loader.load_paper(test_paper_id)

        if not result:
            print("❌ Failed to load paper")
            return False

        markdown_text, metadata = result
        title = loader.extract_title_from_metadata(metadata)

        print(f"✓ Loaded paper from S3: {test_paper_id}")

        # Chunk it
        chunker = MarkdownChunker()
        chunks_result = chunker.chunk_document(
            markdown_text,
            test_paper_id,
            title,
            create_both_types=True
        )

        print(f"✓ Chunked into {len(chunks_result['coarse'])} coarse + {len(chunks_result['fine'])} fine chunks")

        # Verify chunk metadata
        sample_chunk = chunks_result['coarse'][0]
        assert sample_chunk.paper_id == test_paper_id
        assert sample_chunk.paper_title == title
        assert len(sample_chunk.section_hierarchy) > 0

        print(f"✓ Chunk metadata verified")
        print(f"  Paper ID: {sample_chunk.paper_id}")
        print(f"  Title: {sample_chunk.paper_title}")
        print(f"  Section: {' > '.join(sample_chunk.section_hierarchy)}")

        print("\n✅ Test 3 PASSED\n")
        return True

    except Exception as e:
        print(f"❌ Test 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("CHUNKING SYSTEM TEST SUITE")
    print("=" * 80 + "\n")

    tests = [
        ("Local Chunking", test_local_chunking),
        ("S3 Loading", test_s3_loading),
        ("S3 + Chunking Integration", test_s3_chunking_integration),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} CRASHED: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")

    if total_passed == len(results):
        print("\n🎉 All tests passed! System is ready to use.")
    else:
        print("\n⚠️  Some tests failed. Please review errors above.")

    return total_passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
