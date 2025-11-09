"""Tests for worker distribution logic."""

import unittest


class TestWorkerDistribution(unittest.TestCase):
    """Test work distribution logic for parallel processing."""

    def test_get_worker_pdfs_distributes_evenly_with_5_workers(self):
        """get_worker_pdfs should distribute PDFs evenly using modulo."""
        from scripts.utils.worker_distribution import get_worker_pdfs

        all_pdfs = [
            'pdf_00.pdf', 'pdf_01.pdf', 'pdf_02.pdf', 'pdf_03.pdf', 'pdf_04.pdf',
            'pdf_05.pdf', 'pdf_06.pdf', 'pdf_07.pdf', 'pdf_08.pdf', 'pdf_09.pdf',
        ]

        # Worker 0 should get indices 0, 5
        worker_0_pdfs = get_worker_pdfs(all_pdfs, worker_id=0, total_workers=5)
        self.assertEqual(worker_0_pdfs, ['pdf_00.pdf', 'pdf_05.pdf'])

        # Worker 1 should get indices 1, 6
        worker_1_pdfs = get_worker_pdfs(all_pdfs, worker_id=1, total_workers=5)
        self.assertEqual(worker_1_pdfs, ['pdf_01.pdf', 'pdf_06.pdf'])

        # Worker 2 should get indices 2, 7
        worker_2_pdfs = get_worker_pdfs(all_pdfs, worker_id=2, total_workers=5)
        self.assertEqual(worker_2_pdfs, ['pdf_02.pdf', 'pdf_07.pdf'])

        # Worker 3 should get indices 3, 8
        worker_3_pdfs = get_worker_pdfs(all_pdfs, worker_id=3, total_workers=5)
        self.assertEqual(worker_3_pdfs, ['pdf_03.pdf', 'pdf_08.pdf'])

        # Worker 4 should get indices 4, 9
        worker_4_pdfs = get_worker_pdfs(all_pdfs, worker_id=4, total_workers=5)
        self.assertEqual(worker_4_pdfs, ['pdf_04.pdf', 'pdf_09.pdf'])

    def test_get_worker_pdfs_handles_uneven_distribution(self):
        """get_worker_pdfs should handle when PDFs don't divide evenly."""
        from scripts.utils.worker_distribution import get_worker_pdfs

        # 7 PDFs with 3 workers
        all_pdfs = ['p0.pdf', 'p1.pdf', 'p2.pdf', 'p3.pdf', 'p4.pdf', 'p5.pdf', 'p6.pdf']

        worker_0 = get_worker_pdfs(all_pdfs, worker_id=0, total_workers=3)
        worker_1 = get_worker_pdfs(all_pdfs, worker_id=1, total_workers=3)
        worker_2 = get_worker_pdfs(all_pdfs, worker_id=2, total_workers=3)

        # Worker 0: indices 0, 3, 6 (3 PDFs)
        self.assertEqual(worker_0, ['p0.pdf', 'p3.pdf', 'p6.pdf'])

        # Worker 1: indices 1, 4 (2 PDFs)
        self.assertEqual(worker_1, ['p1.pdf', 'p4.pdf'])

        # Worker 2: indices 2, 5 (2 PDFs)
        self.assertEqual(worker_2, ['p2.pdf', 'p5.pdf'])

        # All PDFs should be assigned exactly once
        all_assigned = worker_0 + worker_1 + worker_2
        self.assertEqual(sorted(all_assigned), sorted(all_pdfs))

    def test_get_worker_pdfs_returns_empty_for_worker_beyond_pdf_count(self):
        """get_worker_pdfs should return empty list if worker_id >= number of PDFs."""
        from scripts.utils.worker_distribution import get_worker_pdfs

        all_pdfs = ['p1.pdf', 'p2.pdf']

        # With 5 workers, workers 2, 3, 4 get nothing
        worker_2 = get_worker_pdfs(all_pdfs, worker_id=2, total_workers=5)
        worker_3 = get_worker_pdfs(all_pdfs, worker_id=3, total_workers=5)
        worker_4 = get_worker_pdfs(all_pdfs, worker_id=4, total_workers=5)

        self.assertEqual(worker_2, [])
        self.assertEqual(worker_3, [])
        self.assertEqual(worker_4, [])

    def test_get_worker_pdfs_handles_single_worker(self):
        """get_worker_pdfs should return all PDFs when total_workers=1."""
        from scripts.utils.worker_distribution import get_worker_pdfs

        all_pdfs = ['p1.pdf', 'p2.pdf', 'p3.pdf']

        worker_0 = get_worker_pdfs(all_pdfs, worker_id=0, total_workers=1)

        self.assertEqual(worker_0, all_pdfs)

    def test_extract_pdf_id_from_filename(self):
        """extract_pdf_id should extract the ID from PDF filename."""
        from scripts.utils.worker_distribution import extract_pdf_id

        # Real examples
        pdf_id = extract_pdf_id('00002_W2122361802_Navigating_the_Patent_Thicket.pdf')
        self.assertEqual(pdf_id, '00002_W2122361802')

        pdf_id = extract_pdf_id('00004_W2114989862_Some_Paper_Title.pdf')
        self.assertEqual(pdf_id, '00004_W2114989862')

        # With path
        pdf_id = extract_pdf_id('raw_pdfs/00007_W2150316800_Title.pdf')
        self.assertEqual(pdf_id, '00007_W2150316800')

    def test_get_output_key_converts_pdf_to_folder_with_document_md(self):
        """get_output_key should create folder structure with document.md."""
        from scripts.utils.worker_distribution import get_output_key

        # Real example: extract ID and create folder/document.md
        output = get_output_key(
            'raw_pdfs/00002_W2122361802_Navigating_the_Patent_Thicket.pdf',
            'raw_pdfs/',
            'processed/'
        )
        self.assertEqual(output, 'processed/00002_W2122361802/document.md')

        # Another example
        output = get_output_key(
            'raw_pdfs/00004_W2114989862_Some_Paper_Title.pdf',
            'raw_pdfs/',
            'processed/'
        )
        self.assertEqual(output, 'processed/00004_W2114989862/document.md')

        # Edge case: PDF with no prefix
        output = get_output_key(
            '12345_W9999999999_Paper.pdf',
            '',
            'output/'
        )
        self.assertEqual(output, 'output/12345_W9999999999/document.md')


if __name__ == '__main__':
    unittest.main()
