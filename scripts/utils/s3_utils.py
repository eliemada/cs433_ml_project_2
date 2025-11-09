"""S3 utility functions for distributed PDF processing."""

from typing import List
from botocore.exceptions import ClientError


def list_pdfs_from_s3(s3_client, bucket: str, prefix: str) -> List[str]:
    """
    List all PDF files from S3 bucket with given prefix.

    Args:
        s3_client: boto3 S3 client
        bucket: S3 bucket name
        prefix: Prefix to filter objects (e.g., 'pdfs/')

    Returns:
        Sorted list of PDF object keys
    """
    pdf_keys = []
    continuation_token = None

    while True:
        # Build list_objects_v2 parameters
        params = {
            'Bucket': bucket,
            'Prefix': prefix
        }

        if continuation_token:
            params['ContinuationToken'] = continuation_token

        # List objects
        response = s3_client.list_objects_v2(**params)

        # Extract keys
        if 'Contents' in response:
            for obj in response['Contents']:
                pdf_keys.append(obj['Key'])

        # Check for pagination
        if response.get('IsTruncated', False):
            continuation_token = response.get('NextContinuationToken')
        else:
            break

    # Return sorted list
    return sorted(pdf_keys)


def download_from_s3(s3_client, bucket: str, key: str, local_path: str) -> str:
    """
    Download file from S3 to local path.

    Args:
        s3_client: boto3 S3 client
        bucket: S3 bucket name
        key: S3 object key
        local_path: Local file path to save to

    Returns:
        Local file path
    """
    s3_client.download_file(bucket, key, local_path)
    return local_path


def upload_to_s3(s3_client, bucket: str, key: str, content: str) -> None:
    """
    Upload string content to S3.

    Args:
        s3_client: boto3 S3 client
        bucket: S3 bucket name
        key: S3 object key
        content: String content to upload
    """
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=content.encode('utf-8')
    )


def s3_object_exists(s3_client, bucket: str, key: str) -> bool:
    """
    Check if an object exists in S3.

    Args:
        s3_client: boto3 S3 client
        bucket: S3 bucket name
        key: S3 object key

    Returns:
        True if object exists, False otherwise
    """
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        raise
