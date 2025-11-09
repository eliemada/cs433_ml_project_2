#!/usr/bin/env python3
"""
Distributed PDF processing worker.

Each worker processes a subset of PDFs from S3 in parallel.
"""

import os
import sys
import json
import tempfile
import logging
from pathlib import Path
from typing import List, Dict
import boto3

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils.s3_utils import (
    list_pdfs_from_s3,
    download_from_s3,
    upload_to_s3,
    s3_object_exists,
)
from scripts.utils.worker_distribution import get_worker_pdfs, get_output_key
from rag_pipeline.pdf_parsing.core.pipeline import PDFParsingPipeline
from rag_pipeline.pdf_parsing.config import PDFParsingConfig


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[Worker %(worker_id)s] %(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


class DistributedWorker:
    """Worker for distributed PDF processing."""

    def __init__(self):
        """Initialize worker from environment variables."""
        self.worker_id = int(os.getenv('WORKER_ID', '0'))
        self.total_workers = int(os.getenv('TOTAL_WORKERS', '1'))
        self.s3_input_bucket = os.getenv('S3_INPUT_BUCKET')
        self.s3_input_prefix = os.getenv('S3_INPUT_PREFIX', 'pdfs/')
        self.s3_output_bucket = os.getenv('S3_OUTPUT_BUCKET')
        self.s3_output_prefix = os.getenv('S3_OUTPUT_PREFIX', 'processed/')
        self.max_retries = int(os.getenv('MAX_RETRIES', '2'))

        # Validate configuration
        if not self.s3_input_bucket:
            raise ValueError("S3_INPUT_BUCKET environment variable required")
        if not self.s3_output_bucket:
            raise ValueError("S3_OUTPUT_BUCKET environment variable required")

        # Initialize S3 client
        self.s3 = boto3.client('s3')

        # Initialize PDF parsing pipeline
        self.config = PDFParsingConfig()
        self.pipeline = None  # Lazy load to avoid loading model unless needed

        # Track failures
        self.failures: List[Dict] = []

        # Setup logging with worker ID
        self.logger = logging.getLogger(__name__)
        self.logger = logging.LoggerAdapter(
            self.logger,
            {'worker_id': self.worker_id}
        )

    def get_pipeline(self) -> PDFParsingPipeline:
        """Lazy load PDF parsing pipeline."""
        if self.pipeline is None:
            self.logger.info("Initializing PDF parsing pipeline with Dolphin model...")
            self.pipeline = PDFParsingPipeline(self.config)
            self.logger.info("Pipeline initialized successfully")
        return self.pipeline

    def process_pdf(self, pdf_key: str) -> bool:
        """
        Process a single PDF.

        Args:
            pdf_key: S3 key of PDF file

        Returns:
            True if successful, False otherwise
        """
        output_key = get_output_key(pdf_key, self.s3_input_prefix, self.s3_output_prefix)

        # Check if already processed
        if s3_object_exists(self.s3, self.s3_output_bucket, output_key):
            self.logger.info(f"Skipping {pdf_key} (already processed)")
            return True

        # Download PDF to temporary file
        with tempfile.TemporaryDirectory() as tmpdir:
            local_pdf = Path(tmpdir) / Path(pdf_key).name

            try:
                self.logger.info(f"Downloading {pdf_key}...")
                download_from_s3(
                    self.s3,
                    self.s3_input_bucket,
                    pdf_key,
                    str(local_pdf)
                )

                # Process with Dolphin model
                self.logger.info(f"Processing {pdf_key} with Dolphin...")
                pipeline = self.get_pipeline()
                result = pipeline.parse_document(local_pdf)

                # Get markdown output
                markdown_path = self.config.output.get_markdown_path(local_pdf)
                if not markdown_path.exists():
                    raise FileNotFoundError(f"Markdown not generated: {markdown_path}")

                markdown_content = markdown_path.read_text()

                # Upload to S3
                self.logger.info(f"Uploading {output_key}...")
                upload_to_s3(
                    self.s3,
                    self.s3_output_bucket,
                    output_key,
                    markdown_content
                )

                self.logger.info(f"✓ Successfully processed {pdf_key}")
                return True

            except Exception as e:
                self.logger.error(f"✗ Failed to process {pdf_key}: {e}")
                self.failures.append({
                    'pdf_key': pdf_key,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                return False

    def run(self):
        """Main worker processing loop."""
        self.logger.info(f"Starting distributed worker {self.worker_id}/{self.total_workers}")
        self.logger.info(f"Input: s3://{self.s3_input_bucket}/{self.s3_input_prefix}")
        self.logger.info(f"Output: s3://{self.s3_output_bucket}/{self.s3_output_prefix}")

        # List all PDFs
        self.logger.info("Listing PDFs from S3...")
        all_pdfs = list_pdfs_from_s3(self.s3, self.s3_input_bucket, self.s3_input_prefix)
        self.logger.info(f"Found {len(all_pdfs)} total PDFs")

        # Get this worker's slice
        my_pdfs = get_worker_pdfs(all_pdfs, self.worker_id, self.total_workers)
        self.logger.info(f"Assigned {len(my_pdfs)} PDFs to this worker")

        if not my_pdfs:
            self.logger.info("No PDFs assigned to this worker - exiting")
            return

        # Process each PDF
        successful = 0
        failed = 0

        for i, pdf_key in enumerate(my_pdfs, 1):
            self.logger.info(f"Progress: {i}/{len(my_pdfs)} ({i*100//len(my_pdfs)}%)")

            if self.process_pdf(pdf_key):
                successful += 1
            else:
                failed += 1

        # Upload failure report if any
        if self.failures:
            self.upload_failure_report()

        # Summary
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Worker {self.worker_id} completed!")
        self.logger.info(f"  Successful: {successful}/{len(my_pdfs)}")
        self.logger.info(f"  Failed: {failed}/{len(my_pdfs)}")
        self.logger.info(f"{'='*60}\n")

        # Exit with error code if any failures
        if failed > 0:
            sys.exit(1)

    def upload_failure_report(self):
        """Upload failure report to S3."""
        failure_key = f"failures/worker-{self.worker_id}-failures.json"

        report = {
            'worker_id': self.worker_id,
            'total_workers': self.total_workers,
            'failures': self.failures
        }

        try:
            upload_to_s3(
                self.s3,
                self.s3_output_bucket,
                failure_key,
                json.dumps(report, indent=2)
            )
            self.logger.info(f"Uploaded failure report to s3://{self.s3_output_bucket}/{failure_key}")
        except Exception as e:
            self.logger.error(f"Failed to upload failure report: {e}")


def main():
    """Main entry point."""
    try:
        worker = DistributedWorker()
        worker.run()
    except Exception as e:
        logging.error(f"Worker failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
