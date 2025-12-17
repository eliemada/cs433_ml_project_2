#!/usr/bin/env python3
"""Batch PDF processing script for vast.ai deployment."""

import json
import os
import queue
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError
from loguru import logger

from rag_pipeline.pdf_parsing import (
    PDFParsingConfig,
    PDFParsingPipeline,
    DolphinModelConfig,
    OutputConfig,
)

# Configure loguru for production use
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO",
)
logger.add(
    "/tmp/pdf_processing.log",
    rotation="100 MB",
    retention="1 day",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="DEBUG",
)


def get_doc_id(s3_key: str) -> str:
    """Extract document ID from S3 key.

    Example: 'raw_pdfs/00347_W3004748802_Small_firms.pdf' -> '00347_W3004748802'
    """
    filename = Path(s3_key).stem
    # Extract ID pattern: {index}_{work_id}
    parts = filename.split("_")
    if len(parts) >= 2:
        return f"{parts[0]}_{parts[1]}"
    return filename


def list_s3_files(s3_client, bucket: str, prefix: str) -> List[str]:
    """List all files under S3 prefix."""
    files = []
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        if "Contents" in page:
            files.extend([obj["Key"] for obj in page["Contents"]])
    return files


def list_s3_folders(s3_client, bucket: str, prefix: str) -> set:
    """List all folder names under S3 prefix."""
    folders = set()
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter="/"):
        if "CommonPrefixes" in page:
            for prefix_info in page["CommonPrefixes"]:
                folder_name = prefix_info["Prefix"].rstrip("/").split("/")[-1]
                folders.add(folder_name)
    return folders


def find_unprocessed_pdfs(s3_client, bucket: str) -> List[str]:
    """Find PDFs that haven't been processed yet."""
    logger.info("Finding unprocessed PDFs...")
    all_pdfs = [f for f in list_s3_files(s3_client, bucket, "raw_pdfs/") if f.endswith(".pdf")]
    processed_ids = list_s3_folders(s3_client, bucket, "processed/")

    unprocessed = [pdf for pdf in all_pdfs if get_doc_id(pdf) not in processed_ids]

    logger.info(f"Total PDFs: {len(all_pdfs)}")
    logger.info(f"Already processed: {len(processed_ids)}")
    logger.info(f"To process: {len(unprocessed)}")

    return unprocessed


def download_from_s3(s3_client, bucket: str, s3_key: str, local_path: Path) -> Path:
    """Download file from S3 to local path."""
    local_path.parent.mkdir(parents=True, exist_ok=True)
    s3_client.download_file(bucket, s3_key, str(local_path))
    return local_path


def upload_to_s3(s3_client, bucket: str, local_path: Path, s3_key: str):
    """Upload file from local path to S3."""
    s3_client.upload_file(str(local_path), bucket, s3_key)


def upload_results(s3_client, bucket: str, doc_id: str, output_dir: Path):
    """Upload all processing results for a document to S3."""
    base_prefix = f"processed/{doc_id}/"

    # Upload markdown
    md_file = output_dir / "markdown" / f"{doc_id}.md"
    if md_file.exists():
        upload_to_s3(s3_client, bucket, md_file, f"{base_prefix}document.md")

    # Upload JSON
    json_file = output_dir / "recognition_json" / f"{doc_id}.json"
    if json_file.exists():
        upload_to_s3(s3_client, bucket, json_file, f"{base_prefix}metadata.json")

    # Upload figures
    figures_dir = output_dir / "markdown" / "figures"
    if figures_dir.exists():
        for fig in figures_dir.iterdir():
            if fig.is_file():
                s3_key = f"{base_prefix}figures/{fig.name}"
                upload_to_s3(s3_client, bucket, fig, s3_key)


def main():
    """Main processing loop with pipeline parallelism."""
    # Get config from environment
    bucket = os.environ.get("S3_BUCKET", "cs433-rag-project2")
    logger.info(f"Using S3 bucket: {bucket}")

    # Initialize S3 client
    s3_client = boto3.client("s3")

    # Find unprocessed PDFs
    unprocessed = find_unprocessed_pdfs(s3_client, bucket)

    if not unprocessed:
        logger.warning("No PDFs to process!")
        return

    # Initialize pipeline
    logger.info("Initializing PDF parsing pipeline...")
    config = PDFParsingConfig(
        model=DolphinModelConfig(model_path=Path("/app/models/dolphin")),
        output=OutputConfig(output_dir=Path("/tmp/output")),
    )
    pipeline = PDFParsingPipeline(config)
    logger.success("Pipeline initialized successfully")

    # Pipeline queues
    download_queue = queue.Queue(maxsize=2)
    process_queue = queue.Queue(maxsize=2)
    failed = []

    # Stage 1: Download thread
    def downloader():
        for pdf_key in unprocessed:
            doc_id = get_doc_id(pdf_key)
            local_pdf = Path(f"/tmp/downloads/{doc_id}.pdf")
            try:
                download_from_s3(s3_client, bucket, pdf_key, local_pdf)
                download_queue.put((doc_id, local_pdf))
                logger.info(f"Downloaded: {doc_id}")
            except Exception as e:
                logger.error(f"Download failed for {doc_id}: {e}")
                failed.append({"doc_id": doc_id, "error": f"Download: {str(e)}"})
        download_queue.put(None)  # Signal completion
        logger.info("Download stage completed")

    # Stage 2: Process on GPU (main thread)
    def processor():
        processed_count = 0
        while True:
            item = download_queue.get()
            if item is None:
                process_queue.put(None)
                logger.info(f"Processing stage completed. Processed {processed_count} documents")
                break

            doc_id, local_pdf = item
            try:
                logger.info(f"Processing: {doc_id}")
                result = pipeline.parse_document(local_pdf)
                process_queue.put((doc_id, None))
                processed_count += 1
                logger.success(f"Parsed: {doc_id} ({processed_count}/{len(unprocessed)})")
            except Exception as e:
                logger.error(f"Processing failed for {doc_id}: {e}")
                process_queue.put((doc_id, str(e)))
            finally:
                # Clean up local PDF
                if local_pdf.exists():
                    local_pdf.unlink()

    # Stage 3: Upload thread
    def uploader():
        uploaded_count = 0
        while True:
            item = process_queue.get()
            if item is None:
                logger.info(f"Upload stage completed. Uploaded {uploaded_count} documents")
                break

            doc_id, error = item
            if error:
                failed.append({"doc_id": doc_id, "error": f"Processing: {error}"})
            else:
                try:
                    output_dir = Path("/tmp/output")
                    upload_results(s3_client, bucket, doc_id, output_dir)
                    uploaded_count += 1
                    logger.success(f"Uploaded: {doc_id}")

                    # Clean up local output
                    for subdir in ["markdown", "recognition_json"]:
                        path = output_dir / subdir
                        if path.exists():
                            for f in path.rglob("*"):
                                if f.is_file():
                                    f.unlink()
                except Exception as e:
                    logger.error(f"Upload failed for {doc_id}: {e}")
                    failed.append({"doc_id": doc_id, "error": f"Upload: {str(e)}"})

    # Run pipeline
    logger.info(f"Starting pipeline for {len(unprocessed)} PDFs...")
    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(downloader)
        executor.submit(uploader)
        processor()  # Run on main thread

    # Upload failed list if any
    if failed:
        logger.warning(f"{len(failed)} documents failed:")
        for item in failed:
            logger.warning(f"  - {item['doc_id']}: {item['error']}")

        failed_json = json.dumps(failed, indent=2)
        s3_client.put_object(
            Bucket=bucket, Key="processing_logs/failed_docs.json", Body=failed_json
        )
        logger.info("Failed documents log uploaded to S3: processing_logs/failed_docs.json")
    else:
        logger.success("All documents processed successfully!")

    # Cleanup
    pipeline.unload_model()
    logger.success("Processing complete!")


if __name__ == "__main__":
    main()
