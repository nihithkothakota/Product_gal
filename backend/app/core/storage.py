"""
S3-compatible object storage client for product images and screenshots.
Works with AWS S3 in production and MinIO in development.
"""

import io
from uuid import uuid4

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.config import get_settings

settings = get_settings()


def _get_s3_client():
    """Create an S3 client configured for the current environment."""
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=BotoConfig(signature_version="s3v4"),
    )


def ensure_bucket_exists() -> None:
    """Create the bucket if it doesn't exist (useful for local dev with MinIO)."""
    client = _get_s3_client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket_name)
    except ClientError:
        client.create_bucket(Bucket=settings.s3_bucket_name)


def upload_image(image_bytes: bytes, content_type: str = "image/jpeg", prefix: str = "products") -> str:
    """
    Upload an image to S3 and return the object key.

    Args:
        image_bytes: Raw image bytes.
        content_type: MIME type of the image.
        prefix: S3 key prefix (folder).

    Returns:
        The S3 object key (e.g., "products/abc123.jpg").
    """
    ext = content_type.split("/")[-1] if "/" in content_type else "jpg"
    key = f"{prefix}/{uuid4().hex}.{ext}"

    client = _get_s3_client()
    client.upload_fileobj(
        io.BytesIO(image_bytes),
        settings.s3_bucket_name,
        key,
        ExtraArgs={"ContentType": content_type},
    )
    return key


def generate_presigned_url(key: str) -> str:
    """Generate a time-limited presigned URL for reading an S3 object."""
    client = _get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket_name, "Key": key},
        ExpiresIn=settings.s3_presigned_url_expire,
    )


def delete_object(key: str) -> None:
    """Delete an object from S3."""
    client = _get_s3_client()
    client.delete_object(Bucket=settings.s3_bucket_name, Key=key)
