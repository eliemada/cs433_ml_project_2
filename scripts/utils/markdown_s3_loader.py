"""
AWS S3 utilities for loading markdown documents and metadata.
"""

import boto3
import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import io


class S3MarkdownLoader:
    """Load markdown documents and metadata from S3"""

    def __init__(self, bucket_name: str, prefix: str = "processed/"):
        """
        Initialize S3 loader.

        Args:
            bucket_name: S3 bucket name
            prefix: Prefix for processed documents
        """
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.s3_client = boto3.client('s3')

    def list_paper_ids(self) -> List[str]:
        """
        List all paper IDs in the bucket.

        Returns:
            List of paper IDs (folder names like "00002_W2122361802")
        """
        response = self.s3_client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=self.prefix,
            Delimiter='/'
        )

        paper_ids = []
        for prefix in response.get('CommonPrefixes', []):
            folder_name = prefix['Prefix'].rstrip('/').split('/')[-1]
            paper_ids.append(folder_name)

        return sorted(paper_ids)

    def load_document(self, paper_id: str) -> Optional[str]:
        """
        Load markdown document for a paper.

        Args:
            paper_id: Paper ID (folder name)

        Returns:
            Markdown text or None if not found
        """
        key = f"{self.prefix}{paper_id}/document.md"

        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            markdown_text = response['Body'].read().decode('utf-8')
            return markdown_text
        except self.s3_client.exceptions.NoSuchKey:
            print(f"Document not found: {key}")
            return None
        except Exception as e:
            print(f"Error loading document {key}: {e}")
            return None

    def load_metadata(self, paper_id: str) -> Optional[Dict]:
        """
        Load metadata JSON for a paper.

        Args:
            paper_id: Paper ID (folder name)

        Returns:
            Metadata dict or None if not found
        """
        key = f"{self.prefix}{paper_id}/metadata.json"

        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            metadata = json.loads(response['Body'].read().decode('utf-8'))
            return metadata
        except self.s3_client.exceptions.NoSuchKey:
            print(f"Metadata not found: {key}")
            return None
        except Exception as e:
            print(f"Error loading metadata {key}: {e}")
            return None

    def load_paper(self, paper_id: str) -> Optional[Tuple[str, Dict]]:
        """
        Load both document and metadata for a paper.

        Args:
            paper_id: Paper ID (folder name)

        Returns:
            Tuple of (markdown_text, metadata) or None if not found
        """
        markdown_text = self.load_document(paper_id)
        metadata = self.load_metadata(paper_id)

        if markdown_text is None or metadata is None:
            return None

        return markdown_text, metadata

    def extract_title_from_metadata(self, metadata: Dict) -> str:
        """
        Extract paper title from metadata.

        Args:
            metadata: Metadata dict

        Returns:
            Paper title or "Unknown Title"
        """
        # Try to find title in page elements
        if 'pages' in metadata and len(metadata['pages']) > 0:
            first_page = metadata['pages'][0]
            if 'elements' in first_page:
                for element in first_page['elements']:
                    # Look for title-like elements
                    if element.get('label', '').startswith('sec_0') or \
                       element.get('label', '') == 'title':
                        return element.get('text', 'Unknown Title').strip()

        # Fallback: use source filename
        if 'source_file' in metadata:
            return Path(metadata['source_file']).stem

        return "Unknown Title"

    def save_chunks_to_s3(
        self,
        chunks: List[Dict],
        paper_id: str,
        chunk_type: str,
        output_prefix: str = "chunks/"
    ):
        """
        Save chunks to S3 as JSON.

        Args:
            chunks: List of chunk dicts
            paper_id: Paper ID
            chunk_type: "coarse" or "fine"
            output_prefix: S3 prefix for output
        """
        key = f"{output_prefix}{paper_id}_{chunk_type}_chunks.json"

        try:
            json_data = json.dumps(chunks, indent=2)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json_data.encode('utf-8'),
                ContentType='application/json'
            )
            print(f"Saved {len(chunks)} {chunk_type} chunks to s3://{self.bucket_name}/{key}")
        except Exception as e:
            print(f"Error saving chunks to S3: {e}")

    def download_sample_papers(
        self,
        num_papers: int,
        output_dir: str = "./sample_papers"
    ) -> List[str]:
        """
        Download sample papers for local testing.

        Args:
            num_papers: Number of papers to download
            output_dir: Local directory to save papers

        Returns:
            List of downloaded paper IDs
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        paper_ids = self.list_paper_ids()[:num_papers]

        for paper_id in paper_ids:
            # Create paper directory
            paper_dir = output_path / paper_id
            paper_dir.mkdir(exist_ok=True)

            # Download document
            markdown_text = self.load_document(paper_id)
            if markdown_text:
                (paper_dir / "document.md").write_text(markdown_text, encoding='utf-8')

            # Download metadata
            metadata = self.load_metadata(paper_id)
            if metadata:
                (paper_dir / "metadata.json").write_text(
                    json.dumps(metadata, indent=2),
                    encoding='utf-8'
                )

            print(f"Downloaded {paper_id}")

        return paper_ids
