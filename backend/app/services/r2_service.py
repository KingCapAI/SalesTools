"""Cloudflare R2 storage service (S3-compatible)."""

import asyncio
from typing import Optional
from functools import lru_cache

from ..config import get_settings

settings = get_settings()


@lru_cache()
def get_r2_client():
    """Get a cached boto3 S3 client configured for Cloudflare R2."""
    import boto3
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )


def _use_r2() -> bool:
    """Check if R2 is configured."""
    return bool(
        settings.r2_account_id
        and settings.r2_access_key_id
        and settings.r2_secret_access_key
        and settings.r2_bucket_name
    )


async def upload_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Upload bytes to R2. Returns the key."""
    client = get_r2_client()
    await asyncio.to_thread(
        client.put_object,
        Bucket=settings.r2_bucket_name,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return key


async def download_bytes(key: str) -> Optional[bytes]:
    """Download an object from R2 as bytes. Returns None if not found."""
    try:
        client = get_r2_client()
        response = await asyncio.to_thread(
            client.get_object,
            Bucket=settings.r2_bucket_name,
            Key=key,
        )
        return response["Body"].read()
    except Exception as e:
        error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', '')
        if error_code == 'NoSuchKey':
            return None
        print(f"[R2] Error downloading {key}: {e}")
        return None


def delete_object(key: str) -> bool:
    """Delete an object from R2."""
    try:
        client = get_r2_client()
        client.delete_object(Bucket=settings.r2_bucket_name, Key=key)
        return True
    except Exception as e:
        print(f"[R2] Error deleting {key}: {e}")
        return False


def get_public_url(key: str) -> str:
    """Get the public URL for an R2 object."""
    # Strip leading /uploads/ prefix if present (legacy path format)
    clean_key = key.lstrip("/")
    if clean_key.startswith("uploads/"):
        clean_key = clean_key[len("uploads/"):]
    return f"{settings.r2_public_url}/{clean_key}"
