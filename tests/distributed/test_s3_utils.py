"""Tests for S3 utility functions."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os


class TestS3Utils(unittest.TestCase):
    """Test S3 utility functions."""

    def test_list_pdfs_from_s3_returns_sorted_pdf_keys(self):
        """list_pdfs_from_s3 should return sorted list of PDF object keys."""
        # Import will fail initially - that's expected (RED phase)
        from scripts.utils.s3_utils import list_pdfs_from_s3

        # Mock S3 client
        mock_s3 = Mock()
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'pdfs/paper_003.pdf'},
                {'Key': 'pdfs/paper_001.pdf'},
                {'Key': 'pdfs/paper_002.pdf'},
            ]
        }

        result = list_pdfs_from_s3(mock_s3, 'test-bucket', 'pdfs/')

        # Should return sorted list
        expected = [
            'pdfs/paper_001.pdf',
            'pdfs/paper_002.pdf',
            'pdfs/paper_003.pdf',
        ]
        self.assertEqual(result, expected)

    def test_list_pdfs_handles_pagination(self):
        """list_pdfs_from_s3 should handle paginated responses."""
        from scripts.utils.s3_utils import list_pdfs_from_s3

        mock_s3 = Mock()
        # Simulate pagination with IsTruncated
        mock_s3.list_objects_v2.side_effect = [
            {
                'Contents': [{'Key': 'pdfs/page1.pdf'}],
                'IsTruncated': True,
                'NextContinuationToken': 'token123'
            },
            {
                'Contents': [{'Key': 'pdfs/page2.pdf'}],
                'IsTruncated': False
            }
        ]

        result = list_pdfs_from_s3(mock_s3, 'test-bucket', 'pdfs/')

        # Should return all results from both pages
        self.assertEqual(len(result), 2)
        self.assertIn('pdfs/page1.pdf', result)
        self.assertIn('pdfs/page2.pdf', result)

    def test_download_from_s3_saves_file_locally(self):
        """download_from_s3 should download object and save to local path."""
        from scripts.utils.s3_utils import download_from_s3

        mock_s3 = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = os.path.join(tmpdir, 'test.pdf')

            result = download_from_s3(
                mock_s3,
                'test-bucket',
                'pdfs/paper.pdf',
                local_path
            )

            # Should call download_file with correct params
            mock_s3.download_file.assert_called_once_with(
                'test-bucket',
                'pdfs/paper.pdf',
                local_path
            )

            # Should return the local path
            self.assertEqual(result, local_path)

    def test_upload_to_s3_uploads_content(self):
        """upload_to_s3 should upload string content to S3."""
        from scripts.utils.s3_utils import upload_to_s3

        mock_s3 = Mock()
        content = "# Markdown content\n\nThis is a test."

        upload_to_s3(mock_s3, 'test-bucket', 'output/test.md', content)

        # Should call put_object with correct params
        mock_s3.put_object.assert_called_once_with(
            Bucket='test-bucket',
            Key='output/test.md',
            Body=content.encode('utf-8')
        )

    def test_s3_object_exists_returns_true_when_object_exists(self):
        """s3_object_exists should return True if object exists."""
        from scripts.utils.s3_utils import s3_object_exists

        mock_s3 = Mock()
        mock_s3.head_object.return_value = {'ContentLength': 1234}

        result = s3_object_exists(mock_s3, 'test-bucket', 'pdfs/exists.pdf')

        self.assertTrue(result)
        mock_s3.head_object.assert_called_once_with(
            Bucket='test-bucket',
            Key='pdfs/exists.pdf'
        )

    def test_s3_object_exists_returns_false_when_object_missing(self):
        """s3_object_exists should return False if object doesn't exist."""
        from scripts.utils.s3_utils import s3_object_exists

        mock_s3 = Mock()
        # Simulate 404 error
        from botocore.exceptions import ClientError
        mock_s3.head_object.side_effect = ClientError(
            {'Error': {'Code': '404'}},
            'head_object'
        )

        result = s3_object_exists(mock_s3, 'test-bucket', 'pdfs/missing.pdf')

        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
