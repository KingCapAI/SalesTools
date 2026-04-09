"""File storage service for handling uploads — uses Cloudflare R2 when configured, local disk as fallback."""

import os
import uuid
import base64
import mimetypes
from pathlib import Path
from typing import Optional, Tuple, Union

from fastapi import UploadFile

from ..config import get_settings
from . import r2_service

settings = get_settings()


def generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename while preserving extension."""
    ext = Path(original_filename).suffix.lower()
    unique_id = str(uuid.uuid4())
    return f"{unique_id}{ext}"


def _normalize_key(path: str) -> str:
    """Normalize a stored path to a clean R2 key (no leading slash or 'uploads/' prefix)."""
    clean = path.lstrip("/")
    if clean.startswith("uploads/"):
        clean = clean[len("uploads/"):]
    return clean


# --- Public API ---


async def save_upload_file(
    file: UploadFile,
    subdir: str,
    allowed_types: Optional[list] = None,
    max_size_mb: Optional[int] = None,
) -> Tuple[str, str, int]:
    """
    Save an uploaded file.

    Returns:
        Tuple of (relative_path, mime_type, file_size)
    """
    if allowed_types and file.content_type not in allowed_types:
        raise ValueError(f"File type {file.content_type} not allowed. Allowed types: {allowed_types}")

    content = await file.read()
    file_size = len(content)

    max_size = (max_size_mb or settings.max_file_size_mb) * 1024 * 1024
    if file_size > max_size:
        raise ValueError(f"File size exceeds maximum allowed ({max_size_mb or settings.max_file_size_mb}MB)")

    filename = generate_unique_filename(file.filename or "upload")
    relative_path = f"{subdir}/{filename}"

    if r2_service._use_r2():
        await r2_service.upload_bytes(relative_path, content, file.content_type or "application/octet-stream")
    else:
        _save_local(relative_path, content)

    return relative_path, file.content_type, file_size


async def save_file_bytes(
    data: bytes,
    subdir: str,
    filename: str,
    content_type: str = "application/octet-stream",
) -> str:
    """
    Save raw bytes to storage.

    Returns:
        The relative path (e.g. 'location_logos/uuid.png')
    """
    relative_path = f"{subdir}/{filename}"

    if r2_service._use_r2():
        await r2_service.upload_bytes(relative_path, data, content_type)
    else:
        _save_local(relative_path, data)

    return relative_path


async def save_generated_image(
    image_data: Union[bytes, str],
    design_id: str,
    version_number: int,
) -> str:
    """Save a generated design image. Returns the relative file path."""
    filename = f"{design_id}_v{version_number}.png"
    relative_path = f"generated_designs/{filename}"

    if isinstance(image_data, str):
        image_data = base64.b64decode(image_data)

    if r2_service._use_r2():
        await r2_service.upload_bytes(relative_path, image_data, "image/png")
    else:
        _save_local(relative_path, image_data)

    return relative_path


async def read_file_bytes(relative_path: str) -> Optional[bytes]:
    """Read a file's bytes from storage. Returns None if not found."""
    key = _normalize_key(relative_path)

    if r2_service._use_r2():
        return await r2_service.download_bytes(key)
    else:
        full_path = Path(settings.upload_dir) / key
        if full_path.exists():
            return full_path.read_bytes()
        return None


def delete_file(relative_path: str) -> bool:
    """Delete a file from storage."""
    key = _normalize_key(relative_path)

    if r2_service._use_r2():
        return r2_service.delete_object(key)
    else:
        try:
            full_path = Path(settings.upload_dir) / key
            if full_path.exists():
                full_path.unlink()
                return True
        except Exception:
            pass
        return False


def get_file_url(relative_path: str) -> str:
    """Get the public URL for a file."""
    key = _normalize_key(relative_path)

    if r2_service._use_r2():
        return r2_service.get_public_url(key)
    else:
        return f"{settings.backend_url}/api/uploads/{key}"


# --- Local filesystem fallback ---


def _save_local(relative_path: str, data: bytes):
    """Save bytes to local filesystem."""
    full_path = Path(settings.upload_dir) / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(data)
