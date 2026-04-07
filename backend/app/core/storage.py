"""MinIO S3-compatible storage client."""

import logging

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_s3_client():
    """Create and return a boto3 S3 client configured for MinIO."""
    protocol = "https" if settings.minio_use_ssl else "http"
    endpoint_url = f"{protocol}://{settings.minio_endpoint}"

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def ensure_bucket_exists() -> None:
    """Create the contracts bucket if it doesn't already exist."""
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.minio_bucket)
        logger.info("Bucket '%s' already exists", settings.minio_bucket)
    except ClientError:
        client.create_bucket(Bucket=settings.minio_bucket)
        logger.info("Created bucket '%s'", settings.minio_bucket)


def upload_file(file_bytes: bytes, object_name: str, content_type: str) -> str:
    """Upload a file to MinIO and return the object URL."""
    client = get_s3_client()
    client.put_object(
        Bucket=settings.minio_bucket,
        Key=object_name,
        Body=file_bytes,
        ContentType=content_type,
    )
    return f"{settings.minio_bucket}/{object_name}"


def download_file(object_name: str) -> bytes:
    """Download a file from MinIO and return its bytes."""
    client = get_s3_client()
    response = client.get_object(
        Bucket=settings.minio_bucket,
        Key=object_name,
    )
    return response["Body"].read()
