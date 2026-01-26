"""File storage service for handling uploads."""

import os
import uuid
import base64
import aiofiles
from pathlib import Path
from typing import Optional, Tuple, Union
from fastapi import UploadFile

from ..config import get_settings

settings = get_settings()


def get_upload_path(subdir: str) -> Path:
    """Get the full path for an upload subdirectory."""
    base_path = Path(settings.upload_dir)
    full_path = base_path / subdir
    full_path.mkdir(parents=True, exist_ok=True)
    return full_path


def generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename while preserving extension."""
    ext = Path(original_filename).suffix.lower()
    unique_id = str(uuid.uuid4())
    return f"{unique_id}{ext}"


async def save_upload_file(
    file: UploadFile,
    subdir: str,
    allowed_types: Optional[list] = None,
    max_size_mb: Optional[int] = None,
) -> Tuple[str, str, int]:
    """
    Save an uploaded file to the specified subdirectory.

    Args:
        file: The uploaded file
        subdir: Subdirectory within uploads (e.g., 'logos', 'brand_assets')
        allowed_types: List of allowed MIME types (e.g., ['image/png', 'image/jpeg'])
        max_size_mb: Maximum file size in MB

    Returns:
        Tuple of (file_path, mime_type, file_size)

    Raises:
        ValueError: If file type or size is invalid
    """
    # Validate file type
    if allowed_types and file.content_type not in allowed_types:
        raise ValueError(f"File type {file.content_type} not allowed. Allowed types: {allowed_types}")

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Validate file size
    max_size = (max_size_mb or settings.max_file_size_mb) * 1024 * 1024
    if file_size > max_size:
        raise ValueError(f"File size exceeds maximum allowed ({max_size_mb or settings.max_file_size_mb}MB)")

    # Generate unique filename and save
    upload_path = get_upload_path(subdir)
    filename = generate_unique_filename(file.filename or "upload")
    file_path = upload_path / filename

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Return relative path from uploads directory
    relative_path = f"{subdir}/{filename}"
    return relative_path, file.content_type, file_size


async def save_generated_image(
    image_data: Union[bytes, str],
    design_id: str,
    version_number: int,
) -> str:
    """
    Save a generated design image.

    Args:
        image_data: The image bytes or base64-encoded string
        design_id: The design ID
        version_number: The version number

    Returns:
        The relative file path
    """
    upload_path = get_upload_path("generated_designs")
    filename = f"{design_id}_v{version_number}.png"
    file_path = upload_path / filename

    # Decode base64 if it's a string
    if isinstance(image_data, str):
        image_data = base64.b64decode(image_data)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(image_data)

    return f"generated_designs/{filename}"


def delete_file(relative_path: str) -> bool:
    """
    Delete a file from the uploads directory.

    Args:
        relative_path: The relative path from uploads directory

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        full_path = Path(settings.upload_dir) / relative_path
        if full_path.exists():
            full_path.unlink()
            return True
    except Exception:
        pass
    return False


def get_file_url(relative_path: str) -> str:
    """
    Get the URL for accessing an uploaded file.

    Args:
        relative_path: The relative path from uploads directory

    Returns:
        The full URL to access the file
    """
    return f"{settings.backend_url}/api/uploads/{relative_path}"
